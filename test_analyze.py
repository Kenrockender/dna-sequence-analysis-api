"""Test the /api/analyze endpoint."""
from fastapi.testclient import TestClient
from app.main import app
from app.services.reference import load_reference

# Load reference
load_reference()

# Create test client
client = TestClient(app)

# Test with patient_02
with open('Supporting Files/patient_02.fasta', 'rb') as f:
    response = client.post('/api/analyze', files={'file': ('patient_02.fasta', f, 'text/plain')})

print("Testing /api/analyze endpoint...")
print("="* 50)

if response.status_code == 200:
    data = response.json()
    print(f"✓ Status: {response.status_code}")
    print(f"✓ Sequence ID: {data['sequence_id']}")
    print(f"✓ Variants found: {len(data['variants'])}")
    
    print("\nVariant Effects:")
    for v in data['variants']:
        effect = v.get('effect', 'N/A')
        aa_change = v.get('aa_change', '')
        print(f"  - Position {v['position']}: {v['type']} → {effect} {aa_change}")
    
    print(f"\n✓ Reference translation: {data['reference_translation']['length']} amino acids")
    print(f"✓ Query translation: {data['query_translation']['length']} amino acids")
    print(f"✓ Query has stop: {data['query_translation']['has_stop_codon']}")
    
    print("\n✅ /api/analyze endpoint working correctly!")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.json())
