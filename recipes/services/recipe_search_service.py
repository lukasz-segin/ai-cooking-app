import logging
from typing import List, Dict, Any
from documents_processor.services.openai_service import OpenAIService
from documents_processor.services.vector_service import VectorService
from documents_processor.models import DocumentChunk, StoredDocument

logger = logging.getLogger(__name__)

class RecipeSearchService:
    def __init__(self):
        self.openai_service = OpenAIService()
        self.vector_service = VectorService(self.openai_service)
    
    def search_recipes_by_semantic(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for recipes semantically similar to the query text
        
        Args:
            query: The search query (meal name or description)
            limit: Maximum number of results to return
            
        Returns:
            List of matching document chunks with similarity scores
        """
        try:
            # Use the improved vector service that returns chunks with scores
            results = self.vector_service.search_similar(query, limit=limit)
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic recipe search: {e}")
            raise 