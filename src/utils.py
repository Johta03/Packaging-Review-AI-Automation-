"""Helpers: run_id generation and file I/O."""
import uuid
from pathlib import Path


def generate_run_id() -> str:
    """Return a unique run ID (UUID)."""
    return str(uuid.uuid4())


def read_brief(path: str | Path) -> str:
    """Read brief text from file. Raises FileNotFoundError if missing."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Brief file not found: {path}")
    return p.read_text(encoding="utf-8")


def ensure_output_dir(base_out: str | Path, run_id: str) -> Path:
    """Create outputs/<run_id>/ and return the path."""
    out_dir = Path(base_out) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir
