"""Tests for variant extraction from aligned sequences."""
import pytest
from app.services.alignment import _extract_variants, _calculate_identity, align_sequences


class TestVariantExtraction:
    """Tests for variant extraction from hand-built aligned strings."""
    
    def test_single_snv(self):
        """Single SNV is detected at correct position."""
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
        """Multiple SNVs are detected."""
        ref = "ACGTACGT"
        query = "CCGTACAT"
        variants = _extract_variants(ref, query)
        
        assert len(variants) == 2
        assert variants[0] == {"position": 1, "ref": "A", "alt": "C", "type": "SNV"}
        assert variants[1] == {"position": 7, "ref": "G", "alt": "A", "type": "SNV"}
    
    def test_insertion_at_position_0(self):
        """Insertion before first base has position 0."""
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
        """Insertion in middle of sequence."""
        ref = "AC--GT"
        query = "ACAAGT"
        variants = _extract_variants(ref, query)
        
        assert len(variants) == 1
        assert variants[0] == {
            "position": 2,  # After position 2 (AC)
            "ref": "-",
            "alt": "AA",
            "type": "insertion"
        }
    
    def test_deletion_at_position_1(self):
        """Deletion starting at position 1."""
        ref = "AACGT"
        query = "A--GT"
        variants = _extract_variants(ref, query)
        
        assert len(variants) == 1
        assert variants[0] == {
            "position": 2,  # First deleted base (second A)
            "ref": "AC",
            "alt": "-",
            "type": "deletion"
        }
    
    def test_deletion_mid_sequence(self):
        """Deletion in middle of sequence."""
        ref = "ACGTACGT"
        query = "AC---CGT"
        variants = _extract_variants(ref, query)
        
        assert len(variants) == 1
        assert variants[0] == {
            "position": 3,  # First deleted base (G at position 3)
            "ref": "GTA",
            "alt": "-",
            "type": "deletion"
        }
    
    def test_multi_base_indel_grouped(self):
        """Multi-base insertion is one event."""
        ref = "AC-----GT"
        query = "ACAAAAAGT"
        variants = _extract_variants(ref, query)
        
        assert len(variants) == 1
        assert variants[0]["ref"] == "-"
        assert variants[0]["alt"] == "AAAAA"
        assert variants[0]["type"] == "insertion"
    
    def test_two_separate_indels(self):
        """Two separate indels are reported as separate events."""
        ref = "AC--GT--AA"
        query = "ACAAGTTAAA"
        variants = _extract_variants(ref, query)
        
        assert len(variants) == 2
        assert variants[0]["type"] == "insertion"
        assert variants[0]["alt"] == "AA"
        assert variants[1]["type"] == "insertion"
        assert variants[1]["alt"] == "TA"
    
    def test_adjacent_snv_and_indel(self):
        """SNV and indel next to each other."""
        ref = "ACGTA--CGT"
        query = "ACCTAAACGT"
        variants = _extract_variants(ref, query)
        
        # Should find SNV at position 3 (G->C) and insertion at position 5
        assert len(variants) == 2
        assert variants[0] == {"position": 3, "ref": "G", "alt": "C", "type": "SNV"}
        assert variants[1] == {"position": 5, "ref": "-", "alt": "AA", "type": "insertion"}
    
    def test_n_is_not_snv(self):
        """N vs any base is not called as an SNV."""
        ref = "ACNGT"
        query = "ACAGT"
        variants = _extract_variants(ref, query)
        
        assert len(variants) == 0
    
    def test_n_vs_n_not_snv(self):
        """N vs N is not an SNV."""
        ref = "ACNGT"
        query = "ACNGT"
        variants = _extract_variants(ref, query)
        
        assert len(variants) == 0
    
    def test_n_vs_different_base_not_snv(self):
        """N in query vs ACGT in ref is not an SNV."""
        ref = "ACAGT"
        query = "ACNGT"
        variants = _extract_variants(ref, query)
        
        assert len(variants) == 0
    
    def test_event_ordering(self):
        """Events are in alignment order (sorted by position)."""
        ref = "ACGT--A--CGT"
        query = "CCGTAAATTCGT"
        variants = _extract_variants(ref, query)
        
        # SNV at 1 (A->C), insertion at 4 (AA), insertion at 5 (TT)
        # Note: the last C vs C at the end is NOT an SNV
        assert len(variants) == 3
        positions = [v["position"] for v in variants]
        assert positions == sorted(positions)


