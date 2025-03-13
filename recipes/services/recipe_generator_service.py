import logging
import json
from typing import Dict, Any, List

from documents_processor.services.openai_service import OpenAIService
from documents_processor.services.vector_service import VectorService
from recipes.models import Recipe
from recipes.services.recipe_search_service import RecipeSearchService
from recipes.models.chat_models import ChatRequest, Message

logger = logging.getLogger(__name__)

class RecipeGeneratorService:
    """Service for generating new recipes based on similar existing recipes."""
    
    def __init__(self):
        self.openai_service = OpenAIService()
        self.vector_service = VectorService(self.openai_service)
        self.search_service = RecipeSearchService()
    
    def generate_recipe(self, query: str, num_examples: int = 3) -> Dict[str, Any]:
        """
        Generate a new recipe based on similar existing recipes.
        
        Args:
            query: The recipe name or description to generate
            num_examples: Number of similar recipes to use as examples
            
        Returns:
            Dictionary containing the generated recipe
        """
        try:
            # Step 1: Find similar recipes to use as examples
            similar_recipes = self.search_service.search_recipes_by_semantic(query, limit=num_examples)
            
            # Step 2: Format similar recipes as context for the LLM
            recipes_context = self._format_recipes_for_context(similar_recipes)
            
            # Step 3: Create a system prompt and user prompt
            system_prompt = self._create_system_prompt(recipes_context)
            user_prompt = self._create_user_prompt(query)
            
            # Step 4: Call LLM to generate new recipe (synchronously)
            
            chat_request = ChatRequest(
                messages=[
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=user_prompt),
                ],
                model="gpt-4o",  # Using a capable model for recipe generation
                stream=False,
                json_mode=True,  # Request structured JSON output
            )
            
            # Use the synchronous method
            response = self.openai_service.create_completion(chat_request)
            
            # Step 5: Parse and structure the response
            content = response.content if hasattr(response, "content") else str(response)
            
            # Step 6: Save the generated recipe to the database
            new_recipe = self._save_recipe_to_database(query, content)
            
            # Step 7: Return formatted result
            return {
                "status": "success",
                "recipe": {
                    "id": new_recipe.id,
                    "title": new_recipe.title,
                    "description": new_recipe.description,
                    "instructions": new_recipe.instructions
                },
                "similar_recipes_used": [
                    {
                        "document_title": item.get("document_title", "Unknown"),
                        "similarity_score": item.get("vector_similarity", 0)
                    } for item in similar_recipes[:3]  # Limit to top 3 for clarity
                ],
                "recipe_query": query
            }
            
        except Exception as e:
            logger.error(f"Error generating recipe: {e}", exc_info=True)
            raise
    
    def _format_recipes_for_context(self, recipes: list) -> str:
        """Format a list of recipes into a context string for the LLM."""
        context = "Here are some similar recipes to use as reference:\n\n"
        
        for i, recipe in enumerate(recipes, 1):
            context += f"RECIPE {i}:\n"
            context += f"Title: {recipe.get('document_title', 'Unknown')}\n"
            context += f"Content: {recipe.get('content', '')}\n\n"
        
        return context
    
    def _create_system_prompt(self, recipes_context: str) -> str:
        """Create a system prompt with instructions and recipe examples."""
        # MOCK: This will be replaced with a more sophisticated prompt in the future
        return f"""You are a professional chef and recipe creator. Your task is to create a new, unique recipe based on the examples provided.
        
The recipe should be well-structured with:
1. A title
2. A list of ingredients with precise measurements
3. Step-by-step cooking instructions
4. Nutritional information (estimated calories and macronutrients)
5. Preparation time and cooking time

Use the following similar recipes as inspiration, but create something original:

{recipes_context}

Format your response as a JSON object with the following fields:
- title: string
- description: string
- ingredients: array of strings
- instructions: array of strings
- nutritional_info: object with calories, protein, carbs, fat
- prep_time_minutes: number
- cook_time_minutes: number

Be precise and make sure the recipe is practical and can be followed by home cooks.
"""
    
    def _create_user_prompt(self, query: str) -> str:
        """Create a user prompt based on the query."""
        # MOCK: This will be replaced with a more sophisticated prompt in the future
        return f"""Create a new, unique recipe for "{query}" using the example recipes as inspiration. Make sure it's delicious, practical, and includes all required sections."""
    
    def _save_recipe_to_database(self, title: str, recipe_content: str) -> Recipe:
        """Save the generated recipe to the database."""
        # Parse the JSON content if needed
        # For now, we'll just create a simple recipe
        try:
            # Remove markdown code block markers if present
            cleaned_content = recipe_content.replace("```json", "").replace("```", "").strip()
            recipe_data = json.loads(cleaned_content)
            
            # Create formatted content for instructions
            instructions_text = "\n\n".join([
                f"# Ingredients\n" + "\n".join([f"- {ing}" for ing in recipe_data.get("ingredients", [])]),
                f"# Instructions\n" + "\n".join([f"{i+1}. {step}" for i, step in enumerate(recipe_data.get("instructions", []))]),
                f"# Nutritional Information\n" + 
                f"Calories: {recipe_data.get('nutritional_info', {}).get('calories', 'N/A')}\n" +
                f"Protein: {recipe_data.get('nutritional_info', {}).get('protein', 'N/A')}\n" +
                f"Carbs: {recipe_data.get('nutritional_info', {}).get('carbs', 'N/A')}\n" +
                f"Fat: {recipe_data.get('nutritional_info', {}).get('fat', 'N/A')}\n\n" +
                f"Prep Time: {recipe_data.get('prep_time_minutes', 'N/A')} minutes\n" +
                f"Cook Time: {recipe_data.get('cook_time_minutes', 'N/A')} minutes"
            ])
            
            new_recipe = Recipe.objects.create(
                title=recipe_data.get("title", title),
                description=recipe_data.get("description", ""),
                instructions=instructions_text
            )
            
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            new_recipe = Recipe.objects.create(
                title=title,
                description="Generated recipe",
                instructions=recipe_content
            )
            
        return new_recipe 