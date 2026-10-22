from fastapi import APIRouter, File, UploadFile, Form
from typing import Optional

from app.services.fasta import parse_and_validate
from app.services.translation import translate_sequence
from app.schemas import TranslateResponse
from app.errors import ValidationError

router = APIRouter()


@router.post("/translate", response_model=TranslateResponse)
async def translate_endpoint(
    file: UploadFile = File(...),
    frame: Optional[str] = Form("1")
):
    content = await file.read()

    sequence_id, sequence = parse_and_validate(content)

    # validasi parameter frame, harus integer 1-3
    try:
        frame_int = int(frame)
    except (ValueError, TypeError):
        raise ValidationError("invalid_frame", f"Frame must be an integer 1-3, got: {frame}")

    if frame_int not in (1, 2, 3):
        raise ValidationError("invalid_frame", f"Frame must be 1, 2, or 3, got: {frame_int}")

    result = translate_sequence(sequence, frame=frame_int)

    return TranslateResponse(
        sequence_id=sequence_id,
        frame=frame_int,
        protein=result["protein"],
        length=result["length"],
        has_stop_codon=result["has_stop_codon"]
    )
