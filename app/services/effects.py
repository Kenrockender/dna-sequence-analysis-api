from typing import List, Dict
from Bio.Data import CodonTable

from app.services.translation import translate_sequence

# tabel kodon standar
_codon_table = CodonTable.unambiguous_dna_by_id[1]


def annotate_variant_effects(reference_seq: str, query_seq: str, variants: List[Dict]) -> List[Dict]:
    # terjemahkan dulu kedua sequence di frame 1 untuk perbandingan
    ref_protein = translate_sequence(reference_seq, frame=1)["protein"]
    qry_protein = translate_sequence(query_seq, frame=1)["protein"]

    # lacak apakah sudah terjadi frameshift sebelumnya
    frameshift_offset = 0

    annotated = []

    for v in variants:
        item = v.copy()
        pos = v["position"]
        vtype = v["type"]

        # kalau sudah ada frameshift sebelumnya, varian ini tidak bisa ditentukan efeknya
        if frameshift_offset != 0:
            item["effect"] = "undetermined"
            item["notes"] = f"downstream of frameshift (offset {frameshift_offset})"
            annotated.append(item)
            continue

        if vtype == "SNV":
            # cari kodon mana yang kena SNV ini
            nt_idx = pos - 1           # konversi ke 0-based
            codon_num = nt_idx // 3    # index kodon (0-based)
            pos_in_codon = nt_idx % 3  # posisi dalam kodon

            codon_start = codon_num * 3
            ref_codon = reference_seq[codon_start:codon_start + 3]

            # bangun kodon alternatif dengan mengganti satu basa
            alt_codon = (
                ref_codon[:pos_in_codon] +
                v["alt"] +
                ref_codon[pos_in_codon + 1:]
            )

            # kalau ada N, tidak bisa ditentukan efeknya
            if 'N' in ref_codon or 'N' in alt_codon:
                item["effect"] = "undetermined"
                item["notes"] = "codon contains N"
                item["codon"] = codon_num + 1
                annotated.append(item)
                continue

            try:
                ref_aa = _codon_table.forward_table.get(ref_codon, None)
                alt_aa = _codon_table.forward_table.get(alt_codon, None)

                ref_is_stop = ref_codon in ('TAA', 'TAG', 'TGA')
                alt_is_stop = alt_codon in ('TAA', 'TAG', 'TGA')

                if ref_is_stop:
                    ref_aa = '*'
                if alt_is_stop:
                    alt_aa = '*'

                # tentukan tipe efek berdasarkan perubahan asam amino
                if ref_aa == alt_aa:
                    effect = "synonymous"       # basa berubah tapi protein sama
                elif alt_is_stop and not ref_is_stop:
                    effect = "nonsense"         # muncul stop codon baru
                elif ref_is_stop and not alt_is_stop:
                    effect = "stop_lost"        # stop codon hilang
                else:
                    effect = "missense"         # asam amino berubah

                item["effect"] = effect
                item["codon"] = codon_num + 1
                item["ref_codon"] = ref_codon
                item["alt_codon"] = alt_codon
                item["ref_aa"] = ref_aa if ref_aa else '*'
                item["alt_aa"] = alt_aa if alt_aa else '*'

                # buat notasi perubahan, contoh: K59N
                if effect in ("missense", "nonsense", "stop_lost"):
                    item["aa_change"] = f"{ref_aa}{codon_num + 1}{alt_aa}"

            except (KeyError, IndexError):
                item["effect"] = "undetermined"
                item["notes"] = "error translating codon"

        elif vtype in ("insertion", "deletion"):
            length = len(v["alt"]) if vtype == "insertion" else len(v["ref"])

            if length % 3 == 0:
                # panjang kelipatan 3, reading frame tidak bergeser
                item["effect"] = "inframe_insertion" if vtype == "insertion" else "inframe_deletion"
            else:
                # panjang bukan kelipatan 3, reading frame bergeser
                item["effect"] = "frameshift"
                if vtype == "insertion":
                    frameshift_offset = (frameshift_offset + length) % 3
                else:
                    frameshift_offset = (frameshift_offset - length) % 3

        annotated.append(item)

    return annotated
