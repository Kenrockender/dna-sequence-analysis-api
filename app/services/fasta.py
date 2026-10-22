import re
from typing import Tuple

from app.config import MAX_SEQUENCE_LENGTH, MAX_FILE_SIZE_BYTES, VALID_NUCLEOTIDES
from app.errors import ValidationError


def parse_and_validate(content: bytes) -> Tuple[str, str]:
    # cek ukuran file dulu sebelum diproses
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise ValidationError("file_too_large", f"File exceeds maximum size of {MAX_FILE_SIZE_BYTES} bytes")

    # decode bytes ke string, handle BOM kalau ada
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValidationError("invalid_encoding", "File must be UTF-8 encoded")

    if not text.strip():
        raise ValidationError("empty_file", "File is empty")

    # normalisasi line ending biar konsisten
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')

    # cari semua baris yang mulai dengan '>' (header FASTA)
    header_indices = [i for i, line in enumerate(lines) if line.strip().startswith('>')]

    if len(header_indices) == 0:
        raise ValidationError("no_header", "No FASTA header found (line starting with '>')")

    if len(header_indices) > 1:
        raise ValidationError("multiple_records", "FASTA file must contain exactly one sequence record")

    header_idx = header_indices[0]

    # pastikan tidak ada teks sebelum header
    for i in range(header_idx):
        if lines[i].strip():
            raise ValidationError("text_before_header", "Text found before FASTA header")

    # ambil dan cek header
    header_line = lines[header_idx].strip()
    if len(header_line) <= 1:
        raise ValidationError("empty_header", "FASTA header is empty")

    header_content = header_line[1:].strip()
    if not header_content:
        raise ValidationError("empty_header", "FASTA header is empty")

    # sequence_id diambil dari token pertama setelah '>'
    sequence_id = header_content.split()[0]

    # kumpulkan baris-baris sequence di bawah header
    seq_lines = []
    for i in range(header_idx + 1, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
        if line.startswith('>'):
            raise ValidationError("multiple_records", "FASTA file must contain exactly one sequence record")
        seq_lines.append(line)

    if not seq_lines:
        raise ValidationError("empty_sequence", "Sequence is empty")

    sequence = ''.join(seq_lines)

    # sequence tidak boleh ada spasi di dalamnya
    if re.search(r'\s', sequence):
        raise ValidationError("invalid_sequence", "Sequence contains whitespace characters")

    sequence = sequence.upper()

    # cek kalau ada karakter yang bukan ACGTN
    bad_chars = set(sequence) - VALID_NUCLEOTIDES
    if bad_chars:
        bad_str = ', '.join(sorted(bad_chars))
        raise ValidationError("invalid_characters", f"Sequence contains invalid characters: {bad_str}")

    # cek panjang sequence
    seq_len = len(sequence)
    if seq_len == 0:
        raise ValidationError("empty_sequence", "Sequence is empty")
    if seq_len > MAX_SEQUENCE_LENGTH:
        raise ValidationError("sequence_too_long",
                              f"Sequence length ({seq_len}) exceeds maximum ({MAX_SEQUENCE_LENGTH})")

    return sequence_id, sequence
