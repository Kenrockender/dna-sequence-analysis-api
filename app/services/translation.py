"""DNA to protein translation service."""
from typing import Dict
from Bio.Data import CodonTable


# Standard genetic code (NCBI table 1)
_codon_table = CodonTable.unambiguous_dna_by_id[1]


def translate_sequence(sequence: str, frame: int = 1) -> Dict:
    """
    Translate DNA sequence to protein in specified reading frame.
    
    Args:
        sequence: DNA sequence (uppercase ACGTN)
        frame: Reading frame 1, 2, or 3 (1-based)
        
    Returns:
        Dict with keys:
            - protein: amino acid sequence (may contain X for ambiguous codons)
            - length: length of protein
            - has_stop_codon: True if translation stopped at stop codon
            
    Rules:
        - Frame 1/2/3 means start at nucleotide 1/2/3 (1-based indexing)
        - Only complete codons are translated (trailing 1-2 nt ignored)
        - Any codon containing N becomes X (even if amino acid could be inferred)
        - Translation stops at first unambiguous stop codon (TAA, TAG, TGA)
        - Stop codon (*) is not included in the output
    """
    if frame not in (1, 2, 3):
        raise ValueError(f"Frame must be 1, 2, or 3, got {frame}")
    
    # Start position (0-indexed)
    start_pos = frame - 1
    
    # Extract sequence from frame start
    seq_from_frame = sequence[start_pos:]
    
    # Calculate number of complete codons
    num_codons = len(seq_from_frame) // 3
    
    if num_codons == 0:
        return {
            "protein": "",
            "length": 0,
            "has_stop_codon": False
        }
    
    protein = []
    has_stop = False
    
    for i in range(num_codons):
        codon = seq_from_frame[i*3:(i+1)*3]
        
        # Check if codon contains N
        if 'N' in codon:
            protein.append('X')
            continue
        
        # Check if it's a stop codon
        if codon in ('TAA', 'TAG', 'TGA'):
            has_stop = True
            break
        
        # Translate using Biopython codon table
        try:
            amino_acid = _codon_table.forward_table.get(codon)
            if amino_acid:
                protein.append(amino_acid)
            else:
                # This shouldn't happen with valid ACGT, but handle defensively
                protein.append('X')
        except KeyError:
            protein.append('X')
    
    protein_str = ''.join(protein)
    
    return {
        "protein": protein_str,
        "length": len(protein_str),
        "has_stop_codon": has_stop
    }
