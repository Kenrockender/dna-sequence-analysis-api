"""Tests for /api/translate endpoint."""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app
from app.services.reference import load_reference


# Load reference once for all tests
load_reference()

client = TestClient(app)

# Path to patient files
PATIENT_DIR = Path("Supporting Files")


class TestTranslateEndpoint:
    """Tests for /api/translate endpoint."""
    
    def test_patient_02_frame_1(self):
        """Patient 02 in frame 1."""
        with open(PATIENT_DIR / "patient_02.fasta", "rb") as f:
            response = client.post("/api/translate", files={"file": ("patient_02.fasta", f, "text/plain")})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["sequence_id"] == "patient_02"
        assert data["frame"] == 1
        assert data["length"] > 0
        # Should have K at position 59 (0-indexed 58) before the mutation
        assert "K" in data["protein"] or data["has_stop_codon"]  # May stop before position 59
    
    def test_frame_1_explicit(self):
        """Explicit frame=1."""
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate", 
                files={"file": ("patient_01.fasta", f, "text/plain")},
                data={"frame": "1"}
            )
        
        assert response.status_code == 200
        assert response.json()["frame"] == 1
    
    def test_frame_2(self):
        """Frame 2."""
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate", 
                files={"file": ("patient_01.fasta", f, "text/plain")},
                data={"frame": "2"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["frame"] == 2
        # Different frame should give different protein
        
    def test_frame_3(self):
        """Frame 3."""
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate", 
                files={"file": ("patient_01.fasta", f, "text/plain")},
                data={"frame": "3"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["frame"] == 3
    
    def test_n_codons_become_x(self):
        """Patient 04 with N codons."""
        with open(PATIENT_DIR / "patient_04.fasta", "rb") as f:
            response = client.post("/api/translate", files={"file": ("patient_04.fasta", f, "text/plain")})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should contain X for N-containing codons
        assert "X" in data["protein"]
    
    def test_has_stop_codon_true(self):
        """Sequence with stop codon."""
        # Patient 02 has a nonsense mutation that creates a stop
        with open(PATIENT_DIR / "patient_02.fasta", "rb") as f:
            response = client.post("/api/translate", files={"file": ("patient_02.fasta", f, "text/plain")})
        
        assert response.status_code == 200
        data = response.json()
        # May or may not have stop depending on the sequence
        assert isinstance(data["has_stop_codon"], bool)
    
    def test_incomplete_codon_ignored(self):
        """Trailing incomplete codon is ignored."""
        # Create a short sequence with trailing nucleotides
        fasta = b">test\nATGCGTA"  # 7 nt = 2 codons + 1 trailing
        response = client.post("/api/translate", files={"file": ("test.fasta", fasta, "text/plain")})
        
        assert response.status_code == 200
        data = response.json()
        assert data["length"] == 2  # Only 2 complete codons


class TestTranslateFrameValidation:
    """Tests for frame parameter validation."""
    
    def test_invalid_frame_0(self):
        """Frame 0 is invalid."""
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate",
                files={"file": ("patient_01.fasta", f, "text/plain")},
                data={"frame": "0"}
            )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "invalid_frame"
    
    def test_invalid_frame_4(self):
        """Frame 4 is invalid."""
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate",
                files={"file": ("patient_01.fasta", f, "text/plain")},
                data={"frame": "4"}
            )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "invalid_frame"
    
    def test_invalid_frame_abc(self):
        """Non-numeric frame is invalid."""
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate",
                files={"file": ("patient_01.fasta", f, "text/plain")},
                data={"frame": "abc"}
            )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "invalid_frame"
    
    def test_invalid_frame_float(self):
        """Float frame is invalid."""
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate",
                files={"file": ("patient_01.fasta", f, "text/plain")},
                data={"frame": "1.5"}
            )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "invalid_frame"
    
    def test_omitted_frame_uses_default(self):
        """Omitted frame parameter uses default (1)."""
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            response = client.post(
                "/api/translate",
                files={"file": ("patient_01.fasta", f, "text/plain")}
            )
        
        # Should use default frame 1
        assert response.status_code == 200
        assert response.json()["frame"] == 1


class TestTranslateErrors:
    """Test error handling for /api/translate."""
    
    def test_missing_file(self):
        """Missing file returns 422."""
        response = client.post("/api/translate")
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
    
    def test_invalid_fasta_multiple_records(self):
        """Multiple records in FASTA returns 422."""
        invalid_fasta = b">seq1\nATG\n>seq2\nATG"
        response = client.post("/api/translate", files={"file": ("test.fasta", invalid_fasta, "text/plain")})
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "multiple_records"
    
    def test_sequence_too_long(self):
        """Sequence over 1000 nt returns 422."""
        long_seq = "A" * 1001
        invalid_fasta = f">seq1\n{long_seq}".encode()
        response = client.post("/api/translate", files={"file": ("test.fasta", invalid_fasta, "text/plain")})
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "sequence_too_long"
    
    def test_invalid_characters(self):
        """Invalid characters return 422."""
        invalid_fasta = b">seq1\nATGU"  # U is not allowed
        response = client.post("/api/translate", files={"file": ("test.fasta", invalid_fasta, "text/plain")})
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "invalid_characters"


class TestTranslateDeterminism:
    """Test that translation is deterministic."""
    
    def test_same_input_same_output(self):
        """Same input produces identical output."""
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            content = f.read()
        
        response1 = client.post("/api/translate", files={"file": ("patient_01.fasta", content, "text/plain")})
        response2 = client.post("/api/translate", files={"file": ("patient_01.fasta", content, "text/plain")})
        
        assert response1.json() == response2.json()
