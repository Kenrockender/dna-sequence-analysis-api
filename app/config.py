from pathlib import Path

# panjang maksimal sequence yang boleh dikirim
MAX_SEQUENCE_LENGTH = 1000
MAX_FILE_SIZE_BYTES = 1_048_576  # sekitar 1 MB

# karakter yang valid untuk DNA
VALID_NUCLEOTIDES = set("ACGTN")

# skor untuk proses alignment
MATCH_SCORE = 1       # kalau basanya sama
MISMATCH_SCORE = -1   # kalau beda
GAP_OPEN_SCORE = -2   # penalty buat gap
GAP_EXTEND_SCORE = -2 # penalty tiap nambah gap
N_SCORE = 0           # N vs apapun dianggap netral

# path ke file referensi
APP_DIR = Path(__file__).parent
REFERENCE_PATH = APP_DIR / "data" / "reference.fasta"
