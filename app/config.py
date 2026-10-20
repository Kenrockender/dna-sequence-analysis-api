"""Configuration constants for the DNA sequence analysis API."""
from pathlib import Path

# Sequence validation
MAX_SEQUENCE_LENGTH = 1000
MAX_FILE_SIZE_BYTES = 1_048_576  # ~1 MB

# Valid nucleotides
VALID_NUCLEOTIDES = set("ACGTN")

# Alignment scoring
MATCH_SCORE = 1
MISMATCH_SCORE = -1
GAP_OPEN_SCORE = -2
GAP_EXTEND_SCORE = -2
N_SCORE = 0  # N vs any base (including N) scores 0

# Reference sequence path
APP_DIR = Path(__file__).parent
REFERENCE_PATH = APP_DIR / "data" / "reference.fasta"
