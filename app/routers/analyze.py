"""Router for combined analysis endpoint with variant effects."""
from fastapi import APIRouter, File, UploadFile

from app.services.fasta import parse_and_validate
from app.services.reference import get_reference
from app.services.alignment import align_sequences
from app.services.translation import translate_sequence
from app.services.effects import annotate_variant_effects
from app.schemas import (
    AnalyzeResponse,
    AlignmentInfoModel,
    VariantEffectModel,
    TranslationModel
)


router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(file: UploadFile = File(...)):
    """
    Comprehensive sequence analysis: alignment, translation, and variant effects.
    
    Combines alignment and translation with variant effect annotation.
    All effects are judged against reference frame 1.
    
    Returns:
    - Alignment information (score, identity, variants)
    - Query translation (frame 1)
    - Reference translation (frame 1)
    - Variant effects (synonymous, missense, nonsense, frameshift, etc.)
    
    **Variant Effects**:
    - **SNV**: synonymous, missense, nonsense, stop_lost
    - **Insertion/Deletion**: inframe_insertion, inframe_deletion, frameshift
    - **Undetermined**: N in codon, downstream of frameshift
    """
    # Read uploaded file
    content = await file.read()
    
    # Parse and validate FASTA
    sequence_id, sequence = parse_and_validate(content)
    
    # Get reference
    reference_id, reference_seq = get_reference()
    
    # Perform alignment
    alignment_info, variants = align_sequences(reference_seq, sequence)
    
    # Translate both sequences in frame 1
    query_translation = translate_sequence(sequence, frame=1)
    reference_translation = translate_sequence(reference_seq, frame=1)
    
    # Annotate variant effects
    annotated_variants = annotate_variant_effects(
        reference_seq,
        sequence,
        variants
    )
    
    # Convert to response models
    alignment_model = AlignmentInfoModel(**alignment_info)
    query_trans_model = TranslationModel(**query_translation)
    ref_trans_model = TranslationModel(**reference_translation)
    variant_models = [VariantEffectModel(**v) for v in annotated_variants]
    
    return AnalyzeResponse(
        sequence_id=sequence_id,
        reference_id=reference_id,
        alignment=alignment_model,
        variants=variant_models,
        query_translation=query_trans_model,
        reference_translation=ref_trans_model
    )
