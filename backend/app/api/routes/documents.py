import os

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    DocumentProcessingError,
    InvalidDocumentFormatError,
    OpenAIRateLimitError,
    OpenAIServiceError,
)
from app.db.database import get_db
from app.db.repository import DocumentAnalysisRepository
from app.models.schemas import DocumentAnalysisResult
from app.services.chunking_service import ChunkingService
from app.services.document_processor import DocumentProcessor
from app.services.extraction_service import ExtractionService
from app.services.openai_service import OpenAIService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

def get_document_processor() -> DocumentProcessor:
    """
    Dependency that provides DocumentProcessor with all required services.
    
    Returns:
        Configured DocumentProcessor instance
    """
    extraction_service = ExtractionService()
    chunking_service = ChunkingService()
    openai_service = OpenAIService()
    
    return DocumentProcessor(
        extraction_service=extraction_service,
        chunking_service=chunking_service,
        openai_service=openai_service
    )

@router.post(
    "/analyze",
    response_model=DocumentAnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Analyze Legislative Document",
    description="""
    Analyze a legislative document (acta) to generate summaries and detect financial content.
    
    **Process:**
    1. Extract content from .docx or .txt file
    2. Split into chunks for analysis
    3. Analyze each chunk (summary + classification)
    4. Generate general summary
    5. Generate financial summary if applicable
    
    **Supported formats:** .docx, .txt
    
    **Max file size:** 15MB
    """
)
async def analyze_document(
    file: UploadFile = File(...),
    processor: DocumentProcessor = Depends(get_document_processor),
    db: Session = Depends(get_db)
) -> DocumentAnalysisResult:
    """
    Analyze uploaded legislative document.
    
    Args:
        file: Uploaded document file
        processor: DocumentProcessor instance (injected)
    
    Returns:
        DocumentAnalysisResult with summaries and classifications
    
    Raises:
        HTTPException: For various error conditions
    """
    logger.info(
        "analyze_document_request_received",
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=file.size if hasattr(file, 'size') else 'unknown'
    )
    
    # Validate file format
    if not file.filename:
        logger.warning("filename_missing")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    _, file_ext = os.path.splitext(file.filename)
    if file_ext.lower() not in settings.allowed_file_extensions:
        logger.warning(
            "invalid_file_format",
            filename=file.filename,
            extension=file_ext
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format: {file_ext}. Only .docx and .txt are supported."
        )
    
    try:
        # Read file bytes
        file_bytes = await file.read()
        
        # Validate file size
        file_size = len(file_bytes)
        max_size = settings.max_file_size_mb * 1024 * 1024
        if file_size > max_size:
            logger.warning(
                "file_too_large",
                filename=file.filename,
                size_bytes=file_size,
                max_size_bytes=max_size
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {max_size / (1024*1024):.0f}MB"
            )
        
        # Validate file is not empty
        if file_size == 0:
            logger.warning(
                "empty_file",
                filename=file.filename
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # Process document
        result = await processor.process_document(file)
        
        # Save to database
        repository = DocumentAnalysisRepository(db)
        repository.create(result)
        
        logger.info(
            "analyze_document_request_completed",
            filename=file.filename,
            is_financial=result.is_financial,
            entities_count=len(result.entities)
        )
        
        return result
        
    except InvalidDocumentFormatError as e:
        logger.warning(
            "invalid_document_format",
            filename=file.filename,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except OpenAIRateLimitError as e:
        logger.error(
            "openai_rate_limit_exceeded",
            filename=file.filename,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="OpenAI API rate limit exceeded. Please try again later."
        )
    
    except OpenAIServiceError as e:
        logger.error(
            "openai_service_error",
            filename=file.filename,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable. Please try again later."
        )
    
    except DocumentProcessingError as e:
        logger.error(
            "document_processing_error",
            filename=file.filename,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )
    
    except Exception as e:
        logger.error(
            "unexpected_error",
            filename=file.filename,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the document"
        )


@router.get(
    "/analyses",
    status_code=status.HTTP_200_OK,
    summary="List All Analyses",
    description="Retrieve all document analyses with optional filtering"
)
async def list_analyses(
    skip: int = 0,
    limit: int = 100,
    is_financial: bool = False,
    db: Session = Depends(get_db)
):
    """
    List all document analyses with pagination and filtering.
    
    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        is_financial: Filter by financial classification
        db: Database session
    
    Returns:
        List of document analyses
    """
    logger.info(
        "list_analyses_requested",
        skip=skip,
        limit=limit,
        is_financial=is_financial
    )
    
    repository = DocumentAnalysisRepository(db)
    analyses = repository.get_all(skip=skip, limit=limit, is_financial=is_financial)
    
    return {
        "total": len(analyses),
        "skip": skip,
        "limit": limit,
        "results": [analysis.to_dict() for analysis in analyses]
    }


@router.get(
    "/analyses/{analysis_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Analysis by ID",
    description="Retrieve specific document analysis by ID"
)
async def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    """
    Get document analysis by ID.
    
    Args:
        analysis_id: Analysis ID
        db: Database session
    
    Returns:
        Document analysis if found
    
    Raises:
        HTTPException: If analysis not found
    """
    logger.info("get_analysis_requested", analysis_id=analysis_id)
    
    repository = DocumentAnalysisRepository(db)
    analysis = repository.get_by_id(analysis_id)
    
    if not analysis:
        logger.warning("analysis_not_found", analysis_id=analysis_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {analysis_id} not found"
        )
    
    return analysis.to_dict()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Check if the document analysis service is operational"
)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Status message indicating service is operational
    """
    logger.debug("health_check_requested")
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "service": "document-analysis",
            "version": "1.0.0"
        }
    )