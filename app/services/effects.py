"""Variant effect annotation service."""
from typing import List, Dict
from Bio.Data import CodonTable

from app.services.translation import translate_sequence


# Standard genetic code
_codon_table = CodonTable.unambiguous_dna_by_id[1]


def annotate_variant_effects(
    reference_seq: str,
    query_seq: str,
    variants: List[Dict]
) -> List[Dict]:
    """
    Annotate variants with their effects on protein sequence.
    
    All effects are judged against reference frame 1.
    
    Args:
        reference_seq: Reference DNA sequence
        query_seq: Query DNA sequence
        variants: List of variants from alignment
        
    Returns:
        List of variants with added effect annotations
    """
    # Translate reference in frame 1
    ref_translation = translate_sequence(reference_seq, frame=1)
    ref_protein = ref_translation["protein"]
    
    # Translate query in frame 1
    query_translation = translate_sequence(query_seq, frame=1)
    query_protein = query_translation["protein"]
    
    # Track frameshift offset
    frameshift_offset = 0
    
    annotated_variants = []
    
    for variant in variants:
        annotated = variant.copy()
        position = variant["position"]
        var_type = variant["type"]
        
        # Check if downstream of frameshift
        if frameshift_offset != 0:
            annotated["effect"] = "undetermined"
            annotated["notes"] = f"downstream of frameshift (offset {frameshift_offset})"
            annotated_variants.append(annotated)
            continue
        
        if var_type == "SNV":
            # Determine which codon this SNV affects (0-based codon index)
            # Position is 1-based, so position-1 is 0-based nucleotide index
            nt_index = position - 1
            codon_num = nt_index // 3  # 0-based codon index
            codon_pos_in_codon = nt_index % 3  # Position within codon (0, 1, or 2)
            
            # Get the reference codon
            codon_start = codon_num * 3
            ref_codon = reference_seq[codon_start:codon_start + 3]
            
            # Build the alternate codon
            ref_base = variant["ref"]
            alt_base = variant["alt"]
            
            alt_codon = (
                ref_codon[:codon_pos_in_codon] +
                alt_base +
                ref_codon[codon_pos_in_codon + 1:]
            )
            
            # Check for N in either codon
            if 'N' in ref_codon or 'N' in alt_codon:
                annotated["effect"] = "undetermined"
                annotated["notes"] = "codon contains N"
                annotated["codon"] = codon_num + 1  # 1-based
                annotated_variants.append(annotated)
                continue
            
            # Translate codons
            try:
                ref_aa = _codon_table.forward_table.get(ref_codon, None)
                alt_aa = _codon_table.forward_table.get(alt_codon, None)
                
                # Check for stop codons
                ref_is_stop = ref_codon in ('TAA', 'TAG', 'TGA')
                alt_is_stop = alt_codon in ('TAA', 'TAG', 'TGA')
                
                if ref_is_stop:
                    ref_aa = '*'
                if alt_is_stop:
                    alt_aa = '*'
                
                # Annotate effect
                if ref_aa == alt_aa:
                    effect = "synonymous"
                elif alt_is_stop and not ref_is_stop:
                    effect = "nonsense"
                elif ref_is_stop and not alt_is_stop:
                    effect = "stop_lost"
                else:
                    effect = "missense"
                
                annotated["effect"] = effect
                annotated["codon"] = codon_num + 1  # 1-based
                annotated["ref_codon"] = ref_codon
                annotated["alt_codon"] = alt_codon
                annotated["ref_aa"] = ref_aa if ref_aa else '*'
                annotated["alt_aa"] = alt_aa if alt_aa else '*'
                
                # Create amino acid change notation (e.g., K59N)
                if effect in ("missense", "nonsense", "stop_lost"):
                    aa_change = f"{ref_aa}{codon_num + 1}{alt_aa}"
                    annotated["aa_change"] = aa_change
                
            except (KeyError, IndexError):
                annotated["effect"] = "undetermined"
                annotated["notes"] = "error translating codon"
            
        elif var_type in ("insertion", "deletion"):
            # Classify based on length
            if var_type == "insertion":
                length = len(variant["alt"])
            else:  # deletion
                length = len(variant["ref"])
            
            # Check if frameshift
            if length % 3 == 0:
                # In-frame
                if var_type == "insertion":
                    annotated["effect"] = "inframe_insertion"
                else:
                    annotated["effect"] = "inframe_deletion"
            else:
                # Frameshift
                annotated["effect"] = "frameshift"
                # Update frameshift offset for subsequent variants
                if var_type == "insertion":
                    frameshift_offset = (frameshift_offset + length) % 3
                else:
                    frameshift_offset = (frameshift_offset - length) % 3
        
        annotated_variants.append(annotated)
    
    return annotated_variants
