from pathlib import Path
from typing import Tuple

from app.config import REFERENCE_PATH
from app.services.fasta import parse_and_validate

# disimpan di sini supaya cuma dibaca sekali waktu startup
_reference_sequence: str | None = None
_reference_id: str | None = None


def load_reference() -> None:
    global _reference_sequence, _reference_id

    if not REFERENCE_PATH.exists():
        raise FileNotFoundError(f"Reference file not found: {REFERENCE_PATH}")

    with open(REFERENCE_PATH, 'rb') as f:
        content = f.read()

    # pakai fungsi yang sama dengan validasi input user
    _reference_id, _reference_sequence = parse_and_validate(content)


def get_reference() -> Tuple[str, str]:
    # kalau belum di-load, lempar error
    if _reference_sequence is None or _reference_id is None:
        raise RuntimeError("Reference sequence not loaded. Call load_reference() first.")

    return _reference_id, _reference_sequence


def get_reference_sequence() -> str:
    return get_reference()[1]


def get_reference_id() -> str:
    return get_reference()[0]
