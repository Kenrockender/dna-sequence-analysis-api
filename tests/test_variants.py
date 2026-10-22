import pytest
from app.services.alignment import _extract_variants, _calculate_identity, align_sequences


class TestVariantExtraction:

    def test_single_snv(self):
        # SNV tunggal harus ketahuan di posisi yang benar
        ref = "ACGT"
        query = "ACCT"
        variants = _extract_variants(ref, query)

        assert len(variants) == 1
        assert variants[0] == {
            "position": 3,
            "ref": "G",
            "alt": "C",
            "type": "SNV"
        }

    def test_multiple_snvs(self):
        ref = "ACGTACGT"
        query = "CCGTACAT"
        variants = _extract_variants(ref, query)

        assert len(variants) == 2
        assert variants[0] == {"position": 1, "ref": "A", "alt": "C", "type": "SNV"}
        assert variants[1] == {"position": 7, "ref": "G", "alt": "A", "type": "SNV"}

    def test_insertion_at_position_0(self):
        # insertion sebelum basa pertama, posisinya 0
        ref = "---ACGT"
        query = "AAAACGT"
        variants = _extract_variants(ref, query)

        assert len(variants) == 1
        assert variants[0] == {
            "position": 0,
            "ref": "-",
            "alt": "AAA",
            "type": "insertion"
        }

    def test_insertion_mid_sequence(self):
        ref = "AC--GT"
        query = "ACAAGT"
        variants = _extract_variants(ref, query)

        assert len(variants) == 1
        assert variants[0] == {
            "position": 2,
            "ref": "-",
            "alt": "AA",
            "type": "insertion"
        }

    def test_deletion_at_position_1(self):
        ref = "AACGT"
        query = "A--GT"
        variants = _extract_variants(ref, query)

        assert len(variants) == 1
        assert variants[0] == {
            "position": 2,
            "ref": "AC",
            "alt": "-",
            "type": "deletion"
        }

    def test_deletion_mid_sequence(self):
        ref = "ACGTACGT"
        query = "AC---CGT"
        variants = _extract_variants(ref, query)

        assert len(variants) == 1
        assert variants[0] == {
            "position": 3,
            "ref": "GTA",
            "alt": "-",
            "type": "deletion"
        }

    def test_multi_base_indel_grouped(self):
        # insertion multi-basa dihitung satu event
        ref = "AC-----GT"
        query = "ACAAAAAGT"
        variants = _extract_variants(ref, query)

        assert len(variants) == 1
        assert variants[0]["ref"] == "-"
        assert variants[0]["alt"] == "AAAAA"
        assert variants[0]["type"] == "insertion"

    def test_two_separate_indels(self):
        # dua indel terpisah harus dilaporkan sebagai dua event
        ref = "AC--GT--AA"
        query = "ACAAGTTAAA"
        variants = _extract_variants(ref, query)

        assert len(variants) == 2
        assert variants[0]["type"] == "insertion"
        assert variants[0]["alt"] == "AA"
        assert variants[1]["type"] == "insertion"
        assert variants[1]["alt"] == "TA"

    def test_adjacent_snv_and_indel(self):
        ref = "ACGTA--CGT"
        query = "ACCTAAACGT"
        variants = _extract_variants(ref, query)

        assert len(variants) == 2
        assert variants[0] == {"position": 3, "ref": "G", "alt": "C", "type": "SNV"}
        assert variants[1] == {"position": 5, "ref": "-", "alt": "AA", "type": "insertion"}

    def test_n_is_not_snv(self):
        # N vs basa apapun bukan SNV
        ref = "ACNGT"
        query = "ACAGT"
        variants = _extract_variants(ref, query)

        assert len(variants) == 0

    def test_n_vs_n_not_snv(self):
        ref = "ACNGT"
        query = "ACNGT"
        variants = _extract_variants(ref, query)

        assert len(variants) == 0

    def test_n_vs_different_base_not_snv(self):
        ref = "ACAGT"
        query = "ACNGT"
        variants = _extract_variants(ref, query)

        assert len(variants) == 0

    def test_event_ordering(self):
        # urutan event harus sesuai posisi di alignment
        ref = "ACGT--A--CGT"
        query = "CCGTAAATTCGT"
        variants = _extract_variants(ref, query)

        assert len(variants) == 3
        positions = [v["position"] for v in variants]
        assert positions == sorted(positions)


class TestIdentityCalculation:

    def test_perfect_identity(self):
        identity = _calculate_identity("ACGT", "ACGT")
        assert identity == 1.0

    def test_one_mismatch(self):
        # 3 dari 4 basa cocok
        identity = _calculate_identity("ACGT", "ACCT")
        assert identity == 0.75

    def test_gap_in_denominator(self):
        # gap masuk denominator tapi tidak dihitung match
        identity = _calculate_identity("AC-GT", "ACAGT")
        assert identity == 0.8

    def test_n_in_denominator_no_match(self):
        # N masuk denominator tapi tidak dihitung match
        identity = _calculate_identity("ACNGT", "ACNGT")
        assert identity == 0.8

    def test_n_vs_base_no_match(self):
        identity = _calculate_identity("ACNGT", "ACAGT")
        assert identity == 0.8

    def test_gap_vs_base_no_match(self):
        identity = _calculate_identity("AC-GT", "ACAGT")
        assert identity == 0.8

    def test_all_gaps_zero_identity(self):
        identity = _calculate_identity("-----", "ACGTA")
        assert identity == 0.0

    def test_empty_sequences(self):
        identity = _calculate_identity("", "")
        assert identity == 0.0


class TestFullAlignment:

    def test_perfect_match(self):
        ref = "ACGTACGT"
        query = "ACGTACGT"
        aln, variants = align_sequences(ref, query)

        assert aln["score"] == 8.0
        assert aln["identity"] == 1.0
        assert len(variants) == 0

    def test_single_mismatch(self):
        # 7 match (+7) + 1 mismatch (-1) = 6
        ref = "ACGTACGT"
        query = "ACCTACGT"
        aln, variants = align_sequences(ref, query)

        assert aln["score"] == 6.0
        assert len(variants) == 1
        assert variants[0]["type"] == "SNV"

    def test_alignment_with_gap(self):
        # 7 match (+7) + 1 gap (-2) = 5
        ref = "ACGTACGT"
        query = "ACGTCGT"
        aln, variants = align_sequences(ref, query)

        assert aln["score"] == 5.0
        assert len(variants) == 1
        assert variants[0]["type"] == "deletion"

    def test_n_handling(self):
        # N vs basa lain skor 0, dan tidak dihitung sebagai SNV
        ref = "ACGTACGT"
        query = "ACNTACGT"
        aln, variants = align_sequences(ref, query)

        assert aln["score"] == 7.0
        assert len(variants) == 0
        assert aln["identity"] < 1.0

    def test_aligned_sequences_correct_length(self):
        # panjang aligned sequence harus sama
        ref = "ACGTACGT"
        query = "ACGTCGT"
        aln, variants = align_sequences(ref, query)

        assert len(aln["reference_aligned"]) == len(aln["query_aligned"])

    def test_deterministic_output(self):
        # input sama harus selalu menghasilkan output yang sama
        ref = "ACGTACGT"
        query = "ACCTACGT"

        aln1, variants1 = align_sequences(ref, query)
        aln2, variants2 = align_sequences(ref, query)

        assert aln1["score"] == aln2["score"]
        assert aln1["identity"] == aln2["identity"]
        assert variants1 == variants2
