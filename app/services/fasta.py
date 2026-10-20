"""FASTA file parsing and validation service."""
import re
from typing import Tuple

from app.config import MAX_SEQUENCE_LENGTH, MAX_FILE_SIZE_BYTES, VALID_NUCLEOTIDES
from app.errors import ValidationError


def parse_and_validate(content: bytes) -> Tuple[str, str]:
    """
    Parse and validate a FASTA file from bytes.
    
    Args:
        content: Raw bytes from uploaded FASTA file
        
    Returns:
        Tuple of (sequence_id, sequence) where sequence is uppercase ACGTN
        
    Raises:
        ValidationError: If validation fails
    """
    # Check file size
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise ValidationError("file_too_large", f"File exceeds maximum size of {MAX_FILE_SIZE_BYTES} bytes")
    
    # Decode to string, handling UTF-8 BOM
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValidationError("invalid_encoding", "File must be UTF-8 encoded")
    
    # Empty file check
    if not text.strip():
        raise ValidationError("empty_file", "File is empty")
    
    # Split into lines and normalize line endings
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    
    # Find header lines (starting with >)
    header_indices = [i for i, line in enumerate(lines) if line.strip().startswith('>')]
    
    if len(header_indices) == 0:
        raise ValidationError("no_header", "No FASTA header found (line starting with '>')")
    
    if len(header_indices) > 1:
        raise ValidationError("multiple_records", "FASTA file must contain exactly one sequence record")
    
    header_idx = header_indices[0]
    
    # Check for text before header
    for i in range(header_idx):
        if lines[i].strip():
            raise ValidationError("text_before_header", "Text found before FASTA header")
    
    # Parse header
    header_line = lines[header_idx].strip()
    if len(header_line) <= 1:  # Just '>' with nothing after
        raise ValidationError("empty_header", "FASTA header is empty")
    
    # Extract sequence_id (first whitespace-delimited token after >)
    header_content = header_line[1:].strip()
    if not header_content:
        raise ValidationError("empty_header", "FASTA header is empty")
    
    sequence_id = header_content.split()[0]
    
    # Parse sequence lines
    sequence_lines = []
    for i in range(header_idx + 1, len(lines)):
        line = lines[i].strip()
        if not line:  # Skip blank lines
            continue
        if line.startswith('>'):
            raise ValidationError("multiple_records", "FASTA file must contain exactly one sequence record")
        sequence_lines.append(line)
    
    if not sequence_lines:
        raise ValidationError("empty_sequence", "Sequence is empty")
    
    # Join sequence lines
    sequence = ''.join(sequence_lines)
    
    # Check for embedded whitespace in sequence
    if re.search(r'\s', sequence):
        raise ValidationError("invalid_sequence", "Sequence contains whitespace characters")
    
    # Convert to uppercase
    sequence = sequence.upper()
    
    # Validate characters
    invalid_chars = set(sequence) - VALID_NUCLEOTIDES
    if invalid_chars:
        invalid_str = ', '.join(sorted(invalid_chars))
        raise ValidationError("invalid_characters", f"Sequence contains invalid characters: {invalid_str}")
    
    # Check length
    seq_len = len(sequence)
    if seq_len == 0:
        raise ValidationError("empty_sequence", "Sequence is empty")
    if seq_len > MAX_SEQUENCE_LENGTH:
        raise ValidationError("sequence_too_long", 
                            f"Sequence length ({seq_len}) exceeds maximum ({MAX_SEQUENCE_LENGTH})")
    
    return sequence_id, sequence
