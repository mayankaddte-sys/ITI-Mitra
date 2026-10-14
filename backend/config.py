"""Central configuration, read once from environment / .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _path(name: str, default: str) -> str:
    p = Path(os.getenv(name, default))
    if not p.is_absolute():
        p = BASE_DIR / p
    return str(p.resolve())


def _writable(name: str, default: str, fallback: str) -> str:
    """Like _path, but falls back to a writable folder if the configured one cannot be created."""
    p = Path(os.getenv(name, default))
    if not p.is_absolute():
        p = BASE_DIR / p
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError:
        p = Path(fallback)
        p.mkdir(parents=True, exist_ok=True)
    return str(p.resolve())


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "").strip()
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]

VECTOR_DB_PATH = _writable("VECTOR_DB_PATH", "./vector_db", "/tmp/vector_db")
UPLOAD_DIR = _writable("UPLOAD_DIR", "/tmp/uploads", "/tmp/uploads")
FRONTEND_DIR = str(BASE_DIR / "frontend")

TOP_K = _int("TOP_K", 5)
MIN_SCORE = _float("MIN_SCORE", 0.25)
CHUNK_SIZE = _int("CHUNK_SIZE", 900)
CHUNK_OVERLAP = _int("CHUNK_OVERLAP", 150)
MAX_ANSWER_TOKENS = _int("MAX_ANSWER_TOKENS", 700)
EMBED_BATCH = 100

MAX_UPLOAD_BYTES = _int("MAX_UPLOAD_MB", 15) * 1024 * 1024
CHAT_RATE_LIMIT_PER_MIN = _int("CHAT_RATE_LIMIT_PER_MIN", 20)
TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() == "true"

OCR_LANGS = os.getenv("OCR_LANGS", "hin+eng")
MAX_OCR_PAGES = _int("MAX_OCR_PAGES", 60)

FALLBACK_CONTACT = os.getenv(
    "FALLBACK_CONTACT",
    "Please contact your ITI office or the Directorate helpline for confirmed information. / "
    "कृपया पुष्टि की गई जानकारी के लिए अपने आईटीआई कार्यालय या निदेशालय हेल्पलाइन से संपर्क करें।",
)

LOG_QUESTIONS = os.getenv("LOG_QUESTIONS", "true").lower() == "true"
RETENTION_DAYS = _int("RETENTION_DAYS", 90)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
