"""Sequence alignment and variant calling service."""
from typing import List, Dict, Tuple
from Bio.Align import PairwiseAligner

from app.config import (
    MATCH_SCORE, MISMATCH_SCORE, GAP_OPEN_SCORE, 
    GAP_EXTEND_SCORE, N_SCORE, VALID_NUCLEOTIDES
)


def _create_aligner() -> PairwiseAligner:
    """Create and configure a PairwiseAligner with custom scoring."""
    import numpy as np
    from Bio.Align import substitution_matrices
    
    aligner = PairwiseAligner()
    aligner.mode = 'global'
    
    # Create custom substitution matrix for ACGTN
    # N vs anything (including N) scores 0
    # Otherwise: match = +1, mismatch = -1
    alphabet = "ACGNT"  # Must be a string for Bio.Align
    
    # Build 2D matrix as numpy array
    size = len(alphabet)
    matrix_data = []
    for i, base1 in enumerate(alphabet):
        row = []
        for j, base2 in enumerate(alphabet):
            if base1 == 'N' or base2 == 'N':
                # N vs anything = 0
                row.append(N_SCORE)
            elif base1 == base2:
                # Match
                row.append(MATCH_SCORE)
            else:
                # Mismatch
                row.append(MISMATCH_SCORE)
        matrix_data.append(row)
    
    # Create Array from numpy array
    matrix_array = np.array(matrix_data, dtype=float)
    substitution_matrix = substitution_matrices.Array(alphabet=alphabet, dims=2, data=matrix_array)
    aligner.substitution_matrix = substitution_matrix
    
    # Linear gap scoring: both open and extend are -2
    # This means each gap character costs -2 regardless of position
    aligner.open_gap_score = GAP_OPEN_SCORE
    aligner.extend_gap_score = GAP_EXTEND_SCORE
    
    # End gaps are penalized (default behavior)
    # aligner.target_end_gap_score and aligner.query_end_gap_score default to same as open/extend
    
    return aligner


def _extract_variants(ref_aligned: str, query_aligned: str) -> List[Dict]:
    """
    Extract variants by walking aligned sequences.
    
    Args:
        ref_aligned: Reference sequence with gaps
        query_aligned: Query sequence with gaps
        
    Returns:
        List of variant dicts with keys: position, ref, alt, type
        
    Coordinate rules (1-based):
        - SNV: position is the reference position (1-based)
        - Insertion: position is the preceding reference base (0 = before first base)
        - Deletion: position is the first deleted base (1-based)
    """
    variants = []
    ref_pos = 0  # Current position in reference (0-based, will be 1-based in output)
    i = 0
    
    while i < len(ref_aligned):
        ref_base = ref_aligned[i]
        query_base = query_aligned[i]
        
        if ref_base != '-' and query_base != '-':
            # Both bases present
            ref_pos += 1
            
            # SNV: both must be ACGT and different (N is never an SNV)
            if (ref_base != query_base and 
                ref_base in 'ACGT' and 
                query_base in 'ACGT'):
                variants.append({
                    "position": ref_pos,
                    "ref": ref_base,
                    "alt": query_base,
                    "type": "SNV"
                })
            i += 1
            
        elif ref_base == '-':
            # Insertion: run of gaps in reference
            # Position is the preceding reference base (ref_pos before increment)
            insertion_bases = []
            while i < len(ref_aligned) and ref_aligned[i] == '-':
                insertion_bases.append(query_aligned[i])
                i += 1
            
            variants.append({
                "position": ref_pos,  # Preceding base (0 = before first base)
                "ref": "-",
                "alt": ''.join(insertion_bases),
                "type": "insertion"
            })
            
        else:  # query_base == '-'
            # Deletion: run of gaps in query
            # Position is the first deleted base
            deletion_start = ref_pos + 1
            deletion_bases = []
            while i < len(ref_aligned) and query_aligned[i] == '-':
                deletion_bases.append(ref_aligned[i])
                ref_pos += 1
                i += 1
            
            variants.append({
                "position": deletion_start,
                "ref": ''.join(deletion_bases),
                "alt": "-",
                "type": "deletion"
            })
    
    return variants


def _calculate_identity(ref_aligned: str, query_aligned: str) -> float:
    """
    Calculate sequence identity.
    
    Identity = (number of matching ACGT bases) / (total alignment columns)
    
    - Gap columns count in denominator, never match
    - N columns count in denominator, never match
    - Only exact ACGT matches count as matches
    """
    if len(ref_aligned) != len(query_aligned):
        raise ValueError("Aligned sequences must have same length")
    
    if len(ref_aligned) == 0:
        return 0.0
    
    matches = 0
    total = len(ref_aligned)
    
    for ref_base, query_base in zip(ref_aligned, query_aligned):
        # Only count exact matches of ACGT bases
        if (ref_base == query_base and 
            ref_base in 'ACGT'):
            matches += 1
    
    return matches / total


def align_sequences(reference_seq: str, query_seq: str) -> Tuple[Dict, List[Dict]]:
    """
    Align query sequence to reference and extract variants.
    
    Args:
        reference_seq: Reference sequence (uppercase ACGTN)
        query_seq: Query sequence (uppercase ACGTN)
        
    Returns:
        Tuple of (alignment_dict, variants_list)
        
        alignment_dict contains:
            - score: alignment score
            - identity: fraction of matching bases
            - reference_aligned: reference with gaps
            - query_aligned: query with gaps
            
        variants_list: list of variant dicts (see _extract_variants)
    """
    aligner = _create_aligner()
    
    # Perform alignment
    # Note: Do NOT call len(alignments) - it can be huge when there are ties
    # Just take the first alignment (deterministic tie-breaking)
    alignments = aligner.align(reference_seq, query_seq)
    alignment = next(iter(alignments))  # Get first alignment
    
    # Extract score
    score = alignment.score
    
    # Get aligned sequences using alignment's attributes
    # alignment.target is the reference, alignment.query is the query
    ref_aligned = str(alignment).split('\n')[0].split()[2]  # Extract just the sequence part
    query_aligned = str(alignment).split('\n')[2].split()[2]
    
    # Better approach: use format to get clean aligned strings
    formatted = format(alignment, 'fasta')
    lines = formatted.strip().split('\n')
    # FASTA format: >target\nseq\n>query\nseq
    ref_aligned = lines[1]
    query_aligned = lines[3]
    
    # Calculate identity
    identity = _calculate_identity(ref_aligned, query_aligned)
    
    # Extract variants
    variants = _extract_variants(ref_aligned, query_aligned)
    
    alignment_info = {
        "score": float(score),
        "identity": identity,
        "reference_aligned": ref_aligned,
        "query_aligned": query_aligned
    }
    
    return alignment_info, variants
