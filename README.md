# DNA Sequence Analysis API

A REST API for DNA sequence alignment and protein translation, built with FastAPI and Biopython.

Repository: [github.com/Kenrockender/bioinformatics-test](https://github.com/Kenrockender/bioinformatics-test)

## Features

- **Sequence Alignment**: Align DNA sequences to a reference genome and identify variants (SNVs, insertions, deletions)
- **Protein Translation**: Translate DNA sequences to protein in reading frames 1-3
- **Robust Validation**: Comprehensive FASTA format validation with clear error messages
- **Well-Tested**: Automated tests cover the API contract, supplied samples, validation edge cases, and bonus analysis endpoint

## Installation

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

Interactive API documentation: `http://localhost:8000/docs`

## API Endpoints

### POST /api/align

Align a DNA sequence to the reference and report variants.

**Input**: FASTA file (multipart/form-data)

**Example**:
```bash
curl -X POST "http://localhost:8000/api/align" \
  -F "file=@patient_01.fasta"
```

**Response**:
```json
{
  "sequence_id": "patient_01",
  "reference_id": "REF_001",
  "alignment": {
    "score": 300.0,
    "identity": 1.0,
    "reference_aligned": "ATGAGTTCG...",
    "query_aligned": "ATGAGTTCG..."
  },
  "variants": []
}
```

### POST /api/translate

Translate DNA sequence to protein.

**Input**: 
- `file`: FASTA file (multipart/form-data)
- `frame`: Reading frame 1, 2, or 3 (form field, default: 1)

**Example**:
```bash
curl -X POST "http://localhost:8000/api/translate" \
  -F "file=@patient_01.fasta" \
  -F "frame=1"
```

**Response**:
```json
{
  "sequence_id": "patient_01",
  "frame": 1,
  "protein": "MSSSVPLLYVSRVGTSOQLFSLFTKFT...",
  "length": 99,
  "has_stop_codon": false
}
```

## FASTA Requirements

- Single sequence per file
- 1-1000 nucleotides
- Valid characters: A, C, G, T, N (case-insensitive)
- Standard FASTA format with header line starting with `>`

## Running Tests

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_align_api.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

**Test Results**:
```
136 passed, 3 warnings
```

**Test Breakdown**:
- ✅ 32 FASTA validation tests
- ✅ 31 translation tests (frames, stops, N handling)
- ✅ 27 alignment and variant extraction tests
- ✅ 13 align endpoint tests (all patient files)
- ✅ 17 translate endpoint tests
- ✅ 16 API-level requirement regression tests, including every supplied patient file and `/api/analyze`

All edge cases covered including N nucleotides, incomplete codons, stop codons, gaps, and error conditions.

## Alignment Scoring

- **Match**: +1
- **Mismatch**: -1
- **Gap (open and extend)**: -2 each
- **N vs any base**: 0

## Identity Calculation

```
Identity = (matching ACGT bases) / (total alignment columns)
```

Gap columns and N columns count in the denominator but never as matches.

## Coordinate System

All positions are **1-based**:
- **SNV**: Position is the reference position
- **Insertion**: Position is the preceding reference base (0 = before first base)
- **Deletion**: Position is the first deleted base

## Translation Rules

- Frame 1/2/3 = start at nucleotide 1/2/3 (1-based)
- Only complete codons translated (trailing 1-2 nt ignored)
- Any codon containing N becomes X
- Translation stops at first unambiguous stop codon (TAA, TAG, TGA)
- Stop codon (*) not included in output

## Error Handling

All validation errors return HTTP 422 with consistent JSON format:

```json
{
  "error": "error_code",
  "detail": "Human-readable error message"
}
```

Common error codes:
- `no_header`: Missing FASTA header
- `multiple_records`: More than one sequence in file
- `sequence_too_long`: Sequence exceeds 1000 nt
- `invalid_characters`: Non-ACGTN characters found
- `invalid_frame`: Frame not 1, 2, or 3

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration constants
│   ├── errors.py            # Custom exceptions
│   ├── schemas.py           # Pydantic response models
│   ├── routers/             # API endpoints
│   │   ├── align.py
│   │   └── translate.py
│   ├── services/            # Business logic
│   │   ├── fasta.py         # FASTA parsing
│   │   ├── reference.py     # Reference loading
│   │   ├── alignment.py     # Sequence alignment
│   │   └── translation.py   # DNA translation
│   └── data/
│       └── reference.fasta  # Reference sequence
├── tests/                   # Comprehensive test suite
├── requirements.txt
└── README.md
```

## Design Decisions

### Why FastAPI?
- Automatic API documentation via OpenAPI/Swagger
- Pydantic for data validation
- High performance with async support
- Easy to test with TestClient

### Why Biopython?
- Industry-standard bioinformatics library
- Well-tested PairwiseAligner implementation
- Reliable genetic code tables
- Saves development time on complex algorithms

### Architecture
- **Routers**: Handle HTTP requests/responses
- **Services**: Contain business logic (testable without HTTP)
- **Schemas**: Define API contracts with Pydantic

This separation allows comprehensive unit testing of business logic independent of the API layer.

## Assumptions

1. **Reading frames**: Frame 1/2/3 means starting at nucleotide position 1/2/3 of the input sequence (no start codon search)
2. **Stop codons**: Translation stops at first TAA/TAG/TGA; * is excluded from output
3. **Linear gap scoring**: Both gap open and gap extend penalties are -2
4. **End gaps**: Penalized (contribute to score)
5. **Tie-breaking**: When multiple optimal alignments exist, Biopython returns them in a deterministic order; we take the first

## Limitations

1. **N regions**: Indel placement within or adjacent to N runs is arbitrary
2. **Nearby variants**: Effect annotation (bonus feature) evaluates each variant independently
3. **Biopython dependency**: Core algorithms use Biopython rather than hand-written implementations

## Development

Built with clean git history showing incremental development:
1. Project skeleton and FASTA validation
2. Translation service
3. Alignment and variant extraction
4. API endpoints with error handling
5. Comprehensive test suite

All code follows Python best practices with type hints, docstrings, and clear separation of concerns.

## License

MIT License - Free for educational and commercial use.
