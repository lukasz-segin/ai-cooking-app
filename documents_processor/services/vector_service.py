from django.db import transaction
from django.db.models import Q, Value, FloatField, F, ExpressionWrapper
import logging
from typing import List, Dict, Any
from pgvector.django import CosineDistance
from django.contrib.postgres.search import SearchQuery, SearchRank

from ..models import DocumentChunk, StoredDocument

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self, openai_service):
        self.openai_service = openai_service
        self.embedding_dimension = 1536  # Matches the small model dimensions
    
    def store_chunk(self, document: StoredDocument, chunk_text: str, chunk_index: int) -> DocumentChunk:
        """
        Generates embedding for a chunk and stores it in the database.
        """
        try:
            # Create embedding
            embedding = self.openai_service.create_embedding(chunk_text)
            
            # Check if the embedding has the correct dimensions
            if len(embedding) != self.embedding_dimension:
                raise ValueError(f"Expected embedding of {self.embedding_dimension} dimensions, got {len(embedding)}")
            
            # Create the document chunk without specifying content_tsv
            chunk = DocumentChunk(
                document=document,
                chunk_index=chunk_index,
                content=chunk_text,
                embedding=embedding,
                # Don't include content_tsv here - it's generated automatically
            )
            chunk.save()
            
            return chunk
            
        except Exception as e:
            logger.error(f"Error storing chunk: {e}")
            raise

    def search_similar(self, text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Hybrid search using both text search and vector similarity.
        """
        try:
            # Create embedding for semantic search
            query_embedding = self.openai_service.create_embedding(text)
            
            # Create search query for text search
            search_query = SearchQuery(text, config='simple')
            
            # Try hybrid search first
            chunks_with_scores = DocumentChunk.objects.annotate(
                # Vector similarity (lower is better)
                distance=CosineDistance("embedding", query_embedding),
                # Text match score (higher is better)
                text_rank=SearchRank('content_tsv', search_query),
                # Combined score calculation
                combined_score=ExpressionWrapper(
                    F('distance') - (F('text_rank') * 0.2),
                    output_field=FloatField()
                )
            ).order_by('combined_score')[:limit]
            
            # IMPORTANT: If no results found with hybrid search, fall back to pure vector search
            if not chunks_with_scores.exists():
                chunks_with_scores = DocumentChunk.objects.annotate(
                    distance=CosineDistance("embedding", query_embedding),
                    text_rank=Value(0.0, output_field=FloatField()),
                    combined_score=F('distance')  # Just use distance for combined score
                ).order_by('distance')[:limit]
            
            # Format results with normalized similarity scores
            results = []
            for chunk in chunks_with_scores:
                # Convert cosine distance to similarity score (1 - distance)
                vector_score = round(1 - float(chunk.distance), 4)
                text_score = float(chunk.text_rank)
                
                results.append({
                    'chunk_id': chunk.id,
                    'document_id': chunk.document.id,
                    'document_title': chunk.document.title,
                    'content': chunk.content,
                    'chunk_index': chunk.chunk_index,
                    'vector_similarity': vector_score,
                    'text_match_score': text_score,
                    # Combined score formula gives higher weight to text relevance (adjust weights as necessary):
                    'combined_score': round((vector_score + text_score*5)/6, 4),
                    'search_method': 'hybrid' if text_score > 0.01 else 'semantic'
                })
            
            return results
        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}")
            raise