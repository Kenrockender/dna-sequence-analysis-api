"""Tests for DNA to protein translation."""
import pytest
from app.services.translation import translate_sequence


class TestTranslationFrames:
    """Tests for different reading frames."""
    
    def test_frame_1(self):
        """Frame 1 starts at position 1 (index 0)."""
        # ATGCGT = ATG (M) + CGT (R)
        result = translate_sequence("ATGCGT", frame=1)
        assert result["protein"] == "MR"
        assert result["length"] == 2
        assert result["has_stop_codon"] is False
    
    def test_frame_2(self):
        """Frame 2 starts at position 2 (index 1)."""
        # xATGCGT -> ATG (M) + CGT (R)
        result = translate_sequence("CATGCGT", frame=2)
        assert result["protein"] == "MR"
        assert result["length"] == 2
    
    def test_frame_3(self):
        """Frame 3 starts at position 3 (index 2)."""
        # xxATGCGT -> ATG (M) + CGT (R)
        result = translate_sequence("CCATGCGT", frame=3)
        assert result["protein"] == "MR"
        assert result["length"] == 2
    
    def test_different_frames_different_proteins(self):
        """Same sequence in different frames produces different proteins."""
        seq = "ATGCGTAAA"
        # Frame 1: ATG CGT AAA -> M R K
        # Frame 2: (A)TGC GTA AA(x) -> C V
        # Frame 3: (AT)GCG TAA (Ax) -> A (stop)
        
        result1 = translate_sequence(seq, frame=1)
        result2 = translate_sequence(seq, frame=2)
        result3 = translate_sequence(seq, frame=3)
        
        assert result1["protein"] == "MRK"
        assert result2["protein"] == "CV"
        assert result3["protein"] == "A"
        assert result3["has_stop_codon"] is True


class TestIncompleteCodons:
    """Tests for sequences with trailing incomplete codons."""
    
    def test_trailing_1_nucleotide_ignored(self):
        """Sequence with 1 trailing nt: ignored."""
        # ATGCGTA = ATG CGT (A ignored)
        result = translate_sequence("ATGCGTA", frame=1)
        assert result["protein"] == "MR"
        assert result["length"] == 2
    
    def test_trailing_2_nucleotides_ignored(self):
        """Sequence with 2 trailing nt: ignored."""
        # ATGCGTAA = ATG CGT (AA ignored)
        result = translate_sequence("ATGCGTAA", frame=1)
        assert result["protein"] == "MR"
        assert result["length"] == 2
    
    def test_no_complete_codon_frame_1(self):
        """Sequence shorter than 3 nt in frame 1: empty protein."""
        result = translate_sequence("AT", frame=1)
        assert result["protein"] == ""
        assert result["length"] == 0
        assert result["has_stop_codon"] is False
    
    def test_no_complete_codon_frame_2(self):
        """Frame 2 with no complete codon after offset."""
        # Frame 2 starts at index 1, only 2 nt left
        result = translate_sequence("ATG", frame=2)
        assert result["protein"] == ""
        assert result["length"] == 0
        assert result["has_stop_codon"] is False
    
    def test_no_complete_codon_frame_3(self):
        """Frame 3 with no complete codon after offset."""
        # Frame 3 starts at index 2, only 1 nt left
        result = translate_sequence("ATG", frame=3)
        assert result["protein"] == ""
        assert result["length"] == 0
        assert result["has_stop_codon"] is False


class TestStopCodons:
    """Tests for stop codon handling."""
    
    def test_stop_at_taa(self):
        """TAA stops translation."""
        # ATG AAA TAA GGG -> M K (stop, GGG not translated)
        result = translate_sequence("ATGAAATAAGG G", frame=1)
        assert result["protein"] == "MK"
        assert result["has_stop_codon"] is True
    
    def test_stop_at_tag(self):
        """TAG stops translation."""
        # ATG AAA TAG GGG -> M K (stop)
        result = translate_sequence("ATGAAATAGGG G", frame=1)
        assert result["protein"] == "MK"
        assert result["has_stop_codon"] is True
    
    def test_stop_at_tga(self):
        """TGA stops translation."""
        # ATG AAA TGA GGG -> M K (stop)
        result = translate_sequence("ATGAAATGAGGG", frame=1)
        assert result["protein"] == "MK"
        assert result["has_stop_codon"] is True
    
    def test_stop_not_in_output(self):
        """Stop codon itself (*) is not in the protein output."""
        result = translate_sequence("ATGTAA", frame=1)
        assert result["protein"] == "M"
        assert "*" not in result["protein"]
    
    def test_no_stop_codon(self):
        """Sequence with no stop: has_stop_codon is False."""
        result = translate_sequence("ATGAAAGGG", frame=1)
        assert result["protein"] == "MKG"
        assert result["has_stop_codon"] is False
    
    def test_stop_as_first_codon(self):
        """Stop codon as first codon: empty protein."""
        result = translate_sequence("TAAATGAAA", frame=1)
        assert result["protein"] == ""
        assert result["length"] == 0
        assert result["has_stop_codon"] is True


