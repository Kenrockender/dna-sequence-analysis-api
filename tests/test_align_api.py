import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app
from app.services.reference import load_reference

load_reference()

client = TestClient(app)
PATIENT_DIR = Path("static/samples")


class TestAlignEndpoint:

    def test_patient_01_perfect_match(self):
        # patient_01 identik dengan referensi, tidak ada varian
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post("/api/align", files={"file": ("patient_01.fasta", f, "text/plain")})

        assert response.status_code == 200
        data = response.json()

        assert data["sequence_id"] == "patient_01"
        assert data["reference_id"] == "REF_001"
        assert data["alignment"]["score"] == 300.0
        assert data["alignment"]["identity"] == 1.0
        assert len(data["variants"]) == 0

    def test_patient_02_three_snvs(self):
        # patient_02 punya 3 SNV
        with open(PATIENT_DIR / "patient_02.fasta", "rb") as f:
            response = client.post("/api/align", files={"file": ("patient_02.fasta", f, "text/plain")})

        assert response.status_code == 200
        data = response.json()

        assert data["sequence_id"] == "patient_02"
        assert data["alignment"]["score"] == 294.0
        assert data["alignment"]["identity"] == 0.99

        variants = data["variants"]
        assert len(variants) == 3

        assert variants[0]["position"] == 52
        assert variants[0]["ref"] == "C"
        assert variants[0]["alt"] == "A"
        assert variants[0]["type"] == "SNV"

        assert variants[1]["position"] == 177
        assert variants[1]["ref"] == "A"
        assert variants[1]["alt"] == "T"
        assert variants[1]["type"] == "SNV"

        assert variants[2]["position"] == 245
        assert variants[2]["ref"] == "T"
        assert variants[2]["alt"] == "G"
        assert variants[2]["type"] == "SNV"

    def test_patient_03_two_deletions(self):
        # patient_03 punya deletion, total 4 basa yang hilang
        with open(PATIENT_DIR / "patient_03.fasta", "rb") as f:
            response = client.post("/api/align", files={"file": ("patient_03.fasta", f, "text/plain")})

        assert response.status_code == 200
        data = response.json()

        assert data["sequence_id"] == "patient_03"
        assert data["alignment"]["score"] == 288.0
        assert pytest.approx(data["alignment"]["identity"], 0.001) == 296.0 / 300.0

        variants = data["variants"]
        assert all(v["type"] == "deletion" for v in variants)
        assert all(v["alt"] == "-" for v in variants)

        total_deleted = sum(len(v["ref"]) for v in variants)
        assert total_deleted == 4

    def test_patient_04_n_handling(self):
        # patient_04 ada N, tidak ada SNV yang di-call
        with open(PATIENT_DIR / "patient_04.fasta", "rb") as f:
            response = client.post("/api/align", files={"file": ("patient_04.fasta", f, "text/plain")})

        assert response.status_code == 200
        data = response.json()

        assert data["sequence_id"] == "patient_04"
        assert data["alignment"]["identity"] < 1.0
        assert len(data["variants"]) == 0

    def test_patient_05_two_insertions(self):
        # patient_05 punya insertion, total 4 basa tambahan
        with open(PATIENT_DIR / "patient_05.fasta", "rb") as f:
            response = client.post("/api/align", files={"file": ("patient_05.fasta", f, "text/plain")})

        assert response.status_code == 200
        data = response.json()

        assert data["sequence_id"] == "patient_05"
        assert data["alignment"]["score"] == 292.0
        assert pytest.approx(data["alignment"]["identity"], 0.001) == 300.0 / 304.0

        variants = data["variants"]
        assert all(v["type"] == "insertion" for v in variants)
        assert all(v["ref"] == "-" for v in variants)

        total_inserted = sum(len(v["alt"]) for v in variants)
        assert total_inserted == 4


class TestAlignedSequencesInvariant:

    def test_patient_01_invariant(self):
        # kalau gap dihapus, harus sama dengan sequence aslinya
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            content = f.read()

        response = client.post("/api/align", files={"file": ("patient_01.fasta", content, "text/plain")})
        data = response.json()

        ref_no_gaps = data["alignment"]["reference_aligned"].replace("-", "")
        query_no_gaps = data["alignment"]["query_aligned"].replace("-", "")

        from app.services.fasta import parse_and_validate
        _, query_original = parse_and_validate(content)
        from app.services.reference import get_reference
        _, ref_original = get_reference()

        assert ref_no_gaps == ref_original
        assert query_no_gaps == query_original

    def test_patient_02_invariant(self):
        with open(PATIENT_DIR / "patient_02.fasta", "rb") as f:
            content = f.read()

        response = client.post("/api/align", files={"file": ("patient_02.fasta", content, "text/plain")})
        data = response.json()

        ref_no_gaps = data["alignment"]["reference_aligned"].replace("-", "")
        query_no_gaps = data["alignment"]["query_aligned"].replace("-", "")

        from app.services.fasta import parse_and_validate
        _, query_original = parse_and_validate(content)
        from app.services.reference import get_reference
        _, ref_original = get_reference()

        assert ref_no_gaps == ref_original
        assert query_no_gaps == query_original


class TestAlignDeterminism:

    def test_same_input_same_output(self):
        # input yang sama harus selalu kasih output yang sama
        with open(PATIENT_DIR / "patient_02.fasta", "rb") as f:
            content = f.read()

        response1 = client.post("/api/align", files={"file": ("patient_02.fasta", content, "text/plain")})
        response2 = client.post("/api/align", files={"file": ("patient_02.fasta", content, "text/plain")})

        assert response1.json() == response2.json()


class TestAlignErrors:

    def test_missing_file(self):
        response = client.post("/api/align")
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "detail" in data

    def test_invalid_fasta_multiple_records(self):
        invalid_fasta = b">seq1\nACGT\n>seq2\nACGT"
        response = client.post("/api/align", files={"file": ("test.fasta", invalid_fasta, "text/plain")})
        assert response.status_code == 422
        assert response.json()["error"] == "multiple_records"

    def test_invalid_fasta_no_header(self):
        invalid_fasta = b"ACGTACGT"
        response = client.post("/api/align", files={"file": ("test.fasta", invalid_fasta, "text/plain")})
        assert response.status_code == 422
        assert response.json()["error"] == "no_header"

    def test_sequence_too_long(self):
        long_seq = "A" * 1001
        invalid_fasta = f">seq1\n{long_seq}".encode()
        response = client.post("/api/align", files={"file": ("test.fasta", invalid_fasta, "text/plain")})
        assert response.status_code == 422
        assert response.json()["error"] == "sequence_too_long"

    def test_invalid_characters(self):
        # U tidak valid di DNA
        invalid_fasta = b">seq1\nACGTU"
        response = client.post("/api/align", files={"file": ("test.fasta", invalid_fasta, "text/plain")})
        assert response.status_code == 422
        assert response.json()["error"] == "invalid_characters"
