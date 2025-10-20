import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import documents
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.database import engine
from app.db.models import Base

# Initialize structured logging
setup_logging()
logger = structlog.get_logger(__name__)

def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI instance
    """
    app = FastAPI(
        title="Legislative Document Analysis API",
        description="""
        API for analyzing Costa Rican Legislative Assembly documents (actas).
        
        **Features:**
        - Extract and analyze legislative documents (.docx, .txt)
        - Generate comprehensive summaries
        - Detect and summarize financial content
        
        **Technology:**
        - Document processing: Docling
        - Text analysis: OpenAI Models
        """,
        version="1.0.0",
        docs_url="/docs",
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(documents.router)
    
    return app

app = create_application()

Base.metadata.create_all(bind=engine)

@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint - API information.
    
    Returns:
        API metadata and available endpoints
    """
    return {
        "message": "Welcome to the Legislative Document Analysis API!",
        "version": "1.0.0",
        "documentation": {
            "swagger_ui": "/docs",
        }
    }