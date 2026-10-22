from typing import Dict
from Bio.Data import CodonTable

# pakai tabel kodon standar NCBI nomor 1
_codon_table = CodonTable.unambiguous_dna_by_id[1]


def translate_sequence(sequence: str, frame: int = 1) -> Dict:
    if frame not in (1, 2, 3):
        raise ValueError(f"Frame must be 1, 2, or 3, got {frame}")

    # frame 1 mulai dari index 0, frame 2 dari index 1, dst
    start = frame - 1
    seq = sequence[start:]

    # hitung berapa kodon lengkap yang bisa dibaca
    num_codons = len(seq) // 3

    if num_codons == 0:
        return {"protein": "", "length": 0, "has_stop_codon": False}

    protein = []
    has_stop = False

    for i in range(num_codons):
        codon = seq[i * 3:(i + 1) * 3]

        # kalau ada N dalam kodon, hasilnya X (tidak diketahui)
        if 'N' in codon:
            protein.append('X')
            continue

        # kalau ketemu stop codon, berhenti
        if codon in ('TAA', 'TAG', 'TGA'):
            has_stop = True
            break

        # terjemahkan pakai tabel Biopython
        try:
            aa = _codon_table.forward_table.get(codon)
            if aa:
                protein.append(aa)
            else:
                protein.append('X')
        except KeyError:
            protein.append('X')

    protein_str = ''.join(protein)

    return {
        "protein": protein_str,
        "length": len(protein_str),
        "has_stop_codon": has_stop
    }
