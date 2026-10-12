"""Tiny SQLite log of (a) questions the bot could not answer and (b) thumbs up/down feedback.

Purpose: show admins which documents are missing. Obvious personal data (phone / Aadhaar-like numbers,
e-mail addresses) is masked before anything is stored; no IP address or user id is kept; rows are
deleted after RETENTION_DAYS.
"""
import os
import re
import sqlite3
import time
from contextlib import closing
from typing import Dict, List

from . import config

_DIGITS = re.compile(r"\d[\d\s\-]{7,}\d")  # 9+ digits possibly spaced: phone, Aadhaar, account numbers
_EMAIL = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")


def redact(text: str, limit: int = 500) -> str:
    text = _EMAIL.sub("[email]", text)
    text = _DIGITS.sub("[number]", text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _conn() -> sqlite3.Connection:
    os.makedirs(config.VECTOR_DB_PATH, exist_ok=True)
    conn = sqlite3.connect(os.path.join(config.VECTOR_DB_PATH, "analytics.db"), timeout=10)
    conn.execute("CREATE TABLE IF NOT EXISTS unanswered (ts REAL, question TEXT, norm TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS feedback (ts REAL, rating TEXT, question TEXT, reply TEXT, comment TEXT)")
    return conn


def _prune(conn: sqlite3.Connection) -> None:
    cutoff = time.time() - config.RETENTION_DAYS * 86400
    conn.execute("DELETE FROM unanswered WHERE ts < ?", (cutoff,))
    conn.execute("DELETE FROM feedback WHERE ts < ?", (cutoff,))


def log_unanswered(question: str) -> None:
    if not config.LOG_QUESTIONS:
        return
    q = redact(question)
    if not q:
        return
    with closing(_conn()) as conn:
        with conn:
            _prune(conn)
            conn.execute("INSERT INTO unanswered VALUES (?, ?, ?)", (time.time(), q, _norm(q)))


def log_feedback(rating: str, question: str, reply: str, comment: str = "") -> None:
    if not config.LOG_QUESTIONS:
        return
    with closing(_conn()) as conn:
        with conn:
            _prune(conn)
            conn.execute(
                "INSERT INTO feedback VALUES (?, ?, ?, ?, ?)",
                (time.time(), rating, redact(question), redact(reply, 800), redact(comment)),
            )


def insights(limit: int = 30) -> Dict[str, List[Dict]]:
    with closing(_conn()) as conn:
        unanswered = conn.execute(
            "SELECT MIN(question), COUNT(*) AS n, MAX(ts) FROM unanswered GROUP BY norm ORDER BY n DESC, MAX(ts) DESC LIMIT ?",
            (limit,),
        ).fetchall()
        down = conn.execute(
            "SELECT ts, question, reply, comment FROM feedback WHERE rating='down' ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
        up_n = conn.execute("SELECT COUNT(*) FROM feedback WHERE rating='up'").fetchone()[0]
        down_n = conn.execute("SELECT COUNT(*) FROM feedback WHERE rating='down'").fetchone()[0]
    return {
        "unanswered": [{"question": q, "count": n, "last_seen": ts} for q, n, ts in unanswered],
        "thumbs_down": [{"ts": ts, "question": q, "reply": r, "comment": c} for ts, q, r, c in down],
        "totals": {"up": up_n, "down": down_n},
    }


def clear() -> None:
    with closing(_conn()) as conn:
        with conn:
            conn.execute("DELETE FROM unanswered")
            conn.execute("DELETE FROM feedback")
