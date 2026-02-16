"""Append-only JSONL audit logger."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def log_event(
    audit_path: Path,
    run_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    model_name: str | None = None,
) -> None:
    """Append one JSON object (one line) to the audit file."""
    payload = payload or {}
    record = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "run_id": run_id,
        "event_type": event_type,
        "model_name": model_name,
        "payload": payload,
    }
    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
