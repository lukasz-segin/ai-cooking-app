from django.db import transaction
from django.db.models import Q
import logging
from typing import List, Dict, Any
import numpy as np

from ..models import DocumentChunk, StoredDocument

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self, openai_service):
        self.openai_service = openai_service
        self.embedding_dimension = 3072  # Match the FastAPI dimension

    def store_chunk(self, document: StoredDocument, chunk_text: str, chunk_index: int) -> DocumentChunk:
        """Store a document chunk with its embedding."""
        try:
            embedding = self.openai_service.create_embedding(chunk_text)
            
            # Validate embedding dimension
            if len(embedding) != self.embedding_dimension:
                raise ValueError(f"Expected {self.embedding_dimension} dimensions, got {len(embedding)}")

            with transaction.atomic():
                chunk = DocumentChunk.objects.create(
                    document=document,
                    chunk_index=chunk_index,
                    content=chunk_text,
                    embedding=embedding
                )
            return chunk

        except Exception as e:
            logger.error(f"Error storing chunk: {e}")
            raise

    def search_similar(self, text: str, limit: int = 5) -> List[DocumentChunk]:
        """Search for similar chunks using cosine similarity."""
        try:
            query_embedding = self.openai_service.create_embedding(text)
            
            # Convert to numpy array for pgvector
            query_vector = np.array(query_embedding)
            
            # Search using cosine similarity
            similar_chunks = DocumentChunk.objects.order_by(
                Q(embedding__cosine_distance=query_vector)
            )[:limit]
            
            return similar_chunks

        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}")
            raise 