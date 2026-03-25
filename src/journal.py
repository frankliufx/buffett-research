"""Investment journal persistence — file-based JSON storage."""

import json
import logging
from pathlib import Path
from typing import List

_JOURNAL_FILE = Path(__file__).parent.parent / "data" / "journal.json"
logger = logging.getLogger(__name__)


def load_journal() -> List[dict]:
    """Load all journal entries from disk. Returns [] on any error."""
    try:
        if _JOURNAL_FILE.exists():
            data = json.loads(_JOURNAL_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("Journal load failed: %s", e)
    return []


def save_journal(entries: List[dict]) -> bool:
    """Persist journal entries to disk. Returns True on success."""
    try:
        _JOURNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        _JOURNAL_FILE.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except Exception as e:
        logger.warning("Journal save failed: %s", e)
        return False


def export_json(entries: List[dict]) -> str:
    """Serialize entries to a JSON string for download."""
    return json.dumps(entries, ensure_ascii=False, indent=2)


def import_json(raw: str) -> List[dict]:
    """Parse a JSON string into a list of entries. Raises ValueError on bad input."""
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array")
    return data
