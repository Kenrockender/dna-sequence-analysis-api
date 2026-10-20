"""Quick verification that all services work."""
from app.services.reference import load_reference, get_reference
from app.services.fasta import parse_and_validate
from app.services.alignment import align_sequences
from app.services.translation import translate_sequence

print("🧬 DNA Sequence Analysis API - Verification")
print("=" * 50)

# Load reference
load_reference()
ref_id, ref_seq = get_reference()
print(f"✓ Reference loaded: {ref_id} ({len(ref_seq)} bp)")

# Test FASTA parsing
with open('Supporting Files/patient_01.fasta', 'rb') as f:
    seq_id, seq = parse_and_validate(f.read())
print(f"✓ FASTA parsing: {seq_id} ({len(seq)} bp)")

# Test alignment
aln, variants = align_sequences(ref_seq, seq)
print(f"✓ Alignment: score={aln['score']:.1f}, identity={aln['identity']:.3f}, variants={len(variants)}")

# Test translation
trans = translate_sequence(seq, 1)
print(f"✓ Translation: {trans['length']} amino acids, stop={trans['has_stop_codon']}")

print("\n✅ All core services working correctly!")
print("\nRun 'pytest -v' to execute 120 tests")
print("Run 'uvicorn app.main:app' to start the API server")
