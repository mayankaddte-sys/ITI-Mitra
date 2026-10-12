"""Small disk-backed vector store.

* Embeddings: one L2-normalised float32 matrix (.npy) -> search is a single matrix product.
* Chunks + metadata: JSON. No pickle (loading a tampered pickle can run code).
* Re-uploading a file replaces its old chunks; single files can be removed.
"""
import json
import logging
import os
import re
import threading
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import config
from .openai_client import get_client

log = logging.getLogger("iti_mitra.store")

# Sentence ends: . ! ? and the Hindi danda / double danda.
_SENT_RE = re.compile(r"(?<=[.!?।॥])\s+")


def split_text(text: str, size: int = None, overlap: int = None) -> List[str]:
    size = size or config.CHUNK_SIZE
    overlap = config.CHUNK_OVERLAP if overlap is None else overlap

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    units: List[str] = []
    for para in text.split("\n\n"):
        for sent in _SENT_RE.split(para.strip()):
            sent = sent.strip()
            while len(sent) > size:  # very long run with no sentence end (tables, lists)
                cut = sent.rfind(" ", 0, size)
                cut = cut if cut > size * 0.5 else size
                units.append(sent[:cut].strip())
                sent = sent[cut:].strip()
            if sent:
                units.append(sent)

    chunks: List[str] = []
    cur: List[str] = []
    cur_len = 0
    for unit in units:
        if cur and cur_len + len(unit) + 1 > size:
            chunks.append(" ".join(cur))
            carry: List[str] = []
            carried = 0
            for prev in reversed(cur):  # overlap: repeat the last few sentences
                if carried + len(prev) + 1 > overlap:
                    break
                carry.insert(0, prev)
                carried += len(prev) + 1
            cur, cur_len = carry, carried
        cur.append(unit)
        cur_len += len(unit) + 1
    if cur:
        chunks.append(" ".join(cur))
    return chunks


class VectorStore:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.VECTOR_DB_PATH
        os.makedirs(self.db_path, exist_ok=True)
        self._lock = threading.RLock()
        self.chunks: List[str] = []
        self.metadata: List[dict] = []
        self.embeddings: Optional[np.ndarray] = None
        self._load()

    # ---- embeddings -------------------------------------------------------------------
    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        client = get_client()
        out: List[List[float]] = []
        for i in range(0, len(texts), config.EMBED_BATCH):
            batch = list(texts[i : i + config.EMBED_BATCH])
            resp = client.embeddings.create(model=config.EMBEDDING_MODEL, input=batch)
            out.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
        arr = np.asarray(out, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms

    # ---- write ------------------------------------------------------------------------
    def add_document(self, segments: Sequence[Tuple[Optional[int], str]], base_meta: dict) -> int:
        """Index a document, replacing any earlier upload with the same filename."""
        new_chunks: List[str] = []
        new_meta: List[dict] = []
        for page, text in segments:
            for chunk in split_text(text):
                meta = dict(base_meta)
                if page is not None:
                    meta["page"] = page
                new_chunks.append(chunk)
                new_meta.append(meta)
        if not new_chunks:
            return 0

        emb = self.embed_texts(new_chunks)  # network call: done outside the lock, before touching state

        with self._lock:
            self._remove_locked(base_meta["filename"])
            self.chunks.extend(new_chunks)
            self.metadata.extend(new_meta)
            self.embeddings = emb if self.embeddings is None else np.vstack([self.embeddings, emb])
            self._save_locked()
        return len(new_chunks)

    def remove_file(self, filename: str) -> int:
        with self._lock:
            removed = self._remove_locked(filename)
            if removed:
                self._save_locked()
            return removed

    def clear(self) -> None:
        with self._lock:
            self.chunks, self.metadata, self.embeddings = [], [], None
            self._save_locked()

    def _remove_locked(self, filename: str) -> int:
        keep = [i for i, m in enumerate(self.metadata) if m.get("filename") != filename]
        removed = len(self.metadata) - len(keep)
        if not removed:
            return 0
        self.chunks = [self.chunks[i] for i in keep]
        self.metadata = [self.metadata[i] for i in keep]
        self.embeddings = self.embeddings[keep] if keep else None
        return removed

    # ---- read -------------------------------------------------------------------------
    def search(self, query: str, top_k: int = None, min_score: float = None) -> List[Tuple[str, dict, float]]:
        top_k = top_k or config.TOP_K
        min_score = config.MIN_SCORE if min_score is None else min_score
        with self._lock:  # arrays are replaced, never mutated in place, so references are a safe snapshot
            emb, chunks, meta = self.embeddings, self.chunks, self.metadata
        if emb is None or not len(chunks):
            return []
        q = self.embed_texts([query])[0]
        scores = emb @ q
        order = np.argsort(-scores)[:top_k]
        return [(chunks[i], meta[i], float(scores[i])) for i in order if scores[i] >= min_score]

    def is_empty(self) -> bool:
        return self.embeddings is None or not self.chunks

    def list_files(self) -> List[Dict]:
        with self._lock:
            files: Dict[str, Dict] = {}
            for m in self.metadata:
                f = files.setdefault(
                    m["filename"],
                    {
                        "filename": m["filename"],
                        "chunks": 0,
                        "category": m.get("category", ""),
                        "issue_date": m.get("issue_date", ""),
                    },
                )
                f["chunks"] += 1
            return sorted(files.values(), key=lambda f: f["filename"].lower())

    def get_stats(self) -> dict:
        files = self.list_files()
        return {"total_chunks": len(self.chunks), "files_indexed": len(files)}

    # ---- persistence ------------------------------------------------------------------
    def _paths(self):
        return os.path.join(self.db_path, "store.json"), os.path.join(self.db_path, "embeddings.npy")

    def _save_locked(self) -> None:
        json_path, npy_path = self._paths()
        tmp_json, tmp_npy = json_path + ".tmp", npy_path + ".tmp"
        with open(tmp_json, "w", encoding="utf-8") as f:
            json.dump({"chunks": self.chunks, "metadata": self.metadata}, f, ensure_ascii=False)
        if self.embeddings is not None:
            with open(tmp_npy, "wb") as f:
                np.save(f, self.embeddings, allow_pickle=False)
            os.replace(tmp_npy, npy_path)
        elif os.path.exists(npy_path):
            os.remove(npy_path)
        os.replace(tmp_json, json_path)

    def _load(self) -> None:
        json_path, npy_path = self._paths()
        if not os.path.exists(json_path):
            if os.path.exists(os.path.join(self.db_path, "vector_store.pkl")):
                log.warning("Old pickle-based index found and ignored; please re-upload your documents.")
            return
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            chunks, metadata = data["chunks"], data["metadata"]
            emb = np.load(npy_path, allow_pickle=False) if os.path.exists(npy_path) else None
            if chunks and (emb is None or emb.shape[0] != len(chunks) or len(metadata) != len(chunks)):
                raise ValueError("index files are inconsistent")
            self.chunks, self.metadata, self.embeddings = chunks, metadata, (emb if chunks else None)
        except Exception:
            log.exception("Could not load the vector index; starting empty. Re-upload documents.")
            self.chunks, self.metadata, self.embeddings = [], [], None
