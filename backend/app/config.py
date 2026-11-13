"""Central configuration, read from environment variables (never hard-code keys)."""
import os
from pathlib import Path

DATA_DIR = Path(os.getenv("CODECOMPASS_DATA", Path(__file__).resolve().parents[1] / "data"))
REPOS_DIR = DATA_DIR / "repos"
DB_PATH = DATA_DIR / "codecompass.db"
CHROMA_DIR = DATA_DIR / "chroma"
for p in (DATA_DIR, REPOS_DIR):
    p.mkdir(parents=True, exist_ok=True)

# LLM_PROVIDER can be "ollama" (local, default) or "anthropic".
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-5")

EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
# "auto" = sentence-transformers if installed, else hashing fallback
EMBED_BACKEND = os.getenv("EMBED_BACKEND", "auto")
VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "auto")  # auto | chroma | memory

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
MAX_FILES = int(os.getenv("MAX_FILES", "3000"))
MAX_FILE_KB = int(os.getenv("MAX_FILE_KB", "300"))
TOP_K = int(os.getenv("TOP_K", "6"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
