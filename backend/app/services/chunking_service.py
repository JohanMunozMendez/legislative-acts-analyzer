from typing import Any

import structlog
import tiktoken
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer
from docling_core.types.doc.document import DoclingDocument

from app.core.config import settings
from app.utils.text_processing import count_tokens

logger = structlog.get_logger(__name__)


class ChunkingService:
    def __init__(self):
        self.max_chunk_tokens = settings.max_chunk_tokens
        
        self.tokenizer = OpenAITokenizer(
            tokenizer=tiktoken.encoding_for_model("gpt-4o"),
            max_tokens=self.max_chunk_tokens
        )
        
        self.chunker = HybridChunker(
            tokenizer=self.tokenizer,
            merge_peers=True,
        )
        
        logger.info(
            "chunking_service_initialized",
            max_chunk_tokens=self.max_chunk_tokens,
            tokenizer="OpenAI (official from docling_core)"
        )
    
    def chunk_document(
        self,
        docling_doc: DoclingDocument,
        filename: str = "document"
    ) -> list[dict[str, Any]]:
        logger.info(
            "chunking_started",
            filename=filename
        )
        
        # Apply hybrid chunking
        chunk_iter = self.chunker.chunk(dl_doc=docling_doc)
        raw_chunks = list(chunk_iter)
        
        logger.info(
            "chunking_complete",
            filename=filename,
            chunks_created=len(raw_chunks)
        )
        
        # Convert to standardized format
        chunks = []
        for i, raw_chunk in enumerate(raw_chunks):
            # Get chunk text
            chunk_text = raw_chunk.text
            
            # Count tokens
            token_count = count_tokens(chunk_text)
            
            # Extract metadata
            chunk_dict = {
                "text": chunk_text,
                "token_count": token_count,
                "chunk_index": i,
            }
            
            chunks.append(chunk_dict)
        
        return chunks