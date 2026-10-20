"""Tests for /api/align endpoint with all patient files."""
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


class TestAlignEndpoint:
    """Tests for /api/align endpoint."""
    
    def test_patient_01_perfect_match(self):
        """Patient 01: identical to reference."""
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
        """Patient 02: 3 SNVs, matches test example."""
        with open(PATIENT_DIR / "patient_02.fasta", "rb") as f:
            response = client.post("/api/align", files={"file": ("patient_02.fasta", f, "text/plain")})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["sequence_id"] == "patient_02"
        assert data["alignment"]["score"] == 294.0
        assert data["alignment"]["identity"] == 0.99  # 297 matches / 300 columns
        
        # Expected variants from plan
        variants = data["variants"]
        assert len(variants) == 3
        
        # SNV at position 52: C->A
        assert variants[0]["position"] == 52
        assert variants[0]["ref"] == "C"
        assert variants[0]["alt"] == "A"
        assert variants[0]["type"] == "SNV"
        
        # SNV at position 177: A->T
        assert variants[1]["position"] == 177
        assert variants[1]["ref"] == "A"
        assert variants[1]["alt"] == "T"
        assert variants[1]["type"] == "SNV"
        
        # SNV at position 245: T->G
        assert variants[2]["position"] == 245
        assert variants[2]["ref"] == "T"
        assert variants[2]["alt"] == "G"
        assert variants[2]["type"] == "SNV"
    
    def test_patient_03_two_deletions(self):
        """Patient 03: deletions."""
        with open(PATIENT_DIR / "patient_03.fasta", "rb") as f:
            response = client.post("/api/align", files={"file": ("patient_03.fasta", f, "text/plain")})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["sequence_id"] == "patient_03"
        # 296 nt sequence, 296 matches - 4 gaps * 2 = 288
        assert data["alignment"]["score"] == 288.0
        # 296 matches / 300 total alignment columns
        assert pytest.approx(data["alignment"]["identity"], 0.001) == 296.0 / 300.0
        
        variants = data["variants"]
        # All variants should be deletions
        assert all(v["type"] == "deletion" for v in variants)
        assert all(v["alt"] == "-" for v in variants)
        
        # Total deleted bases should be 4
        total_deleted = sum(len(v["ref"]) for v in variants)
        assert total_deleted == 4
    
    def test_patient_04_n_handling(self):
        """Patient 04: N runs, no SNVs called."""
        with open(PATIENT_DIR / "patient_04.fasta", "rb") as f:
            response = client.post("/api/align", files={"file": ("patient_04.fasta", f, "text/plain")})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["sequence_id"] == "patient_04"
        # N vs base scores 0, not -1, so score should be higher than if they were mismatches
        # Identity should be less than 1.0 because N doesn't match
        assert data["alignment"]["identity"] < 1.0
        # No variants because N is never an SNV
        assert len(data["variants"]) == 0
    
    def test_patient_05_two_insertions(self):
        """Patient 05: insertions."""
        with open(PATIENT_DIR / "patient_05.fasta", "rb") as f:
            response = client.post("/api/align", files={"file": ("patient_05.fasta", f, "text/plain")})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["sequence_id"] == "patient_05"
        # 304 nt sequence, 300 matches - 4 gaps * 2 = 292
        assert data["alignment"]["score"] == 292.0
        # 300 matches / 304 total columns
        assert pytest.approx(data["alignment"]["identity"], 0.001) == 300.0 / 304.0
        
        variants = data["variants"]
        # All variants should be insertions
        assert all(v["type"] == "insertion" for v in variants)
        assert all(v["ref"] == "-" for v in variants)
        
        # Total inserted bases should be 4
        total_inserted = sum(len(v["alt"]) for v in variants)
        assert total_inserted == 4


class TestAlignedSequencesInvariant:
    """Test that aligned sequences match original when gaps removed."""
    
    def test_patient_01_invariant(self):
        """Patient 01: aligned sequences equal original."""
        with open(PATIENT_DIR / "patient_01.fasta", "rb") as f:
            content = f.read()
        
        response = client.post("/api/align", files={"file": ("patient_01.fasta", content, "text/plain")})
        data = response.json()
        
        # Remove gaps from aligned sequences
        ref_no_gaps = data["alignment"]["reference_aligned"].replace("-", "")
        query_no_gaps = data["alignment"]["query_aligned"].replace("-", "")
        
        # Read original sequences
        from app.services.fasta import parse_and_validate
        _, query_original = parse_and_validate(content)
        from app.services.reference import get_reference
        _, ref_original = get_reference()
        
        assert ref_no_gaps == ref_original
        assert query_no_gaps == query_original
    
    def test_patient_02_invariant(self):
        """Patient 02: aligned sequences equal original."""
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
    """Test that alignment output is deterministic."""
    
    def test_same_input_same_output(self):
        """Same input produces identical output."""
        with open(PATIENT_DIR / "patient_02.fasta", "rb") as f:
            content = f.read()
        
        response1 = client.post("/api/align", files={"file": ("patient_02.fasta", content, "text/plain")})
        response2 = client.post("/api/align", files={"file": ("patient_02.fasta", content, "text/plain")})
        
        data1 = response1.json()
        data2 = response2.json()
        
        assert data1 == data2


class TestAlignErrors:
    """Test error handling for /api/align."""
    
    def test_missing_file(self):
        """Missing file returns 422."""
        response = client.post("/api/align")
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "detail" in data
    
    def test_invalid_fasta_multiple_records(self):
        """Multiple records in FASTA returns 422."""
        invalid_fasta = b">seq1\nACGT\n>seq2\nACGT"
        response = client.post("/api/align", files={"file": ("test.fasta", invalid_fasta, "text/plain")})
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "multiple_records"
    
    def test_invalid_fasta_no_header(self):
        """FASTA without header returns 422."""
        invalid_fasta = b"ACGTACGT"
        response = client.post("/api/align", files={"file": ("test.fasta", invalid_fasta, "text/plain")})
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "no_header"
    
    def test_sequence_too_long(self):
        """Sequence over 1000 nt returns 422."""
        long_seq = "A" * 1001
        invalid_fasta = f">seq1\n{long_seq}".encode()
        response = client.post("/api/align", files={"file": ("test.fasta", invalid_fasta, "text/plain")})
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "sequence_too_long"
    
    def test_invalid_characters(self):
        """Invalid characters return 422."""
        invalid_fasta = b">seq1\nACGTU"  # U is not allowed
        response = client.post("/api/align", files={"file": ("test.fasta", invalid_fasta, "text/plain")})
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "invalid_characters"
