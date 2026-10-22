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
    content = await file.read()

    sequence_id, sequence = parse_and_validate(content)
    reference_id, ref_seq = get_reference()

    # alignment dulu untuk dapat varian
    aln_info, variants = align_sequences(ref_seq, sequence)

    # terjemahkan kedua sequence di frame 1
    qry_translation = translate_sequence(sequence, frame=1)
    ref_translation = translate_sequence(ref_seq, frame=1)

    # anotasi efek tiap varian terhadap protein
    annotated = annotate_variant_effects(ref_seq, sequence, variants)

    aln_model = AlignmentInfoModel(**aln_info)
    qry_trans_model = TranslationModel(**qry_translation)
    ref_trans_model = TranslationModel(**ref_translation)
    variant_models = [VariantEffectModel(**v) for v in annotated]

    return AnalyzeResponse(
        sequence_id=sequence_id,
        reference_id=reference_id,
        alignment=aln_model,
        variants=variant_models,
        query_translation=qry_trans_model,
        reference_translation=ref_trans_model
    )