class TestNNucleotides:
    """Tests for N (ambiguous nucleotide) handling."""
    
    def test_n_in_codon_becomes_x(self):
        """Any codon with N becomes X."""
        # ATGNAN -> M X
        result = translate_sequence("ATGNAN", frame=1)
        assert result["protein"] == "MX"
    
    def test_all_n_codon(self):
        """NNN becomes X."""
        result = translate_sequence("ATGNNN", frame=1)
        assert result["protein"] == "MX"
    
    def test_n_first_position(self):
        """N in first position of codon -> X."""
        result = translate_sequence("ATGNAA", frame=1)
        assert result["protein"] == "MX"
    
    def test_n_second_position(self):
        """N in second position of codon -> X."""
        result = translate_sequence("ATGANA", frame=1)
        assert result["protein"] == "MX"
    
    def test_n_third_position(self):
        """N in third position of codon -> X."""
        result = translate_sequence("ATGAAN", frame=1)
        assert result["protein"] == "MX"
    
    def test_ggn_becomes_x_not_g(self):
        """GGN could be inferred as G, but should become X per spec."""
        # All GGx codons code for Glycine (G), but with N we use X
        result = translate_sequence("ATGGGN", frame=1)
        assert result["protein"] == "MX"
        assert "G" not in result["protein"][1:]  # Second char should be X, not G
    
    def test_multiple_n_codons(self):
        """Multiple codons with N all become X."""
        result = translate_sequence("ATGNNNNAACNNGGG", frame=1)
        # ATG NNN NAA CNNGㅡ -> M X X X G
        assert result["protein"] == "MXXXG"
    
    def test_stop_with_n_not_a_stop(self):
        """TAN is not recognized as a stop codon (becomes X instead)."""
        # TAN could be TAA, TAT, TAG, TAC, but we don't know
        # So it becomes X and translation continues
        result = translate_sequence("ATGTANAAA", frame=1)
        assert result["protein"] == "MXK"
        assert result["has_stop_codon"] is False
    
    def test_tan_not_stop(self):
        """TAN specifically: not a stop, becomes X."""
        result = translate_sequence("TAN", frame=1)
        assert result["protein"] == "X"
        assert result["has_stop_codon"] is False
    
    def test_tgn_not_stop(self):
        """TGN: could be TGA (stop) or other, but N makes it X."""
        result = translate_sequence("TGNAAA", frame=1)
        assert result["protein"] == "XK"
        assert result["has_stop_codon"] is False


class TestRealSequences:
    """Tests with realistic codon sequences."""
    
    def test_standard_protein(self):
        """Standard translation without N or stops."""
        # ATG AAA GGG TTT CCC -> M K G F P
        seq = "ATGAAAGGGTTTCCC"
        result = translate_sequence(seq, frame=1)
        assert result["protein"] == "MKGFP"
        assert result["length"] == 5
        assert result["has_stop_codon"] is False
    
    def test_with_trailing_and_stop(self):
        """Complex case: stop codon with trailing nucleotides."""
        # ATG AAA TAG GG (trailing GG ignored, but stop hit first)
        result = translate_sequence("ATGAAATAGGG", frame=1)
        assert result["protein"] == "MK"
        assert result["has_stop_codon"] is True


class TestEdgeCases:
    """Edge cases and boundary conditions."""
    
    def test_empty_sequence(self):
        """Empty sequence."""
        result = translate_sequence("", frame=1)
        assert result["protein"] == ""
        assert result["length"] == 0
        assert result["has_stop_codon"] is False
    
    def test_single_nucleotide(self):
        """Single nucleotide."""
        result = translate_sequence("A", frame=1)
        assert result["protein"] == ""
        assert result["length"] == 0
    
    def test_exactly_three_nucleotides(self):
        """Exactly one codon."""
        result = translate_sequence("ATG", frame=1)
        assert result["protein"] == "M"
        assert result["length"] == 1
    
    def test_invalid_frame_raises(self):
        """Invalid frame number raises ValueError."""
        with pytest.raises(ValueError):
            translate_sequence("ATGAAA", frame=0)
        
        with pytest.raises(ValueError):
            translate_sequence("ATGAAA", frame=4)
