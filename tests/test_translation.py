import pytest
from app.services.translation import translate_sequence


class TestTranslationFrames:

    def test_frame_1(self):
        # frame 1 mulai dari index 0
        result = translate_sequence("ATGCGT", frame=1)
        assert result["protein"] == "MR"
        assert result["length"] == 2
        assert result["has_stop_codon"] is False

    def test_frame_2(self):
        # frame 2 mulai dari index 1, karakter pertama dilewati
        result = translate_sequence("CATGCGT", frame=2)
        assert result["protein"] == "MR"
        assert result["length"] == 2

    def test_frame_3(self):
        # frame 3 mulai dari index 2
        result = translate_sequence("CCATGCGT", frame=3)
        assert result["protein"] == "MR"
        assert result["length"] == 2

    def test_different_frames_different_proteins(self):
        # sequence yang sama di frame berbeda hasilnya beda
        seq = "ATGCGTAAA"
        result1 = translate_sequence(seq, frame=1)
        result2 = translate_sequence(seq, frame=2)
        result3 = translate_sequence(seq, frame=3)

        assert result1["protein"] == "MRK"
        assert result2["protein"] == "CV"
        assert result3["protein"] == "A"
        assert result3["has_stop_codon"] is True


class TestIncompleteCodons:

    def test_trailing_1_nucleotide_ignored(self):
        # sisa 1 nukleotida di akhir diabaikan
        result = translate_sequence("ATGCGTA", frame=1)
        assert result["protein"] == "MR"
        assert result["length"] == 2

    def test_trailing_2_nucleotides_ignored(self):
        # sisa 2 nukleotida di akhir juga diabaikan
        result = translate_sequence("ATGCGTAA", frame=1)
        assert result["protein"] == "MR"
        assert result["length"] == 2

    def test_no_complete_codon_frame_1(self):
        # kurang dari 3 nukleotida, tidak ada kodon lengkap
        result = translate_sequence("AT", frame=1)
        assert result["protein"] == ""
        assert result["length"] == 0
        assert result["has_stop_codon"] is False

    def test_no_complete_codon_frame_2(self):
        result = translate_sequence("ATG", frame=2)
        assert result["protein"] == ""
        assert result["length"] == 0
        assert result["has_stop_codon"] is False

    def test_no_complete_codon_frame_3(self):
        result = translate_sequence("ATG", frame=3)
        assert result["protein"] == ""
        assert result["length"] == 0
        assert result["has_stop_codon"] is False


class TestStopCodons:

    def test_stop_at_taa(self):
        # TAA adalah stop codon, translasi berhenti di sini
        result = translate_sequence("ATGAAATAAGG G", frame=1)
        assert result["protein"] == "MK"
        assert result["has_stop_codon"] is True

    def test_stop_at_tag(self):
        result = translate_sequence("ATGAAATAGGG G", frame=1)
        assert result["protein"] == "MK"
        assert result["has_stop_codon"] is True

    def test_stop_at_tga(self):
        result = translate_sequence("ATGAAATGAGGG", frame=1)
        assert result["protein"] == "MK"
        assert result["has_stop_codon"] is True

    def test_stop_not_in_output(self):
        # stop codon tidak dimasukkan ke hasil protein
        result = translate_sequence("ATGTAA", frame=1)
        assert result["protein"] == "M"
        assert "*" not in result["protein"]

    def test_no_stop_codon(self):
        result = translate_sequence("ATGAAAGGG", frame=1)
        assert result["protein"] == "MKG"
        assert result["has_stop_codon"] is False

    def test_stop_as_first_codon(self):
        # stop codon di posisi pertama, protein kosong
        result = translate_sequence("TAAATGAAA", frame=1)
        assert result["protein"] == ""
        assert result["length"] == 0
        assert result["has_stop_codon"] is True


class TestNNucleotides:

    def test_n_in_codon_becomes_x(self):
        # kodon yang ada N-nya jadi X
        result = translate_sequence("ATGNAN", frame=1)
        assert result["protein"] == "MX"

    def test_all_n_codon(self):
        result = translate_sequence("ATGNNN", frame=1)
        assert result["protein"] == "MX"

    def test_n_first_position(self):
        result = translate_sequence("ATGNAA", frame=1)
        assert result["protein"] == "MX"

    def test_n_second_position(self):
        result = translate_sequence("ATGANA", frame=1)
        assert result["protein"] == "MX"

    def test_n_third_position(self):
        result = translate_sequence("ATGAAN", frame=1)
        assert result["protein"] == "MX"

    def test_ggn_becomes_x_not_g(self):
        # GGN sebenarnya bisa disimpulkan G, tapi per spec tetap jadi X
        result = translate_sequence("ATGGGN", frame=1)
        assert result["protein"] == "MX"
        assert "G" not in result["protein"][1:]

    def test_multiple_n_codons(self):
        result = translate_sequence("ATGNNNNAACNNGGG", frame=1)
        assert result["protein"] == "MXXXG"

    def test_stop_with_n_not_a_stop(self):
        # TAN bukan stop codon karena ada N, jadi X dan translasi lanjut
        result = translate_sequence("ATGTANAAA", frame=1)
        assert result["protein"] == "MXK"
        assert result["has_stop_codon"] is False

    def test_tan_not_stop(self):
        result = translate_sequence("TAN", frame=1)
        assert result["protein"] == "X"
        assert result["has_stop_codon"] is False

    def test_tgn_not_stop(self):
        # TGN bisa jadi TGA (stop) tapi karena ada N, jadi X
        result = translate_sequence("TGNAAA", frame=1)
        assert result["protein"] == "XK"
        assert result["has_stop_codon"] is False


class TestRealSequences:

    def test_standard_protein(self):
        seq = "ATGAAAGGGTTTCCC"
        result = translate_sequence(seq, frame=1)
        assert result["protein"] == "MKGFP"
        assert result["length"] == 5
        assert result["has_stop_codon"] is False

    def test_with_trailing_and_stop(self):
        result = translate_sequence("ATGAAATAGGG", frame=1)
        assert result["protein"] == "MK"
        assert result["has_stop_codon"] is True


class TestEdgeCases:

    def test_empty_sequence(self):
        result = translate_sequence("", frame=1)
        assert result["protein"] == ""
        assert result["length"] == 0
        assert result["has_stop_codon"] is False

    def test_single_nucleotide(self):
        result = translate_sequence("A", frame=1)
        assert result["protein"] == ""
        assert result["length"] == 0

    def test_exactly_three_nucleotides(self):
        result = translate_sequence("ATG", frame=1)
        assert result["protein"] == "M"
        assert result["length"] == 1

    def test_invalid_frame_raises(self):
        # frame di luar 1-3 harus raise error
        with pytest.raises(ValueError):
            translate_sequence("ATGAAA", frame=0)

        with pytest.raises(ValueError):
            translate_sequence("ATGAAA", frame=4)
