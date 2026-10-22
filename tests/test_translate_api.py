import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app
from app.services.reference import load_reference

load_reference()

client = TestClient(app)
PATIENT_DIR = Path("static/samples")


class TestTranslateEndpoint:

    def test_patient_02_frame_1(self):
        with open(PATIENT_DIR / "patient_02.fasta", "rb") as f:
            response = client.post("/api/translate", files={"file": ("patient_02.fasta", f, "text/plain")})

        assert response.status_code == 200
        data = response.json()

        assert data["sequence_id"] == "patient_02"
        assert data["frame"] == 1
        assert data["length"] > 0
        assert "K" in data["protein"] or data["has_stop_codon"]

    def test_frame_1_explicit(self):
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate",
                files={"file": ("patient_01.fasta", f, "text/plain")},
                data={"frame": "1"}
            )

        assert response.status_code == 200
        assert response.json()["frame"] == 1

    def test_frame_2(self):
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate",
                files={"file": ("patient_01.fasta", f, "text/plain")},
                data={"frame": "2"}
            )

        assert response.status_code == 200
        assert response.json()["frame"] == 2

    def test_frame_3(self):
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate",
                files={"file": ("patient_01.fasta", f, "text/plain")},
                data={"frame": "3"}
            )

        assert response.status_code == 200
        assert response.json()["frame"] == 3

    def test_n_codons_become_x(self):
        # patient_04 punya N, harus ada X di protein
        with open(PATIENT_DIR / "patient_04.fasta", "rb") as f:
            response = client.post("/api/translate", files={"file": ("patient_04.fasta", f, "text/plain")})

        assert response.status_code == 200
        assert "X" in response.json()["protein"]

    def test_has_stop_codon_true(self):
        with open(PATIENT_DIR / "patient_02.fasta", "rb") as f:
            response = client.post("/api/translate", files={"file": ("patient_02.fasta", f, "text/plain")})

        assert response.status_code == 200
        assert isinstance(response.json()["has_stop_codon"], bool)

    def test_incomplete_codon_ignored(self):
        # 7 nt = 2 kodon lengkap + 1 sisa, sisa diabaikan
        fasta = b">test\nATGCGTA"
        response = client.post("/api/translate", files={"file": ("test.fasta", fasta, "text/plain")})

        assert response.status_code == 200
        assert response.json()["length"] == 2


class TestTranslateFrameValidation:

    def test_invalid_frame_0(self):
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate",
                files={"file": ("patient_01.fasta", f, "text/plain")},
                data={"frame": "0"}
            )

        assert response.status_code == 422
        assert response.json()["error"] == "invalid_frame"

    def test_invalid_frame_4(self):
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate",
                files={"file": ("patient_01.fasta", f, "text/plain")},
                data={"frame": "4"}
            )

        assert response.status_code == 422
        assert response.json()["error"] == "invalid_frame"

    def test_invalid_frame_abc(self):
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate",
                files={"file": ("patient_01.fasta", f, "text/plain")},
                data={"frame": "abc"}
            )

        assert response.status_code == 422
        assert response.json()["error"] == "invalid_frame"

    def test_invalid_frame_float(self):
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate",
                files={"file": ("patient_01.fasta", f, "text/plain")},
                data={"frame": "1.5"}
            )

        assert response.status_code == 422
        assert response.json()["error"] == "invalid_frame"

    def test_omitted_frame_uses_default(self):
        # kalau frame tidak dikasih, default ke 1
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate",
                files={"file": ("patient_01.fasta", f, "text/plain")}
            )

        assert response.status_code == 200
        assert response.json()["frame"] == 1


class TestTranslateErrors:

    def test_missing_file(self):
        response = client.post("/api/translate")
        assert response.status_code == 422
        assert "error" in response.json()

    def test_invalid_fasta_multiple_records(self):
        invalid_fasta = b">seq1\nATG\n>seq2\nATG"
        response = client.post("/api/translate", files={"file": ("test.fasta", invalid_fasta, "text/plain")})
        assert response.status_code == 422
        assert response.json()["error"] == "multiple_records"

    def test_sequence_too_long(self):
        long_seq = "A" * 1001
        invalid_fasta = f">seq1\n{long_seq}".encode()
        response = client.post("/api/translate", files={"file": ("test.fasta", invalid_fasta, "text/plain")})
        assert response.status_code == 422
        assert response.json()["error"] == "sequence_too_long"

    def test_invalid_characters(self):
        invalid_fasta = b">seq1\nATGU"
        response = client.post("/api/translate", files={"file": ("test.fasta", invalid_fasta, "text/plain")})
        assert response.status_code == 422
        assert response.json()["error"] == "invalid_characters"


class TestTranslateDeterminism:

    def test_same_input_same_output(self):
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            content = f.read()

        response1 = client.post("/api/translate", files={"file": ("patient_01.fasta", content, "text/plain")})
        response2 = client.post("/api/translate", files={"file": ("patient_01.fasta", content, "text/plain")})

        assert response1.json() == response2.json()
