from fastapi import APIRouter, File, UploadFile

from app.services.fasta import parse_and_validate
from app.services.reference import get_reference
from app.services.alignment import align_sequences
from app.schemas import AlignResponse, AlignmentInfoModel, VariantModel

router = APIRouter()


@router.post("/align", response_model=AlignResponse)
async def align_endpoint(file: UploadFile = File(...)):
    content = await file.read()

    # validasi dulu sebelum diproses
    sequence_id, sequence = parse_and_validate(content)

    # ambil referensi yang sudah di-load waktu startup
    reference_id, ref_seq = get_reference()

    # jalankan alignment dan ekstrak varian
    aln_info, variants = align_sequences(ref_seq, sequence)

    aln_model = AlignmentInfoModel(**aln_info)
    variant_models = [VariantModel(**v) for v in variants]

    return AlignResponse(
        sequence_id=sequence_id,
        reference_id=reference_id,
        alignment=aln_model,
        variants=variant_models
    )
