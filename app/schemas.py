from typing import List, Optional
from pydantic import BaseModel, Field


# model untuk satu varian (SNV, insertion, atau deletion)
class VariantModel(BaseModel):
    position: int = Field(description="posisi di referensi, 1-based")
    ref: str = Field(description="basa referensi, '-' kalau insertion")
    alt: str = Field(description="basa alternatif, '-' kalau deletion")
    type: str = Field(description="tipe varian: SNV, insertion, atau deletion")


# info hasil alignment
class AlignmentInfoModel(BaseModel):
    score: float = Field(description="skor alignment")
    identity: float = Field(description="proporsi basa yang cocok (0-1)")
    reference_aligned: str = Field(description="referensi dengan gap")
    query_aligned: str = Field(description="query dengan gap")


# response untuk endpoint /api/align
class AlignResponse(BaseModel):
    sequence_id: str
    reference_id: str
    alignment: AlignmentInfoModel
    variants: List[VariantModel]


# hasil translasi DNA ke protein
class TranslationModel(BaseModel):
    protein: str = Field(description="urutan asam amino")
    length: int = Field(description="panjang protein")
    has_stop_codon: bool = Field(description="True kalau ketemu stop codon")


# response untuk endpoint /api/translate
class TranslateResponse(BaseModel):
    sequence_id: str
    frame: int = Field(description="reading frame yang dipakai (1, 2, atau 3)")
    protein: str
    length: int
    has_stop_codon: bool


# varian yang sudah dikasih anotasi efek
class VariantEffectModel(VariantModel):
    effect: Optional[str] = Field(None, description="efek varian: synonymous, missense, dll")
    codon: Optional[int] = Field(None, description="nomor kodon, 1-based")
    ref_codon: Optional[str] = Field(None, description="kodon referensi")
    alt_codon: Optional[str] = Field(None, description="kodon alternatif")
    ref_aa: Optional[str] = Field(None, description="asam amino referensi")
    alt_aa: Optional[str] = Field(None, description="asam amino alternatif")
    aa_change: Optional[str] = Field(None, description="notasi perubahan asam amino, contoh: K59N")
    notes: Optional[str] = Field(None, description="catatan tambahan")


# response untuk /api/analyze, extends AlignResponse
class AnalyzeResponse(AlignResponse):
    query_translation: TranslationModel
    reference_translation: TranslationModel
    variants: List[VariantEffectModel]  # type: ignore


# format response kalau ada error
class ErrorResponse(BaseModel):
    error: str = Field(description="kode error")
    detail: str = Field(description="pesan error yang bisa dibaca manusia")
