"""Reference sequence loading service."""
from pathlib import Path
from typing import Tuple

from app.config import REFERENCE_PATH
from app.services.fasta import parse_and_validate


# Singleton storage
_reference_sequence: str | None = None
_reference_id: str | None = None


def load_reference() -> None:
    """Load reference sequence from file. Called once at startup."""
    global _reference_sequence, _reference_id
    
    if not REFERENCE_PATH.exists():
        raise FileNotFoundError(f"Reference file not found: {REFERENCE_PATH}")
    
    with open(REFERENCE_PATH, 'rb') as f:
        content = f.read()
    
    _reference_id, _reference_sequence = parse_and_validate(content)


def get_reference() -> Tuple[str, str]:
    """
    Get the loaded reference sequence.
    
    Returns:
        Tuple of (reference_id, reference_sequence)
        
    Raises:
        RuntimeError: If reference has not been loaded
    """
    if _reference_sequence is None or _reference_id is None:
        raise RuntimeError("Reference sequence not loaded. Call load_reference() first.")
    
    return _reference_id, _reference_sequence


def get_reference_sequence() -> str:
    """Get just the reference sequence."""
    return get_reference()[1]


def get_reference_id() -> str:
    """Get just the reference ID."""
    return get_reference()[0]