class TestIdentityCalculation:
    """Tests for identity calculation."""
    
    def test_perfect_identity(self):
        """Identical sequences have identity 1.0."""
        identity = _calculate_identity("ACGT", "ACGT")
        assert identity == 1.0
    
    def test_one_mismatch(self):
        """One mismatch in 4 bases."""
        identity = _calculate_identity("ACGT", "ACCT")
        assert identity == 0.75  # 3/4
    
    def test_gap_in_denominator(self):
        """Gaps count in denominator but never match."""
        identity = _calculate_identity("AC-GT", "ACAGT")
        assert identity == 0.8  # 4 matches out of 5 total columns
    
    def test_n_in_denominator_no_match(self):
        """N counts in denominator but never matches."""
        identity = _calculate_identity("ACNGT", "ACNGT")
        assert identity == 0.8  # 4 matches (ACGT) out of 5
    
    def test_n_vs_base_no_match(self):
        """N vs ACGT base does not match."""
        identity = _calculate_identity("ACNGT", "ACAGT")
        assert identity == 0.8  # 4 matches (A, C, G, T) out of 5; N column doesn't match
    
    def test_gap_vs_base_no_match(self):
        """Gap vs base does not match."""
        identity = _calculate_identity("AC-GT", "ACAGT")
        assert identity == 0.8  # 4/5
    
    def test_all_gaps_zero_identity(self):
        """All gaps gives zero identity."""
        identity = _calculate_identity("-----", "ACGTA")
        assert identity == 0.0
    
    def test_empty_sequences(self):
        """Empty sequences."""
        identity = _calculate_identity("", "")
        assert identity == 0.0


class TestFullAlignment:
    """Tests for complete alignment pipeline."""
    
    def test_perfect_match(self):
        """Identical sequences."""
        ref = "ACGTACGT"
        query = "ACGTACGT"
        alignment, variants = align_sequences(ref, query)
        
        assert alignment["score"] == 8.0  # 8 matches * 1
        assert alignment["identity"] == 1.0
        assert len(variants) == 0
    
    def test_single_mismatch(self):
        """Single mismatch."""
        ref = "ACGTACGT"
        query = "ACCTACGT"
        alignment, variants = align_sequences(ref, query)
        
        # 7 matches (+7) + 1 mismatch (-1) = +6
        assert alignment["score"] == 6.0
        assert len(variants) == 1
        assert variants[0]["type"] == "SNV"
    
    def test_alignment_with_gap(self):
        """Alignment creates a gap."""
        ref = "ACGTACGT"
        query = "ACGTCGT"  # Missing an A
        alignment, variants = align_sequences(ref, query)
        
        # Score: 7 matches (+7) + 1 gap (-2) = +5
        assert alignment["score"] == 5.0
        assert len(variants) == 1
        assert variants[0]["type"] == "deletion"
    
    def test_n_handling(self):
        """N vs base scores 0."""
        ref = "ACGTACGT"
        query = "ACNTACGT"
        alignment, variants = align_sequences(ref, query)
        
        # 7 matches (+7) + 1 N (0) = +7
        assert alignment["score"] == 7.0
        assert len(variants) == 0  # N is not an SNV
        assert alignment["identity"] < 1.0  # N doesn't count as a match
    
    def test_aligned_sequences_correct_length(self):
        """Aligned sequences have same length."""
        ref = "ACGTACGT"
        query = "ACGTCGT"
        alignment, variants = align_sequences(ref, query)
        
        assert len(alignment["reference_aligned"]) == len(alignment["query_aligned"])
    
    def test_deterministic_output(self):
        """Same input gives same output (tie-breaking is deterministic)."""
        ref = "ACGTACGT"
        query = "ACCTACGT"
        
        alignment1, variants1 = align_sequences(ref, query)
        alignment2, variants2 = align_sequences(ref, query)
        
        assert alignment1["score"] == alignment2["score"]
        assert alignment1["identity"] == alignment2["identity"]
        assert variants1 == variants2
