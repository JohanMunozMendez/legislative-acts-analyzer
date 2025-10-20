import os
from typing import Any, Dict

import structlog
from docling.document_converter import DocumentConverter
from fastapi import UploadFile

from app.core.config import BASE_DIR, settings
from app.core.exceptions import DocumentExtractionError, InvalidDocumentFormatError

logger = structlog.get_logger(__name__)


class ExtractionService:
 
    def __init__(self):
        self.supported_formats = settings.allowed_file_extensions
        self.converter = DocumentConverter()
        logger.info("extraction_service_initialized")
    
    async def extract_document(self, file: UploadFile, filename: str) -> Dict[str, Any]:
        
        # Validate format
        file_ext = self._get_file_extension(filename)
        if file_ext not in self.supported_formats:
            logger.warning(
                "unsupported_format_attempted",
                filename=filename,
                format=file_ext,
                supported_formats=list(self.supported_formats)
            )
            raise InvalidDocumentFormatError(
                f"Unsupported format: {file_ext}. Only {self.supported_formats} are supported"
            )
        
        logger.info(
            "extraction_started",
            filename=filename,
            format=file_ext,
        )
        
        static_file_path = static_file_path = BASE_DIR / "data" / "acts" / "2025-2026-PLENARIO-SESION-44 .docx"
        # static_file_path = static_file_path = BASE_DIR / "data" / "acts" / "2025-2026-PLENARIO-SESION-63 .docx"
        try:
            # Extract with Docling
            result = self.converter.convert(static_file_path)
            
            # Export to markdown
            markdown_text = result.document.export_to_markdown()
            
            # Count pages
            num_pages = self._count_pages(result.document)
            
            logger.info(
                "extraction_successful",
                filename=filename,
                pages=num_pages,
                markdown_length=len(markdown_text)
            )
            
            return {
                "document": result.document,
                "markdown": markdown_text,
                "metadata": {
                    "filename": filename,
                    "format": file_ext,
                    "pages": num_pages,
                }
            }
        
        except Exception as e:
            logger.error(
                "extraction_failed",
                filename=filename,
                error=str(e),
                error_type=type(e).__name__
            )
            raise DocumentExtractionError(f"Failed to extract document: {str(e)}")
    
    def _get_file_extension(self, filename: str) -> str:
        _, ext = os.path.splitext(filename)
        return ext.lower()
    
    def _count_pages(self, document) -> int:
        try:
            # Docling organizes content by pages
            return len(document.pages) if hasattr(document, 'pages') else 1
        except Exception:
            return 1