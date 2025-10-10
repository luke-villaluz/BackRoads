from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

_ROOT_DIR = Path(__file__).resolve().parents[2]

def _require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Environment variable {key} is required but unset.")
    return value

def _resolve_path(key: str) -> Path:
    raw_value = _require_env(key)
    path = Path(raw_value)
    if not path.is_absolute():
        path = _ROOT_DIR / path
    return path

GRAPH_PATH = _resolve_path("GRAPH_PATH")
CONFIGS_DIR = _resolve_path("CONFIGS_DIR")
OUTPUTS_DIR = _resolve_path("OUTPUTS_DIR")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

def ensure_directories() -> None:
    for path in (GRAPH_PATH.parent, CONFIGS_DIR, OUTPUTS_DIR):
        path.mkdir(parents=True, exist_ok=True)
