"""Pydantic response models for API endpoints."""
from typing import List, Optional
from pydantic import BaseModel, Field


class VariantModel(BaseModel):
    """A single variant (SNV, insertion, or deletion)."""
    position: int = Field(description="1-based reference position")
    ref: str = Field(description="Reference allele or '-' for insertion")
    alt: str = Field(description="Alternate allele or '-' for deletion")
    type: str = Field(description="Variant type: SNV, insertion, or deletion")


class AlignmentInfoModel(BaseModel):
    """Alignment statistics."""
    score: float = Field(description="Alignment score")
    identity: float = Field(description="Fraction of matching bases (0-1)")
    reference_aligned: str = Field(description="Reference sequence with gaps")
    query_aligned: str = Field(description="Query sequence with gaps")


class AlignResponse(BaseModel):
    """Response for /api/align endpoint."""
    sequence_id: str
    reference_id: str
    alignment: AlignmentInfoModel
    variants: List[VariantModel]


class TranslationModel(BaseModel):
    """Translation result."""
    protein: str = Field(description="Amino acid sequence")
    length: int = Field(description="Length of protein sequence")
    has_stop_codon: bool = Field(description="True if translation stopped at a stop codon")


class TranslateResponse(BaseModel):
    """Response for /api/translate endpoint."""
    sequence_id: str
    frame: int = Field(description="Reading frame used (1, 2, or 3)")
    protein: str
    length: int
    has_stop_codon: bool


class VariantEffectModel(VariantModel):
    """Variant with effect annotation."""
    effect: Optional[str] = Field(None, description="Variant effect: synonymous, missense, nonsense, etc.")
    codon: Optional[int] = Field(None, description="Codon number (1-based)")
    ref_codon: Optional[str] = Field(None, description="Reference codon")
    alt_codon: Optional[str] = Field(None, description="Alternate codon")
    ref_aa: Optional[str] = Field(None, description="Reference amino acid")
    alt_aa: Optional[str] = Field(None, description="Alternate amino acid")
    aa_change: Optional[str] = Field(None, description="Amino acid change (e.g., K59N)")
    notes: Optional[str] = Field(None, description="Additional notes")


class AnalyzeResponse(AlignResponse):
    """Response for /api/analyze endpoint (extends AlignResponse)."""
    query_translation: TranslationModel
    reference_translation: TranslationModel
    variants: List[VariantEffectModel]  # type: ignore  # Override with annotated variants


class ErrorResponse(BaseModel):
    """Error response."""
    error: str = Field(description="Machine-readable error code")
    detail: str = Field(description="Human-readable error message")
