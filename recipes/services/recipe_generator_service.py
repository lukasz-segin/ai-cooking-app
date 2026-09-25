import requests
import uuid
import logging
import json
from typing import Dict, Any, List
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from documents_processor.services.openai_service import OpenAIService
from documents_processor.services.vector_service import VectorService
from recipes.models import Recipe
from recipes.services.recipe_search_service import RecipeSearchService
from recipes.models.chat_models import ChatRequest, Message
from .prompts import get_system_prompt_v3, get_user_prompt_v3, get_image_prompt

logger = logging.getLogger(__name__)


class RecipeGeneratorService:
    """Service for generating new recipes based on similar existing recipes."""

    def __init__(self):
        self.openai_service = OpenAIService()
        self.vector_service = VectorService(self.openai_service)
        self.search_service = RecipeSearchService()

    def generate_recipe(
        self, query: str, num_examples: int = 3, public_base_url: str = ""
    ) -> Dict[str, Any]:
        """
        Generate a new recipe based on similar existing recipes.

        Args:
            query: The recipe name or description to generate
            num_examples: Number of similar recipes to use as examples

        Returns:
            Dictionary containing the generated recipe
        """
        try:
            logger.info(
                f"Starting recipe generation for query: '{query}' with {num_examples} examples"
            )

            # Step 1: Find similar recipes to use as examples
            logger.info(f"Step 1: Searching for similar recipes using semantic search")
            similar_recipes = self.search_service.search_recipes_by_semantic(
                query, limit=num_examples
            )
            logger.info(f"Found {len(similar_recipes)} similar recipes")

            # Log titles and similarity scores of found recipes
            for i, recipe in enumerate(similar_recipes, 1):
                logger.info(
                    f"Similar recipe {i}: '{recipe.get('document_title', 'Unknown')}' (similarity: {recipe.get('vector_similarity', 0):.4f})"
                )

            # Step 2: Format similar recipes as context for the LLM
            logger.info(f"Step 2: Formatting recipes for context")
            recipes_context = self._format_recipes_for_context(similar_recipes)
            logger.debug(f"Recipe context length: {len(recipes_context)} characters")

            # Step 3: Create a system prompt and user prompt
            logger.info(f"Step 3: Creating system and user prompts")
            system_prompt = get_system_prompt_v3(recipes_context)
            user_prompt = get_user_prompt_v3(query)
            logger.debug(f"System prompt length: {len(system_prompt)} characters")
            logger.debug(f"User prompt: {user_prompt}")

            # Step 4: Call LLM to generate new recipe (synchronously)
            logger.info(f"Step 4: Calling LLM to generate recipe with model: gpt-4o")

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
            logger.info(f"Sending request to OpenAI API")
            response = self.openai_service.create_completion(chat_request)

            # Step 5: Parse and structure the response
            logger.info(f"Step 5: Parsing LLM response")
            content = (
                response.content if hasattr(response, "content") else str(response)
            )
            logger.debug(
                f"Raw LLM response: {content[:500]}..."
                if len(content) > 500
                else content
            )

            # Step 6: Save the generated recipe to the database
            logger.info(f"Step 6: Saving generated recipe to database")
            new_recipe = self._save_recipe_to_database(query, content)
            logger.info(
                f"Recipe saved with ID: {new_recipe.id}, title: '{new_recipe.title}'"
            )

            image_url = ""
            if settings.RECIPE_IMAGE_GENERATION_ENABLED:
                logger.info("Step 6.5: Generating image for recipe")
                image_url = self._generate_recipe_image(
                    new_recipe, public_base_url=public_base_url
                )
                logger.info(f"Image generated for recipe: {image_url}")
                new_recipe.image_url = image_url
                new_recipe.save()

            # Step 7: Return formatted result with image
            logger.info(f"Step 7: Generation complete, returning recipe data")
            return {
                "status": "success",
                "recipe": {
                    "id": new_recipe.id,
                    "title": new_recipe.title,
                    "description": new_recipe.description,
                    "blog_content": new_recipe.blog_content,
                    "difficulty": new_recipe.difficulty,
                    "season": new_recipe.season,
                    "keywords": new_recipe.keywords,
                    "ingredients": new_recipe.ingredients,
                    "instructions": new_recipe.instructions,
                    "image_url": image_url,
                    "subtitle": new_recipe.subtitle,
                    "course": new_recipe.course,
                    "cuisine": new_recipe.cuisine,
                    "cooking_methods": new_recipe.cooking_methods,
                    "recipe_keys": new_recipe.recipe_keys,
                },
                "similar_recipes_used": [
                    {
                        "document_title": item.get("document_title", "Unknown"),
                        "similarity_score": item.get("vector_similarity", 0),
                    }
                    for item in similar_recipes[:3]  # Limit to top 3 for clarity
                ],
                "recipe_query": query,
            }

        except Exception as e:
            logger.error(f"Error generating recipe: {e}", exc_info=True)
            raise

    def _format_recipes_for_context(self, recipes: list) -> str:
        """Format a list of recipes into a context string for the LLM."""
        logger.info(f"Formatting {len(recipes)} recipes for context")
        context = "Here are some similar recipes to use as reference:\n\n"

        for i, recipe in enumerate(recipes, 1):
            title = recipe.get("document_title", "Unknown")
            context += f"RECIPE {i}:\n"
            context += f"Title: {title}\n"
            content_excerpt = (
                recipe.get("content", "")[:500] + "..."
                if len(recipe.get("content", "")) > 500
                else recipe.get("content", "")
            )
            context += f"Content: {recipe.get('content', '')}\n\n"
            logger.debug(
                f"Added recipe '{title}' to context (content length: {len(recipe.get('content', ''))} chars)"
            )

        logger.info(
            f"Context preparation complete, total context size: {len(context)} characters"
        )
        return context

    def _save_recipe_to_database(self, title: str, recipe_content: str) -> Recipe:
        """Save the generated recipe to the database."""
        logger.info(f"Saving recipe to database with title: '{title}'")
        # Parse the JSON content if needed
        try:
            # Remove markdown code block markers if present
            logger.debug(f"Processing raw recipe content ({len(recipe_content)} chars)")
            cleaned_content = (
                recipe_content.replace("```json", "").replace("```", "").strip()
            )
            logger.debug(f"Cleaned content for JSON parsing")

            try:
                recipe_data = json.loads(cleaned_content)
                logger.info(f"Successfully parsed JSON content")

                # Log recipe structure
                logger.debug(f"Recipe structure: title='{recipe_data.get('title')}'")
                logger.debug(
                    f"Recipe has {len(recipe_data.get('ingredients', []))} ingredients"
                )
                logger.debug(
                    f"Recipe has {len(recipe_data.get('instructions', []))} instruction steps"
                )

                # Create formatted content for instructions
                instructions_text = "\n\n".join(
                    [
                        f"# Ingredients\n"
                        + "\n".join(
                            [f"- {ing}" for ing in recipe_data.get("ingredients", [])]
                        ),
                        f"# Instructions\n"
                        + "\n".join(
                            [
                                f"{i+1}. {step}"
                                for i, step in enumerate(
                                    recipe_data.get("instructions", [])
                                )
                            ]
                        ),
                        f"# Nutritional Information\n"
                        + f"Calories: {recipe_data.get('nutritional_info', {}).get('calories', 'N/A')}\n"
                        + f"Protein: {recipe_data.get('nutritional_info', {}).get('protein', 'N/A')}\n"
                        + f"Carbs: {recipe_data.get('nutritional_info', {}).get('carbs', 'N/A')}\n"
                        + f"Fat: {recipe_data.get('nutritional_info', {}).get('fat', 'N/A')}\n\n"
                        + f"Prep Time: {recipe_data.get('prep_time_minutes', 'N/A')} minutes\n"
                        + f"Cook Time: {recipe_data.get('cook_time_minutes', 'N/A')} minutes",
                    ]
                )

                logger.debug(
                    f"Formatted instructions text created ({len(instructions_text)} chars)"
                )

                new_recipe = Recipe.objects.create(
                    title=recipe_data.get("title", title),
                    description=recipe_data.get("description", ""),
                    blog_content=recipe_data.get("blog_content", ""),
                    difficulty=recipe_data.get("difficulty", "beginner"),
                    season=recipe_data.get("season", "all_year"),
                    instructions=instructions_text,
                    keywords=recipe_data.get("keywords", ""),
                    ingredients=json.dumps(
                        recipe_data.get("ingredients", []), ensure_ascii=False
                    ),
                    subtitle=recipe_data.get("subtitle", ""),
                    course=recipe_data.get("course", "Obiad"),
                    cuisine=recipe_data.get("cuisine", "Rodzaj kuchni"),
                    cooking_methods=json.dumps(
                        recipe_data.get("cooking_methods", []), ensure_ascii=False
                    ),
                    recipe_keys=json.dumps(
                        recipe_data.get("recipe_keys", []), ensure_ascii=False
                    ),
                )
                logger.info(f"Recipe created in database with ID: {new_recipe.id}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON content: {e}")
                logger.debug(f"Problematic content: {cleaned_content[:500]}...")

                # Fallback if JSON parsing fails
                new_recipe = Recipe.objects.create(
                    title=title,
                    description="Generated recipe",
                    instructions=recipe_content,
                )
                logger.info(
                    f"Created fallback recipe with raw content, ID: {new_recipe.id}"
                )

        except Exception as e:
            logger.error(f"Unexpected error saving recipe: {e}", exc_info=True)
            # Last resort fallback
            new_recipe = Recipe.objects.create(
                title=title,
                description="Recipe generation encountered an error",
                instructions="Error occurred during recipe generation and formatting.",
            )
            logger.info(f"Created error fallback recipe, ID: {new_recipe.id}")

        return new_recipe

    def _generate_recipe_image(self, recipe, public_base_url: str = "") -> str:
        """
        Generate an image for the recipe using OpenAI's DALL-E model,
        download it, and save it locally.
        """
        try:
            logger.info(f"Generating image for recipe: '{recipe.title}'")

            # Create a detailed prompt that describes the dish
            recipe_description = (
                recipe.description if hasattr(recipe, "description") else ""
            )

            prompt = get_image_prompt(recipe.title, recipe_description)

            # 1. Generujemy tymczasowy URL z OpenAI
            temp_image_url = self.openai_service.generate_image(
                prompt=prompt, size="1024x1024", quality="standard", model="dall-e-3"
            )

            # 2. Pobieramy fizyczny plik z OpenAI zanim link wygaśnie
            logger.info(f"Downloading image from OpenAI: {temp_image_url}")
            response = requests.get(temp_image_url)

            if response.status_code == 200:
                # 3. Tworzymy unikalną nazwę pliku
                file_ext = "png"  # DALL-E zwraca PNG
                filename = f"recipes/{recipe.id}_{uuid.uuid4().hex[:8]}.{file_ext}"

                # 4. Zapisujemy plik w MEDIA_ROOT
                saved_path = default_storage.save(
                    filename, ContentFile(response.content)
                )

                # 5. Tworzymy trwały, lokalny URL
                # Zakładamy, że WordPress widzi Django pod localhost:8000
                local_url = f"{public_base_url}{settings.MEDIA_URL}{saved_path}"

                logger.info(f"Image saved locally at: {saved_path}")
                logger.info(f"Permanent local URL: {local_url}")

                return local_url
            else:
                logger.error(
                    f"Failed to download image from OpenAI. Status: {response.status_code}"
                )
                # ZWRACAMY LOKALNY PLACEHOLDER
                return f"{public_base_url}{settings.STATIC_URL}img/recipe-placeholder.jpg"

        except Exception as e:
            logger.error(f"Error generating image for recipe: {e}", exc_info=True)
            # ZWRACAMY LOKALNY PLACEHOLDER
            return f"{public_base_url}{settings.STATIC_URL}img/recipe-placeholder.jpg"
