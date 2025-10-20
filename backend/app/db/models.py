"""
SQLAlchemy Models for Database

Defines database schema for storing document analysis results.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class DocumentAnalysis(Base):
    __tablename__ = "document_analyses"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Document metadata
    filename = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
    
    # Analysis results
    general_summary = Column(Text, nullable=False)
    is_financial = Column(Boolean, nullable=False, default=False, index=True)
    financial_summary = Column(Text, nullable=True)
    
    # Financial entities (stored as JSON array)
    entities = Column(JSON, nullable=True, default=list)
    
    # Processing metadata
    total_chunks = Column(Integer, nullable=False, default=0)
    financial_chunks = Column(Integer, nullable=True, default=0)
    
    def __repr__(self) -> str:
        return (
            f"<DocumentAnalysis("
            f"id={self.id}, "
            f"filename='{self.filename}', "
            f"is_financial={self.is_financial}, "
            f"created_at={self.created_at}"
            f")>"
        )
    
    def to_dict(self) -> dict:
        """
        Convert SQLAlchemy model to dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        return {
            "id": self.id,
            "filename": self.filename,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "general_summary": self.general_summary,
            "is_financial": self.is_financial,
            "financial_summary": self.financial_summary,
            "entities": self.entities,
            "total_chunks": self.total_chunks,
            "financial_chunks": self.financial_chunks,
        }