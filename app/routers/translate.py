"""Router for DNA translation endpoint."""
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
    """
    Translate a DNA sequence to protein in a specified reading frame.
    
    Accepts:
    - file: FASTA file with one sequence
    - frame: Reading frame (1, 2, or 3), default is 1
    
    Returns:
    - Protein sequence
    - Length of protein
    - Whether a stop codon was encountered
    
    **Translation rules:**
    - Frame 1/2/3 = start at nucleotide 1/2/3 (1-based)
    - Only complete codons are translated (trailing 1-2 nt ignored)
    - Any codon containing N becomes X
    - Translation stops at first unambiguous stop codon (TAA, TAG, TGA)
    - Stop codon (*) is not included in output
    """
    # Read uploaded file
    content = await file.read()
    
    # Parse and validate FASTA
    sequence_id, sequence = parse_and_validate(content)
    
    # Validate and parse frame parameter
    try:
        frame_int = int(frame)
    except (ValueError, TypeError):
        raise ValidationError("invalid_frame", f"Frame must be an integer 1-3, got: {frame}")
    
    if frame_int not in (1, 2, 3):
        raise ValidationError("invalid_frame", f"Frame must be 1, 2, or 3, got: {frame_int}")
    
    # Translate sequence
    translation_result = translate_sequence(sequence, frame=frame_int)
    
    return TranslateResponse(
        sequence_id=sequence_id,
        frame=frame_int,
        protein=translation_result["protein"],
        length=translation_result["length"],
        has_stop_codon=translation_result["has_stop_codon"]
    )
