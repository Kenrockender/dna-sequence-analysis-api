import pytest
from app.services.fasta import parse_and_validate
from app.errors import ValidationError


class TestValidFasta:

    def test_single_line_sequence(self):
        fasta = b">seq1\nACGTACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq_id == "seq1"
        assert seq == "ACGTACGT"

    def test_multiline_sequence(self):
        fasta = b">seq2\nACGT\nACGT\nACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq_id == "seq2"
        assert seq == "ACGTACGTACGT"

    def test_lowercase_to_uppercase(self):
        # huruf kecil harus dikonversi ke kapital
        fasta = b">seq3\nacgtacgt"
        seq_id, seq = parse_and_validate(fasta)
        assert seq == "ACGTACGT"

    def test_mixed_case(self):
        fasta = b">seq4\nAcGtNaCgT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq == "ACGTNACGT"

    def test_blank_lines_ignored(self):
        # baris kosong di antara sequence harus diabaikan
        fasta = b">seq5\nACGT\n\nACGT\n\nACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq == "ACGTACGTACGT"

    def test_crlf_line_endings(self):
        # Windows line ending
        fasta = b">seq6\r\nACGT\r\nACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq_id == "seq6"
        assert seq == "ACGTACGT"

    def test_cr_line_endings(self):
        # Mac lama pakai CR
        fasta = b">seq7\rACGT\rACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq_id == "seq7"
        assert seq == "ACGTACGT"

    def test_utf8_bom(self):
        # BOM di awal file harus ditangani
        fasta = b"\xef\xbb\xbf>seq8\nACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq_id == "seq8"
        assert seq == "ACGT"

    def test_header_with_description(self):
        # sequence_id diambil dari token pertama saja
        fasta = b">seq9 This is a description\nACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq_id == "seq9"
        assert seq == "ACGT"

    def test_n_nucleotides(self):
        # N adalah karakter valid
        fasta = b">seq10\nACGTNNNNACGT"
        seq_id, seq = parse_and_validate(fasta)
        assert seq == "ACGTNNNNACGT"

    def test_all_n_sequence(self):
        fasta = b">seq11\nNNNNNNNN"
        seq_id, seq = parse_and_validate(fasta)
        assert seq == "NNNNNNNN"

    def test_leading_trailing_whitespace_on_lines(self):
        # spasi di pinggir baris harus di-trim
        fasta = b">seq12  \n  ACGT  \n  ACGT  "
        seq_id, seq = parse_and_validate(fasta)
        assert seq == "ACGTACGT"

    def test_max_length_1000(self):
        # tepat 1000 karakter harus diterima
        sequence = "A" * 1000
        fasta = f">seq13\n{sequence}".encode()
        seq_id, seq = parse_and_validate(fasta)
        assert len(seq) == 1000


class TestInvalidFasta:

    def test_empty_file(self):
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b"")
        assert exc.value.error_code == "empty_file"

    def test_whitespace_only_file(self):
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b"   \n  \n  ")
        assert exc.value.error_code == "empty_file"

    def test_no_header(self):
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b"ACGTACGT")
        assert exc.value.error_code == "no_header"

    def test_empty_header(self):
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">\nACGT")
        assert exc.value.error_code == "empty_header"

    def test_header_only_whitespace(self):
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">   \nACGT")
        assert exc.value.error_code == "empty_header"

    def test_empty_sequence(self):
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1")
        assert exc.value.error_code == "empty_sequence"

    def test_sequence_only_whitespace(self):
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\n   \n   ")
        assert exc.value.error_code == "empty_sequence"

    def test_multiple_records(self):
        # hanya boleh satu sequence per file
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACGT\n>seq2\nACGT")
        assert exc.value.error_code == "multiple_records"

    def test_text_before_header(self):
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b"Some text\n>seq1\nACGT")
        assert exc.value.error_code == "text_before_header"

    def test_invalid_character_u(self):
        # U (urasil) tidak valid di DNA
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACGUACGT")
        assert exc.value.error_code == "invalid_characters"
        assert "U" in exc.value.detail

    def test_invalid_character_r(self):
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACGRACGT")
        assert exc.value.error_code == "invalid_characters"
        assert "R" in exc.value.detail

    def test_invalid_character_dash(self):
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACG-ACGT")
        assert exc.value.error_code == "invalid_characters"
        assert "-" in exc.value.detail

    def test_invalid_character_asterisk(self):
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACGT*")
        assert exc.value.error_code == "invalid_characters"
        assert "*" in exc.value.detail

    def test_invalid_character_digit(self):
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACGT123")
        assert exc.value.error_code == "invalid_characters"

    def test_embedded_whitespace_space(self):
        # spasi di tengah sequence tidak boleh
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACGT ACGT")
        assert exc.value.error_code == "invalid_sequence"

    def test_embedded_whitespace_tab(self):
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\nACGT\tACGT")
        assert exc.value.error_code == "invalid_sequence"

    def test_length_1001_rejected(self):
        # satu karakter lebih dari batas harus ditolak
        sequence = "A" * 1001
        fasta = f">seq1\n{sequence}".encode()
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(fasta)
        assert exc.value.error_code == "sequence_too_long"

    def test_length_2000_rejected(self):
        sequence = "A" * 2000
        fasta = f">seq1\n{sequence}".encode()
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(fasta)
        assert exc.value.error_code == "sequence_too_long"

    def test_invalid_encoding(self):
        with pytest.raises(ValidationError) as exc:
            parse_and_validate(b">seq1\n\xff\xfeACGT")
        assert exc.value.error_code == "invalid_encoding"
