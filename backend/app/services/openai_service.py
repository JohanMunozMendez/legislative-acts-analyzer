from typing import Any, Dict, List

import structlog
from openai import AsyncOpenAI, AuthenticationError, OpenAIError, RateLimitError

from app.core.config import settings
from app.core.exceptions import (
    MissingCredentialsError,
    OpenAIAuthenticationError,
    OpenAIRateLimitError,
    OpenAIServiceError,
)
from app.models.schemas import ChunkAnalysis, ChunkAnalysisWithMetadata, FinancialClassification

logger = structlog.get_logger(__name__)


class OpenAIService:
    def __init__(self):
        self.analysis_model = settings.openai_analysis_model
        self.summary_model = settings.openai_summary_model
        
        if not settings.openai_api_key:
            logger.error("openai_api_key_missing")
            raise MissingCredentialsError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        logger.info("openai_service_initialized")

    
    async def analyze_chunk(self, chunk: Dict[str, Any], chunk_index: int) -> ChunkAnalysisWithMetadata:
        """
        Analyze single chunk with GPT-4o-mini using structured outputs.
        
        Args:
            chunk: Dictionary with 'text' and 'token_count'
            chunk_index: Index of chunk in document
        
        Returns:
            ChunkAnalysisWithMetadata with summary and classification
        
        Raises:
            OpenAIServiceError: If analysis fails
        """
        logger.debug(
            "chunk_analysis_started",
            chunk_index=chunk_index,
            token_count=chunk.get("token_count", 0)
        )
        
        try:
            response = await self.client.responses.parse(
                model=self.analysis_model,
                input=[
                    {
                        "role": "system",
                        "content": self._get_chunk_analysis_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": chunk["text"]
                    }
                ],
                text_format=ChunkAnalysis,
                temperature=settings.openai_analysis_temperature
            )
            
            # Extract parsed Pydantic model
            chunk_analysis = response.output_parsed
            
            # If financial, get detailed classification
            classification = None
            if chunk_analysis.is_financial:
                classification = await self._classify_chunk_detailed(chunk["text"])
            
            result = ChunkAnalysisWithMetadata(
                chunk_index=chunk_index,
                summary=chunk_analysis.summary,
                is_financial=chunk_analysis.is_financial,
                classification=classification,
                text=chunk["text"]
            )
            
            logger.debug(
                "chunk_analysis_completed",
                chunk_index=chunk_index,
                is_financial=result.is_financial,
                summary_length=len(result.summary),
                entities_count=len(classification.entities) if classification else 0
            )
            
            return result
            
        except (RateLimitError, AuthenticationError) as e:
            logger.error(
                "openai_api_error",
                chunk_index=chunk_index,
                error_type=type(e).__name__,
                error=str(e)
            )
            raise self._map_openai_exception(e)
        except Exception as e:
            logger.error(
                "chunk_analysis_failed",
                chunk_index=chunk_index,
                error=str(e),
                error_type=type(e).__name__
            )
            raise OpenAIServiceError(f"Failed to analyze chunk {chunk_index}: {str(e)}")
    
    async def _classify_chunk_detailed(self, text: str) -> FinancialClassification:
        """
        Get detailed financial classification with confidence, entities, and reasoning.
        
        Args:
            text: Chunk text to classify
        
        Returns:
            FinancialClassification with detailed info
        """
        try:
            response = await self.client.responses.parse(
                model=self.analysis_model,
                input=[
                    {
                        "role": "system",
                        "content": self._get_financial_classification_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                text_format=FinancialClassification,
                temperature=settings.openai_analysis_temperature
            )
            
            return response.output_parsed
            
        except Exception as e:
            logger.warning(
                "detailed_classification_failed",
                error=str(e)
            )
            # Fallback to basic classification
            return FinancialClassification(
                is_financial=True,
                confidence=0.5,
                entities=[],
                reasoning="Detailed classification failed, marked as financial based on initial analysis"
            )
    
    async def analyze_all_chunks(self, chunks: List[Dict[str, Any]]) -> List[ChunkAnalysisWithMetadata]:
        """
        Analyze all chunks sequentially.
        
        Args:
            chunks: List of chunks to analyze
        
        Returns:
            List of chunk analyses with metadata
        """
        logger.info(
            "batch_chunk_analysis_started",
            total_chunks=len(chunks)
        )
        
        chunk_analyses = []
        for i, chunk in enumerate(chunks):
            analysis = await self.analyze_chunk(chunk, i)
            chunk_analyses.append(analysis)
        
        # Aggregate all entities
        all_entities = []
        for chunk in chunk_analyses:
            if chunk.classification:
                all_entities.extend(chunk.classification.entities)
        
        logger.info(
            "batch_chunk_analysis_completed",
            total_chunks=len(chunk_analyses),
        )
        
        return chunk_analyses
    
    
    async def generate_general_summary(self, chunk_summaries: List[str]) -> str:
        """
        Generate general document summary from chunk summaries.
        
        Args:
            chunk_summaries: List of short summaries from each chunk
        
        Returns:
            Comprehensive general summary (200-500 words)
        
        Raises:
            OpenAIServiceError: If summary generation fails
        """
        logger.info(
            "general_summary_started",
            total_summaries=len(chunk_summaries)
        )
        
        try:
            # Combine chunk summaries with section markers
            combined_summaries = "\n\n".join(
                f"Sección {i+1}:\n{summary}"
                for i, summary in enumerate(chunk_summaries)
            )
            
            response = await self.client.responses.create(
                model=self.summary_model,
                max_output_tokens=settings.summary_max_tokens,
                input=[
                    {
                        "role": "system",
                        "content": self._get_general_summary_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Genera un resumen general coherente y profesional del siguiente documento legislativo "
                            f"basándote en estos resúmenes de secciones:\n\n{combined_summaries}"
                        )
                    }
                ],
                temperature=settings.openai_temperature_summary,
            )
            
            general_summary = response.output_text
            
            logger.info(
                "general_summary_completed",
                summary_length=len(general_summary)
            )
            
            return general_summary
            
        except (RateLimitError, AuthenticationError) as e:
            logger.error(
                "openai_api_error",
                error_type=type(e).__name__,
                error=str(e)
            )
            raise self._map_openai_exception(e)
        except Exception as e:
            logger.error(
                "general_summary_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise OpenAIServiceError(f"Failed to generate general summary: {str(e)}")
    
    async def generate_financial_summary(
        self, 
        financial_chunk_summaries: List[str],
        entities: List[str]
    ) -> str:
        """
        Generate financial-specific summary from financial chunk summaries only.
        
        Args:
            financial_chunk_summaries: List of summaries from chunks where is_financial=true
            entities: List of financial entities to emphasize
        
        Returns:
            Detailed financial summary (200-500 words)
        
        Raises:
            OpenAIServiceError: If summary generation fails
        """
        logger.info(
            "financial_summary_started",
            total_financial_summaries=len(financial_chunk_summaries),
            entities_count=len(entities)
        )
        
        try:
            # Combine financial chunk summaries with section markers
            combined_summaries = "\n\n".join(
                f"Sección financiera {i+1}:\n{summary}"
                for i, summary in enumerate(financial_chunk_summaries)
            )
            
            entities_text = ", ".join(entities) if entities else "instituciones financieras"
            
            response = await self.client.responses.create(
                model=self.summary_model,
                max_output_tokens=settings.financial_summary_max_tokens,
                input=[
                    {
                        "role": "system",
                        "content": self._get_financial_summary_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Genera un resumen detallado enfocado exclusivamente en temas financieros, "
                            f"prestando especial atención a: {entities_text}\n\n"
                            f"Secciones financieras:\n\n{combined_summaries}"
                        )
                    }
                ],
                temperature=0.3
            )
            
            financial_summary = response.output_text
            
            logger.info(
                "financial_summary_completed",
                summary_length=len(financial_summary)
            )
            
            return financial_summary
            
        except (RateLimitError, AuthenticationError) as e:
            logger.error(
                "openai_api_error",
                error_type=type(e).__name__,
                error=str(e)
            )
            raise self._map_openai_exception(e)
        except Exception as e:
            logger.error(
                "financial_summary_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise OpenAIServiceError(f"Failed to generate financial summary: {str(e)}")
    
    
    def _get_chunk_analysis_system_prompt(self) -> str:
        """System prompt for chunk-level analysis."""
        return """Eres un analista experto de documentos legislativos de la Asamblea Legislativa de Costa Rica.

Tu tarea es analizar fragmentos individuales de actas legislativas y realizar dos acciones:

1. RESUMEN: Genera un resumen conciso de 2-3 oraciones que capture los puntos clave de este fragmento.

2. CLASIFICACIÓN FINANCIERA: Determina si este fragmento específico discute temas relacionados con:
   - Sistema financiero nacional
   - Instituciones financieras (bancos, cooperativas, mutuales, financieras)
   - Entidades como BAC, BCR, BNCR, Banco Popular, Banco Nacional, etc.
   - Regulación bancaria o financiera
   - SUGEF, CONASSIF, BCCR, u otros entes reguladores financieros

Responde con:
- summary: resumen breve en español formal
- is_financial: true/false según si el fragmento trata temas financieros

Sé preciso: solo marca is_financial=true si el fragmento REALMENTE discute temas financieros."""
    
    def _get_financial_classification_system_prompt(self) -> str:
        """System prompt for detailed financial classification."""
        return """Eres un clasificador experto de contenido financiero para documentos legislativos de Costa Rica.

Tu tarea es proporcionar una clasificación detallada del contenido financiero:

1. is_financial: true (ya se determinó que es financiero)
2. confidence: Nivel de confianza (0.0 a 1.0) de que el contenido es financiero
3. entities: Lista de instituciones financieras o entidades reguladoras mencionadas
   Ejemplos: BAC, BCR, BNCR, Banco Popular, Banco Nacional, SUGEF, CONASSIF, BCCR, cooperativas, mutuales, financieras
4. reasoning: Breve explicación (1-2 oraciones) de por qué este contenido es financiero

Sé específico al identificar entidades. Si se menciona "bancos" en general sin nombres específicos, déjalo en reasoning pero no en entities."""
    
    def _get_general_summary_system_prompt(self) -> str:
        """System prompt for general summary generation."""
        return """Eres un analista legislativo experto de la Asamblea Legislativa de Costa Rica.

Tu tarea es generar un resumen general coherente y profesional de un documento legislativo completo, basándote en resúmenes de sus secciones.

Directrices:
- Resume las discusiones, decisiones y votaciones clave
- Mantén el orden cronológico de los temas
- Incluye nombres importantes y números de expedientes
- Usa lenguaje formal y profesional en español
- Extensión objetivo: 200-500 palabras
- Sé conciso pero comprehensivo
- Conecta las ideas de forma fluida y coherente

NO repitas información redundante de las secciones. Sintetiza y conecta los puntos clave."""
    
    def _get_financial_summary_system_prompt(self) -> str:
        """System prompt for financial summary generation."""
        return """Eres un analista financiero especializado en asuntos legislativos de Costa Rica.

Tu tarea es generar un resumen detallado enfocado EXCLUSIVAMENTE en los temas financieros discutidos en el documento legislativo.

Incluye:
- Qué instituciones financieras específicas se mencionan
- Qué regulaciones o proyectos de ley las afectan
- Decisiones o votaciones clave relacionadas con temas financieros
- Implicaciones para el sistema financiero nacional

Directrices:
- Usa lenguaje formal y profesional en español
- Extensión objetivo: 200-500 palabras
- Sé específico sobre entidades y regulaciones mencionadas
- Conecta los temas financieros de forma coherente

Enfócate SOLO en contenido financiero. No incluyas temas no relacionados."""
    
    def _map_openai_exception(self, error: OpenAIError):
        """Map OpenAI exceptions to custom exceptions."""
        if isinstance(error, RateLimitError):
            return OpenAIRateLimitError(f"OpenAI rate limit exceeded: {str(error)}")
        elif isinstance(error, AuthenticationError):
            return OpenAIAuthenticationError(f"OpenAI authentication failed: {str(error)}")
        else:
            return OpenAIServiceError(f"OpenAI API error: {str(error)}")