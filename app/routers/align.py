"""Router for sequence alignment endpoint."""
from fastapi import APIRouter, File, UploadFile

from app.services.fasta import parse_and_validate
from app.services.reference import get_reference
from app.services.alignment import align_sequences
from app.schemas import AlignResponse, AlignmentInfoModel, VariantModel


router = APIRouter()


@router.post("/align", response_model=AlignResponse)
async def align_endpoint(file: UploadFile = File(...)):
    """
    Align a DNA sequence to the reference and report variants.
    
    Accepts a FASTA file with one sequence and returns:
    - Alignment score and identity
    - List of variants (SNVs and indels)
    - Aligned sequences with gaps
    
    **Coordinate system (1-based):**
    - SNV: position is the reference position
    - Insertion: position is the preceding reference base (0 = before first base)
    - Deletion: position is the first deleted base
    """
    # Read uploaded file
    content = await file.read()
    
    # Parse and validate FASTA
    sequence_id, sequence = parse_and_validate(content)
    
    # Get reference
    reference_id, reference_seq = get_reference()
    
    # Perform alignment
    alignment_info, variants = align_sequences(reference_seq, sequence)
    
    # Convert to response models
    alignment_model = AlignmentInfoModel(**alignment_info)
    variant_models = [VariantModel(**v) for v in variants]
    
    return AlignResponse(
        sequence_id=sequence_id,
        reference_id=reference_id,
        alignment=alignment_model,
        variants=variant_models
    )
