from typing import List, Dict, Tuple
from Bio.Align import PairwiseAligner

from app.config import (
    MATCH_SCORE, MISMATCH_SCORE, GAP_OPEN_SCORE,
    GAP_EXTEND_SCORE, N_SCORE, VALID_NUCLEOTIDES
)


def _create_aligner() -> PairwiseAligner:
    import numpy as np
    from Bio.Align import substitution_matrices

    aligner = PairwiseAligner()
    aligner.mode = 'global'  # bandingkan seluruh sequence, bukan sebagian

    # bikin matriks skor untuk A, C, G, N, T
    alphabet = "ACGNT"

    matrix_data = []
    for i, base1 in enumerate(alphabet):
        row = []
        for j, base2 in enumerate(alphabet):
            if base1 == 'N' or base2 == 'N':
                # N vs apapun = netral, tidak dihitung mutasi
                row.append(N_SCORE)
            elif base1 == base2:
                row.append(MATCH_SCORE)
            else:
                row.append(MISMATCH_SCORE)
        matrix_data.append(row)

    matrix_array = np.array(matrix_data, dtype=float)
    sub_matrix = substitution_matrices.Array(alphabet=alphabet, dims=2, data=matrix_array)
    aligner.substitution_matrix = sub_matrix

    # penalty gap sama rata, tidak peduli panjang gapnya
    aligner.open_gap_score = GAP_OPEN_SCORE
    aligner.extend_gap_score = GAP_EXTEND_SCORE

    return aligner


def _extract_variants(ref_aligned: str, query_aligned: str) -> List[Dict]:
    variants = []
    ref_pos = 0  # posisi di referensi, akan jadi 1-based di output
    i = 0

    while i < len(ref_aligned):
        ref_base = ref_aligned[i]
        qry_base = query_aligned[i]

        if ref_base != '-' and qry_base != '-':
            # kedua sequence punya basa di posisi ini
            ref_pos += 1

            # SNV: basa berbeda dan keduanya bukan N
            if ref_base != qry_base and ref_base in 'ACGT' and qry_base in 'ACGT':
                variants.append({
                    "position": ref_pos,
                    "ref": ref_base,
                    "alt": qry_base,
                    "type": "SNV"
                })
            i += 1

        elif ref_base == '-':
            # referensi punya gap = query punya insertion
            ins_bases = []
            while i < len(ref_aligned) and ref_aligned[i] == '-':
                ins_bases.append(query_aligned[i])
                i += 1

            variants.append({
                "position": ref_pos,  # posisi basa sebelum insertion (0 = sebelum basa pertama)
                "ref": "-",
                "alt": ''.join(ins_bases),
                "type": "insertion"
            })

        else:
            # query punya gap = ada deletion di query
            del_start = ref_pos + 1
            del_bases = []
            while i < len(ref_aligned) and query_aligned[i] == '-':
                del_bases.append(ref_aligned[i])
                ref_pos += 1
                i += 1

            variants.append({
                "position": del_start,  # posisi basa pertama yang didelete
                "ref": ''.join(del_bases),
                "alt": "-",
                "type": "deletion"
            })

    return variants


def _calculate_identity(ref_aligned: str, query_aligned: str) -> float:
    if len(ref_aligned) != len(query_aligned):
        raise ValueError("Aligned sequences must have same length")

    if len(ref_aligned) == 0:
        return 0.0

    matches = 0
    total = len(ref_aligned)

    for r, q in zip(ref_aligned, query_aligned):
        # hanya hitung kalau kedua basa sama dan bukan gap/N
        if r == q and r in 'ACGT':
            matches += 1

    return matches / total


def align_sequences(reference_seq: str, query_seq: str) -> Tuple[Dict, List[Dict]]:
    aligner = _create_aligner()

    # jalankan alignment, ambil hasil pertama saja
    # jangan panggil len() pada alignments karena bisa sangat besar
    alignments = aligner.align(reference_seq, query_seq)
    best = next(iter(alignments))

    score = best.score

    # ambil string aligned dalam format FASTA
    formatted = format(best, 'fasta')
    lines = formatted.strip().split('\n')
    ref_aligned = lines[1]
    qry_aligned = lines[3]

    identity = _calculate_identity(ref_aligned, qry_aligned)
    variants = _extract_variants(ref_aligned, qry_aligned)

    info = {
        "score": float(score),
        "identity": identity,
        "reference_aligned": ref_aligned,
        "query_aligned": qry_aligned
    }

    return info, variants
