from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ChunkAnalysis(BaseModel):
    summary: str = Field(
        description="2-3 sentence summary of this chunk"
    )
    is_financial: bool = Field(
        description="Does this chunk discuss financial topics or institutions?"
    )


class FinancialClassification(BaseModel):
    is_financial: bool = Field(
        description="Whether content discusses financial system or institutions"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 to 1.0"
    )
    entities: List[str] = Field(
        default_factory=list,
        description="List of financial institutions or entities mentioned (e.g., BAC, SUGEF, Banco Nacional)"
    )
    reasoning: str = Field(
        description="Brief explanation of why content is/isn't financial"
    )
    
    @field_validator('entities')
    @classmethod
    def clean_entities(cls, v: List[str]) -> List[str]:
        """Remove duplicates and empty strings."""
        return list(set(entity.strip() for entity in v if entity.strip()))


class DocumentAnalysisResult(BaseModel):
    filename: str = Field(
        description="Name of analyzed document"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of analysis"
    )
    general_summary: str = Field(
        description="General summary of entire document (200-400 words)"
    )
    is_financial: bool = Field(
        description="Whether document contains financial content"
    )
    financial_summary: Optional[str] = Field(
        default=None,
        description="Financial-specific summary (only if is_financial=True)"
    )
    entities: Optional[List[str]] = Field(
        default_factory=list,
        description="Aggregated list of all financial entities mentioned across chunks"
    )
    
    # Metadata fields (useful for DB)
    total_chunks: int = Field(
        default=0,
        description="Total number of chunks analyzed"
    )
    financial_chunks: Optional[int] = Field(
        default=0,
        description="Number of chunks classified as financial"
    )
    
    @field_validator('entities')
    @classmethod
    def clean_entities(cls, v: List[str]) -> List[str]:
        """Remove duplicates and empty strings."""
        return sorted(list(set(entity.strip() for entity in v if entity.strip())))


class ChunkAnalysisWithMetadata(BaseModel):
    chunk_index: int
    summary: str
    is_financial: bool
    classification: Optional[FinancialClassification] = None
    text: str
