from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.reference import load_reference

load_reference()
client = TestClient(app)
PATIENT_DIR = Path("static/samples")


@pytest.mark.parametrize("patient", [f"patient_{number:02d}" for number in range(1, 6)])
def test_translate_accepts_every_supplied_patient_file(patient: str):
    # semua file patient yang disediakan harus diterima endpoint translate
    content = (PATIENT_DIR / f"{patient}.fasta").read_bytes()

    response = client.post(
        "/api/translate",
        files={"file": (f"{patient}.fasta", content, "text/plain")},
        data={"frame": "1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sequence_id"] == patient
    assert body["frame"] == 1
    assert body["length"] == len(body["protein"])


@pytest.mark.parametrize("endpoint", ["/api/align", "/api/translate"])
def test_endpoints_normalize_lowercase_multiline_fasta(endpoint: str):
    # huruf kecil dan multiline harus tetap diterima
    response = client.post(
        endpoint,
        files={"file": ("lowercase.fasta", b">lowercase description\n atg\ncnn \n", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["sequence_id"] == "lowercase"


@pytest.mark.parametrize("endpoint", ["/api/align", "/api/translate"])
@pytest.mark.parametrize(
    ("content", "error_code"),
    [
        (b"ATGC", "no_header"),
        (b">first\nATG\n>second\nATG", "multiple_records"),
    ],
)
def test_endpoints_reject_malformed_fasta(endpoint: str, content: bytes, error_code: str):
    response = client.post(
        endpoint,
        files={"file": ("invalid.fasta", content, "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["error"] == error_code


@pytest.mark.parametrize("endpoint", ["/api/align", "/api/translate"])
def test_endpoints_enforce_sequence_length_limit(endpoint: str):
    content = b">too_long\n" + b"A" * 1001
    response = client.post(
        endpoint,
        files={"file": ("too_long.fasta", content, "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["error"] == "sequence_too_long"


def test_translate_endpoint_handles_n_codons_and_incomplete_final_codon():
    # N dalam kodon jadi X, kodon tidak lengkap di akhir diabaikan
    response = client.post(
        "/api/translate",
        files={"file": ("ambiguous.fasta", b">ambiguous\nATGNNNAA", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "sequence_id": "ambiguous",
        "frame": 1,
        "protein": "MX",
        "length": 2,
        "has_stop_codon": False,
    }


def test_analyze_endpoint_annotates_patient_02_effects():
    # patient_02 harusnya punya 3 varian dengan efek: synonymous, missense, nonsense
    content = (PATIENT_DIR / "patient_02.fasta").read_bytes()
    response = client.post(
        "/api/analyze",
        files={"file": ("patient_02.fasta", content, "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sequence_id"] == "patient_02"
    assert [v["effect"] for v in body["variants"]] == [
        "synonymous",
        "missense",
        "nonsense",
    ]


def test_analyze_endpoint_classifies_patient_03_indels():
    # patient_03 varian pertama frameshift, sisanya undetermined
    content = (PATIENT_DIR / "patient_03.fasta").read_bytes()
    response = client.post(
        "/api/analyze",
        files={"file": ("patient_03.fasta", content, "text/plain")},
    )

    assert response.status_code == 200
    effects = [v["effect"] for v in response.json()["variants"]]
    assert effects[0] == "frameshift"
    assert effects[1:] == ["undetermined", "undetermined"]
