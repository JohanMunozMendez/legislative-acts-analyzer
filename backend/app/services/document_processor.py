"""
Document Processor - Pipeline Orchestrator

Pipeline:
1. Extract document content (ExtractionService)
2. Chunk document (ChunkingService)
3. PHASE 1: Analyze each chunk with GPT-4o-mini (OpenAIService)
4. Aggregate results (determine if document is financial)
5. PHASE 2: Generate summaries with GPT-4o (OpenAIService)
6. Build and return DocumentAnalysisResult
"""

from datetime import datetime
from typing import List

import structlog
from fastapi import UploadFile

from app.core.exceptions import DocumentProcessingError
from app.models.schemas import ChunkAnalysisWithMetadata, DocumentAnalysisResult
from app.services.chunking_service import ChunkingService
from app.services.extraction_service import ExtractionService
from app.services.openai_service import OpenAIService

logger = structlog.get_logger(__name__)


class DocumentProcessor:
    def __init__(
        self,
        extraction_service: ExtractionService,
        chunking_service: ChunkingService,
        openai_service: OpenAIService
    ):
        self.extraction_service = extraction_service
        self.chunking_service = chunking_service
        self.openai_service = openai_service
        
        logger.info("document_processor_initialized")
    
    async def process_document(self, file: UploadFile) -> DocumentAnalysisResult:
        """
        Execute complete document analysis pipeline.
        
        Pipeline steps:
        1. Extract document content
        2. Chunk document into smaller pieces
        3. Analyze each chunk (Phase 1: GPT-4o-mini)
        4. Aggregate chunk analyses
        5. Generate document summaries (Phase 2: GPT-4o)
        6. Build final result
        
        Args:
            file: Uploaded document file
        
        Returns:
            DocumentAnalysisResult with analysis details
        
        Raises:
            DocumentProcessingError: If any step in the pipeline fails
        """
        logger.info(
            "document_processing_started",
            filename=file.filename
        )
        
        try:
            # 1. Extract document content
            logger.debug("pipeline_step_extraction")
            extraction_result = await self.extraction_service.extract_document(
                file=file, 
                filename=file.filename
            )
            
            # 2. Chunk document
            logger.debug("pipeline_step_chunking")
            chunks = self.chunking_service.chunk_document(
                docling_doc=extraction_result["document"],
                filename=file.filename
            )
            
            logger.info(
                "document_chunked",
                total_chunks=len(chunks),
                total_tokens=sum(chunk["token_count"] for chunk in chunks)
            )
            
            # 3. Analyze each chunk
            logger.debug("pipeline_step_chunk_analysis")
            chunk_analyses = await self.openai_service.analyze_all_chunks(chunks)
            
            # 4. Aggregate results
            logger.debug("pipeline_step_aggregation")
            aggregation = self._aggregate_chunk_analyses(chunk_analyses)
            
            logger.info(
                "aggregation_completed",
                is_financial=aggregation["is_financial"],
                financial_chunks_count=aggregation["financial_chunks_count"],
                unique_entities_count=len(aggregation["entities"])
            )
            
            # 5. Generate document summaries
            logger.debug("pipeline_step_summary_generation")
            
            # 5.1: General Summary (always generated)
            general_summary = await self.openai_service.generate_general_summary(
                chunk_summaries=aggregation["all_summaries"]
            )
            
            # 5.2: Financial Summary (only if document is financial)
            financial_summary = None
            if aggregation["is_financial"]:
                logger.debug("generating_financial_summary")
                financial_summary = await self.openai_service.generate_financial_summary(
                    financial_chunk_summaries=aggregation["financial_summaries"],
                    entities=aggregation["entities"]
                )
            
            # 6. Build final result
            result = DocumentAnalysisResult(
                filename=file.filename,
                created_at=datetime.now(),
                general_summary=general_summary,
                is_financial=aggregation["is_financial"],
                financial_summary=financial_summary,
                entities=aggregation["entities"],
                total_chunks=len(chunks),
                financial_chunks=aggregation["financial_chunks_count"]
            )
            
            logger.info(
                "document_processing_completed",
                filename=file.filename,
                is_financial=result.is_financial,
                general_summary_length=len(result.general_summary),
                financial_summary_length=len(result.financial_summary) if result.financial_summary else 0,
                entities_count=len(result.entities)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "document_processing_failed",
                filename=file.filename,
                error=str(e),
                error_type=type(e).__name__
            )
            raise DocumentProcessingError(
                f"Failed to process document '{file.filename}': {str(e)}"
            )
    
    def _aggregate_chunk_analyses(
        self, 
        chunk_analyses: List[ChunkAnalysisWithMetadata]
    ) -> dict:
        """
        Aggregate results from chunk analyses.
        
        Determines:
        - Whether document is financial (any chunk is financial)
        - All chunk summaries (for general summary)
        - Financial chunk summaries (for financial summary)
        - Unique entities across all financial chunks
        
        Args:
            chunk_analyses: List of analyzed chunks
        
        Returns:
            Dictionary with aggregated results:
            {
                "is_financial": bool,
                "financial_chunks_count": int,
                "all_summaries": List[str],
                "financial_summaries": List[str],
                "entities": List[str]  # Unique, sorted
            }
        """
        # Extract all summaries
        all_summaries = [chunk.summary for chunk in chunk_analyses]
        
        # Filter financial chunks
        financial_chunks = [
            chunk for chunk in chunk_analyses 
            if chunk.is_financial
        ]
        
        # Extract financial summaries
        financial_summaries = [chunk.summary for chunk in financial_chunks]
        
        # Aggregate entities from all financial chunks
        all_entities = []
        for chunk in financial_chunks:
            if chunk.classification and chunk.classification.entities:
                all_entities.extend(chunk.classification.entities)
        
        # Remove duplicates and sort
        unique_entities = sorted(list(set(all_entities)))
        
        # Determine if document is financial
        is_financial = len(financial_chunks) > 0
        
        return {
            "is_financial": is_financial,
            "financial_chunks_count": len(financial_chunks),
            "all_summaries": all_summaries,
            "financial_summaries": financial_summaries,
            "entities": unique_entities
        }