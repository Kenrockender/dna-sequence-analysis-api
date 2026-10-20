# Quick Start Guide - DNA Sequence Analysis API

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

## 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

This installs:
- FastAPI (web framework)
- Uvicorn (ASGI server)
- Biopython (bioinformatics algorithms)
- Pytest (testing framework)

### 2. Verify Installation
```bash
python verify.py
```

Expected output:
```
🧬 DNA Sequence Analysis API - Verification
==================================================
✓ Reference loaded: REF_001 (300 bp)
✓ FASTA parsing: patient_01 (300 bp)
✓ Alignment: score=300.0, identity=1.000, variants=0
✓ Translation: 99 amino acids, stop=True

✅ All core services working correctly!
```

### 3. Run Tests
```bash
pytest -v
```

All 120 tests should pass.

### 4. Start the API Server
```bash
uvicorn app.main:app --reload
```

Server starts at: `http://localhost:8000`

### 5. Try the API

**Open Interactive Docs**: `http://localhost:8000/docs`

**Or use curl**:

```bash
# Align a sequence
curl -X POST http://localhost:8000/api/align \
  -F "file=@Supporting Files/patient_02.fasta"

# Translate a sequence  
curl -X POST http://localhost:8000/api/translate \
  -F "file=@Supporting Files/patient_01.fasta" \
  -F "frame=1"
```

## Quick Test with All Patient Files

```bash
# Test all patients with alignment
for i in 01 02 03 04 05; do
  echo "Testing patient_$i..."
  curl -X POST http://localhost:8000/api/align \
    -F "file=@Supporting Files/patient_$i.fasta" \
    -s | python -m json.tool | head -n 20
done
```

## Docker (Optional)

```bash
# Build image
docker build -t dna-api .

# Run container
docker run -p 8000:8000 dna-api
```

## Expected Results

### Patient 01 (Perfect Match)
- Score: 300.0
- Identity: 1.0
- Variants: 0

### Patient 02 (3 SNVs)
- Score: 294.0
- Identity: 0.99
- Variants: 3 (positions 52, 177, 245)

### Patient 03 (Deletions)
- Score: 288.0
- Identity: 0.987
- Variants: Deletions totaling 4 bp

### Patient 04 (N regions)
- Identity: <1.0
- Variants: 0 (N is not called as SNV)

### Patient 05 (Insertions)
- Score: 292.0
- Identity: 0.987
- Variants: Insertions totaling 4 bp

## Common Issues

### Issue: "Module not found"
**Solution**: Make sure you're in the project directory and dependencies are installed:
```bash
pip install -r requirements.txt
```

### Issue: "Port 8000 already in use"
**Solution**: Use a different port:
```bash
uvicorn app.main:app --port 8001
```

### Issue: Tests fail with "Reference not loaded"
**Solution**: This shouldn't happen, but if it does, restart Python:
```bash
python -c "from app.services.reference import load_reference; load_reference()"
pytest -v
```

## API Endpoints Summary

| Endpoint | Method | Purpose | Required | Optional |
|----------|--------|---------|----------|----------|
| `/api/align` | POST | Align sequence to reference | `file` | - |
| `/api/translate` | POST | Translate DNA to protein | `file` | `frame` (1-3) |
| `/` | GET | API information | - | - |
| `/docs` | GET | Interactive API docs | - | - |

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Check [SUBMISSION_SUMMARY.md](SUBMISSION_SUMMARY.md) for design decisions
- Explore `/docs` for interactive API testing
- Review test files in `tests/` for usage examples

## Questions?

Check the README.md for:
- FASTA requirements
- Coordinate system explanation
- Translation rules
- Error handling details
- Architecture overview

---

**Estimated time to get started**: 5 minutes  
**Full test suite runtime**: <1 second  
**All features working**: ✅
