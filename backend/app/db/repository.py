from typing import List, Optional

import structlog
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.models import DocumentAnalysis
from app.models.schemas import DocumentAnalysisResult

logger = structlog.get_logger(__name__)

class DocumentAnalysisRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, analysis: DocumentAnalysisResult) -> DocumentAnalysis:
        """
        Save document analysis result to database.
        
        Args:
            analysis: Pydantic model with analysis results
        
        Returns:
            Created SQLAlchemy model with assigned ID
        
        Raises:
            Exception: If database operation fails
        """
        logger.info(
            "creating_document_analysis",
            filename=analysis.filename,
            is_financial=analysis.is_financial
        )
        
        try:
            # Convert Pydantic model to SQLAlchemy model
            db_analysis = DocumentAnalysis(
                filename=analysis.filename,
                created_at=analysis.created_at,
                general_summary=analysis.general_summary,
                is_financial=analysis.is_financial,
                financial_summary=analysis.financial_summary,
                entities=analysis.entities,
                total_chunks=analysis.total_chunks,
                financial_chunks=analysis.financial_chunks
            )
            
            self.db.add(db_analysis)
            self.db.commit()
            self.db.refresh(db_analysis)
            
            logger.info(
                "document_analysis_created",
                analysis_id=db_analysis.id,
                filename=db_analysis.filename
            )
            
            return db_analysis
            
        except Exception as e:
            self.db.rollback()
            logger.error(
                "create_document_analysis_failed",
                filename=analysis.filename,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def get_all(
    self, 
    skip: int = 0, 
    limit: int = 100,
    is_financial: Optional[bool] = None
) -> List[DocumentAnalysis]:
        """
        Retrieve all document analyses with optional filtering.
        
        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            is_financial: Filter by financial classification (optional)
        
        Returns:
            List of DocumentAnalysis records
        """
        logger.debug(
            "fetching_all_analyses",
            skip=skip,
            limit=limit,
            is_financial=is_financial
        )
        
        query = self.db.query(DocumentAnalysis)
        
        if is_financial is not None:
            query = query.filter(DocumentAnalysis.is_financial == is_financial)
        
        return query.order_by(
            desc(DocumentAnalysis.created_at)
        ).offset(skip).limit(limit).all()        
    
    def get_by_id(self, analysis_id: int) -> Optional[DocumentAnalysis]:
        """
        Retrieve document analysis by ID.
        
        Args:
            analysis_id: Analysis ID
        
        Returns:
            DocumentAnalysis if found, None otherwise
        """
        logger.debug("fetching_analysis_by_id", analysis_id=analysis_id)
        
        return self.db.query(DocumentAnalysis).filter(
            DocumentAnalysis.id == analysis_id
        ).first()