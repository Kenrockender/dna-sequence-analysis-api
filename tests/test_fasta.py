"""Tests for FASTA parsing and validation."""
import pytest
from app.services.fasta import parse_and_validate
from app.errors import ValidationError


class TestValidFasta:
    """Tests for valid FASTA input."""
    
    def test_single_line_sequence(self):
        """Valid single-line FASTA."""
        fasta = b">seq1\nACGTACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq_id == "seq1"
        assert seq == "ACGTACGT"
    
    def test_multiline_sequence(self):
        """Valid multiline FASTA."""
        fasta = b">seq2\nACGT\nACGT\nACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq_id == "seq2"
        assert seq == "ACGTACGTACGT"
    
    def test_lowercase_to_uppercase(self):
        """Lowercase nucleotides are converted to uppercase."""
        fasta = b">seq3\nacgtacgt"
        seq_id, seq = parse_and_validate(fasta)
        assert seq == "ACGTACGT"
    
    def test_mixed_case(self):
        """Mixed case nucleotides are converted to uppercase."""
        fasta = b">seq4\nAcGtNaCgT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq == "ACGTNACGT"
    
    def test_blank_lines_ignored(self):
        """Blank lines in sequence are ignored."""
        fasta = b">seq5\nACGT\n\nACGT\n\nACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq == "ACGTACGTACGT"
    
    def test_crlf_line_endings(self):
        """Windows CRLF line endings are handled."""
        fasta = b">seq6\r\nACGT\r\nACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq_id == "seq6"
        assert seq == "ACGTACGT"
    
    def test_cr_line_endings(self):
        """Old Mac CR line endings are handled."""
        fasta = b">seq7\rACGT\rACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq_id == "seq7"
        assert seq == "ACGTACGT"
    
    def test_utf8_bom(self):
        """UTF-8 BOM is handled."""
        fasta = b"\xef\xbb\xbf>seq8\nACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq_id == "seq8"
        assert seq == "ACGT"
    
    def test_header_with_description(self):
        """Header with description, first token is sequence_id."""
        fasta = b">seq9 This is a description\nACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq_id == "seq9"
        assert seq == "ACGT"
    
    def test_n_nucleotides(self):
        """N nucleotides are valid."""
        fasta = b">seq10\nACGTNNNNACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq == "ACGTNNNNACGT"
    
    def test_all_n_sequence(self):
        """Sequence of all N is valid."""
        fasta = b">seq11\nNNNNNNNN"
        seq_id, seq = parse_and_validate(fasta)
        assert seq == "NNNNNNNN"
    
    def test_leading_trailing_whitespace_on_lines(self):
        """Leading/trailing whitespace on lines is trimmed."""
        fasta = b">seq12  \n  ACGT  \n  ACGT  "
        seq_id, seq = parse_and_validate(fasta)
        assert seq == "ACGTACGT"
    
    def test_max_length_1000(self):
        """Sequence of exactly 1000 nt is accepted."""
        sequence = "A" * 1000
        fasta = f">seq13\n{sequence}".encode()
        seq_id, seq = parse_and_validate(fasta)
        assert len(seq) == 1000


class TestInvalidFasta:
    """Tests for invalid FASTA input that should be rejected."""
    
    def test_empty_file(self):
        """Empty file is rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b"")
        assert exc.value.error_code == "empty_file"
    
    def test_whitespace_only_file(self):
        """File with only whitespace is rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b"   \n  \n  ")
        assert exc.value.error_code == "empty_file"
    
    def test_no_header(self):
        """File without header is rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b"ACGTACGT")
        assert exc.value.error_code == "no_header"
    
    def test_empty_header(self):
        """Header with no content after > is rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">\nACGT")
        assert exc.value.error_code == "empty_header"
    
    def test_header_only_whitespace(self):
        """Header with only whitespace after > is rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">   \nACGT")
        assert exc.value.error_code == "empty_header"
    
    def test_empty_sequence(self):
        """Header with no sequence is rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1")
        assert exc.value.error_code == "empty_sequence"
    
    def test_sequence_only_whitespace(self):
        """Header with only whitespace as sequence is rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\n   \n   ")
        assert exc.value.error_code == "empty_sequence"
    
    def test_multiple_records(self):
        """Multiple sequence records are rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACGT\n>seq2\nACGT")
        assert exc.value.error_code == "multiple_records"
    
    def test_text_before_header(self):
        """Text before first header is rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b"Some text\n>seq1\nACGT")
        assert exc.value.error_code == "text_before_header"
    
    def test_invalid_character_u(self):
        """U (uracil) is rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACGUACGT")
        assert exc.value.error_code == "invalid_characters"
        assert "U" in exc.value.detail
    
    def test_invalid_character_r(self):
        """R (purine) is rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACGRACGT")
        assert exc.value.error_code == "invalid_characters"
        assert "R" in exc.value.detail
    
    def test_invalid_character_dash(self):
        """Dash (gap) is rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACG-ACGT")
        assert exc.value.error_code == "invalid_characters"
        assert "-" in exc.value.detail
    
    def test_invalid_character_asterisk(self):
        """Asterisk (stop codon) is rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACGT*")
        assert exc.value.error_code == "invalid_characters"
        assert "*" in exc.value.detail
    
    def test_invalid_character_digit(self):
        """Digits are rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACGT123")
        assert exc.value.error_code == "invalid_characters"
    
    def test_embedded_whitespace_space(self):
        """Whitespace within sequence line is rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACGT ACGT")
        assert exc.value.error_code == "invalid_sequence"
    
    def test_embedded_whitespace_tab(self):
        """Tab within sequence line is rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACGT\tACGT")
        assert exc.value.error_code == "invalid_sequence"
    
    def test_length_1001_rejected(self):
        """Sequence of 1001 nt is rejected."""
        sequence = "A" * 1001
        fasta = f">seq1\n{sequence}".encode()
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(fasta)
        assert exc.value.error_code == "sequence_too_long"
    
    def test_length_2000_rejected(self):
        """Sequence much longer than limit is rejected."""
        sequence = "A" * 2000
        fasta = f">seq1\n{sequence}".encode()
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(fasta)
        assert exc.value.error_code == "sequence_too_long"
    
    def test_invalid_encoding(self):
        """Non-UTF-8 content is rejected."""
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\n\xff\xfeACGT")
        assert exc.value.error_code == "invalid_encoding"
