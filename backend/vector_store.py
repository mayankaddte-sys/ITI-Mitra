import os
import pickle
import numpy as np
from typing import List, Tuple
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./vector_db")

os.makedirs(VECTOR_DB_PATH, exist_ok=True)

class VectorStore:
    def __init__(self):
        self.chunks = []
        self.embeddings = []
        self.metadata = []
        self.load_from_disk()

    def get_embedding(self, text: str) -> List[float]:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    def add_text(self, text: str, metadata: dict = None):
        if not text or not text.strip():
            return
        
        chunks = self._split_text(text)
        for chunk in chunks:
            embedding = self.get_embedding(chunk)
            self.chunks.append(chunk)
            self.embeddings.append(embedding)
            self.metadata.append(metadata or {})
        
        self.save_to_disk()

    def _split_text(self, text: str, chunk_size: int = 500) -> List[str]:
        import re
        text = text.replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks = []
        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) < chunk_size:
                current = (current + " " + sentence).strip()
            else:
                if current:
                    chunks.append(current)
                current = sentence

        if current:
            chunks.append(current)

        return chunks

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        a_arr = np.array(a, dtype=np.float32)
        b_arr = np.array(b, dtype=np.float32)
        denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
        if denom == 0:
            return 0.0
        return float(np.dot(a_arr, b_arr) / denom)

    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, dict, float]]:
        if not self.embeddings:
            return []
        
        query_embedding = self.get_embedding(query)
        scores = []

        for idx, chunk_embedding in enumerate(self.embeddings):
            score = self.cosine_similarity(query_embedding, chunk_embedding)
            scores.append((score, idx))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, idx in scores[:top_k]:
            results.append((self.chunks[idx], self.metadata[idx], score))
        
        return results

    def save_to_disk(self):
        data = {
            "chunks": self.chunks,
            "embeddings": self.embeddings,
            "metadata": self.metadata
        }
        with open(os.path.join(VECTOR_DB_PATH, "vector_store.pkl"), "wb") as f:
            pickle.dump(data, f)

    def load_from_disk(self):
        file_path = os.path.join(VECTOR_DB_PATH, "vector_store.pkl")
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                data = pickle.load(f)
                self.chunks = data.get("chunks", [])
                self.embeddings = data.get("embeddings", [])
                self.metadata = data.get("metadata", [])

    def clear(self):
        self.chunks = []
        self.embeddings = []
        self.metadata = []
        self.save_to_disk()

    def get_stats(self) -> dict:
        return {
            "total_chunks": len(self.chunks),
            "total_embeddings": len(self.embeddings),
            "files_indexed": len(set([m.get("filename") for m in self.metadata]))
        }
