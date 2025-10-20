"""
Application configuration using Pydantic Settings.
Loads configuration from environment variables.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Define base directory (backend/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Legislative Acts Analyzer"
    app_version: str = "1.0.0"
    environment: Literal["development", "production"] = "development"
    debug: bool = Field(default=True, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    openai_api_key: str = Field(
        ...,
        description="OpenAI API key (starts with sk-)"
    )
    openai_summary_model: str = Field(
        default="gpt-4o",
        description="GPT-4o model name for summaries"
    )
    openai_analysis_model: str = Field(
        default="gpt-4o-mini",
        description="GPT-4o-mini model name for classification"
    )
    openai_temperature_summary: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Temperature for summary generation (lower = more deterministic)"
    )
    openai_analysis_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Temperature for classification (very low for consistency)"
    )

    docling_ocr_enabled: bool = Field(
        default=True,
        description="Enable OCR for embedded images in documents"
    )
    docling_table_structure: bool = Field(
        default=True,
        description="Extract table structure (not just text)"
    )

    max_file_size_mb: int = Field(
        default=10,
        description="Maximum file upload size in MB"
    )
    
    allowed_file_extensions: list[str] = Field(
        default=[".docx", ".txt"],
        description="Allowed file extensions for upload"
    )

    max_chunk_tokens: int = Field(
        default=8000,
        description="Maximum tokens per chunk. Optimized to avoid 'lost in the middle' "
                    "while preserving context. 8k tokens ≈ 6000 words ≈ 12 pages."
    )
    chunk_overlap_tokens: int = Field(
        default=500,
        description="Overlap between chunks (~6%) to preserve context at boundaries. "
                    "500 tokens ≈ 375 words."
    )

    summary_max_tokens: int = Field(
        default=800,
        description="Maximum tokens for general summaries (~600 words, 1.2 pages)."
    )
    financial_summary_max_tokens: int = Field(
        default=600,
        description="Maximum tokens for financial-specific summaries."
    )

    database_url: str = Field(
        default=f"sqlite:///{BASE_DIR}/data/legislative_acts.db",
        description="Database connection URL"
    )

    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Allowed CORS origins",
    )

settings = Settings()