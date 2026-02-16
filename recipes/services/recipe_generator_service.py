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
            logger.info(f"Starting recipe generation for query: '{query}' with {num_examples} examples")
            
            # Step 1: Find similar recipes to use as examples
            logger.info(f"Step 1: Searching for similar recipes using semantic search")
            similar_recipes = self.search_service.search_recipes_by_semantic(query, limit=num_examples)
            logger.info(f"Found {len(similar_recipes)} similar recipes")
            
            # Log titles and similarity scores of found recipes
            for i, recipe in enumerate(similar_recipes, 1):
                logger.info(f"Similar recipe {i}: '{recipe.get('document_title', 'Unknown')}' (similarity: {recipe.get('vector_similarity', 0):.4f})")
            
            # Step 2: Format similar recipes as context for the LLM
            logger.info(f"Step 2: Formatting recipes for context")
            recipes_context = self._format_recipes_for_context(similar_recipes)
            logger.debug(f"Recipe context length: {len(recipes_context)} characters")
            
            # Step 3: Create a system prompt and user prompt
            logger.info(f"Step 3: Creating system and user prompts")
            # system_prompt = self._create_system_prompt(recipes_context)
            system_prompt = self._create_system_prompt_v2(recipes_context)
            # user_prompt = self._create_user_prompt(query)
            user_prompt = self._create_user_prompt_v2(query)
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
            content = response.content if hasattr(response, "content") else str(response)
            logger.debug(f"Raw LLM response: {content[:500]}..." if len(content) > 500 else content)
            
            # Step 6: Save the generated recipe to the database
            logger.info(f"Step 6: Saving generated recipe to database")
            new_recipe = self._save_recipe_to_database(query, content)
            logger.info(f"Recipe saved with ID: {new_recipe.id}, title: '{new_recipe.title}'")
            
            # Step 6.5: Generate an image for the recipe
            logger.info(f"Step 6.5: Generating image for recipe")
            image_url = self._generate_recipe_image(new_recipe)
            logger.info(f"Image generated for recipe: {image_url}")
            
            # If you have image_url field in your model:
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
                    "instructions": new_recipe.instructions,
                    "image_url": image_url  # Add the image URL to the response
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
        logger.info(f"Formatting {len(recipes)} recipes for context")
        context = "Here are some similar recipes to use as reference:\n\n"
        
        for i, recipe in enumerate(recipes, 1):
            title = recipe.get('document_title', 'Unknown')
            context += f"RECIPE {i}:\n"
            context += f"Title: {title}\n"
            content_excerpt = recipe.get('content', '')[:500] + "..." if len(recipe.get('content', '')) > 500 else recipe.get('content', '')
            context += f"Content: {recipe.get('content', '')}\n\n"
            logger.debug(f"Added recipe '{title}' to context (content length: {len(recipe.get('content', ''))} chars)")
        
        logger.info(f"Context preparation complete, total context size: {len(context)} characters")
        return context
    
    def _create_system_prompt(self, recipes_context: str) -> str:
        """Create a system prompt with instructions and recipe examples."""
        logger.info(f"Creating system prompt with recipes context")
        prompt = f"""Jesteś profesjonalnym szefem kuchni i twórcą przepisów. Twoim zadaniem jest stworzenie nowego przepisu WYŁĄCZNIE na podstawie dostarczonych przykładów.

WAŻNE ZASADY:
1. Użyj TYLKO składników i technik, które występują w podanych przykładach przepisów
2. NIE dodawaj kreatywnych lub nowych składników, których nie ma w przykładach
3. NIE wymyślaj nowych kroków przygotowania, które nie są oparte na przykładach
4. Pisz przepis W CAŁOŚCI PO POLSKU
5. Bazuj ściśle na strukturze i stylu przykładowych przepisów

Przepis powinien zawierać:
1. Tytuł (po polsku)
2. Listę składników z dokładnymi miarami (używaj miar metrycznych: g, ml, łyżka, łyżeczka)
3. Instrukcje krok po kroku
4. Informacje o wartościach odżywczych (przybliżone kalorie i makroskładniki)
5. Czas przygotowania i czas gotowania

Użyj poniższych podobnych przepisów jako podstawy, nie dodając niczego spoza nich:

{recipes_context}

Sformatuj odpowiedź jako obiekt JSON z następującymi polami:
- title: string (tytuł po polsku)
- description: string (opis po polsku)
- ingredients: array of strings (składniki po polsku)
- instructions: array of strings (instrukcje po polsku)
- nutritional_info: object with calories, protein, carbs, fat (wartości odżywcze po polsku)
- prep_time_minutes: number (czas przygotowania w minutach)
- cook_time_minutes: number (czas gotowania w minutach)

Bądź precyzyjny i upewnij się, że przepis jest praktyczny i może być łatwo wykonany przez domowych kucharzy. Cały przepis MUSI być w języku polskim.
"""
        logger.debug(f"System prompt created with length {len(prompt)} characters")
        return prompt
    
    def _create_system_prompt_v2(self, recipes_context: str) -> str:
        """Create a system prompt with instructions and recipe examples (version 2)."""
        prompt = f"""
        Jesteś profesjonalnym szefem kuchni, który precyzyjnie generuje przepisy na podstawie przekazanych danych.  

        **Ważne zasady generowania przepisu (OBOWIĄZKOWE):**  
        1. Przepis MUSI być utworzony TYLKO na podstawie dostarczonych przykładów przepisów.  
        2. NIE MOŻESZ dodawać ŻADNYCH nowych składników, których NIE MA w przykładach.  
        3. NIE MOŻESZ używać technik ani kroków przygotowania, których NIE MA w przykładach.  
        4. NIE WOLNO dodawać własnych informacji, porad, ani wariacji składników poza dostarczonym kontekstem.  
        3. Całość przepisów MUSI być w języku polskim.  
        4. Każda sekcja przepisu musi ściśle bazować na podanych przykładach i musi być realistyczna oraz wykonalna.  
        5. Jeśli w przykładach nie ma dokładnych informacji o kaloriach lub wartościach odżywczych, nie wymyślaj tych danych - podaj orientacyjne wartości tylko jeśli są dostępne w przykładach.
        6. NIE WOLNO CI szacować wartości odżywczych. Jeśli brakuje tych informacji w przykładach, wpisz: "Brak danych".
        7. Informacje o wartościach odżywczych (kalorie, białko, węglowodany, tłuszcze) MUSZĄ pochodzić WYŁĄCZNIE z dostarczonych przykładów. Jeśli dane te nie występują w przykładach, wpisz „Brak danych” zamiast podawać jakiekolwiek wartości szacunkowe.


        **Dostarczone przepisy (Użyj TYLKO poniższych informacji):**  
        {recipes_context}

        **WYMAGANA struktura odpowiedzi (format JSON):**  
        ```json
        {{
        "title": "Tytuł przepisu",
        "description": "Krótki opis przepisu",
        "ingredients": [
            "składnik 1 - ilość",
            "składnik 2 - ilość"
        ],
        "instructions": [
            "Krok 1 instrukcji",
            "Krok 2 instrukcji"
        ],
        "nutritional_info": {{
            "calories": liczba kalorii,
            "protein": "ilość białka",
            "carbs": "ilość węglowodanów",
            "fat": "ilość tłuszczów"
        }},
        "prep_time_minutes": liczba,
        "cook_time_minutes": liczba
        }}
        ```
        Nie wolno ci użyć niczego, czego nie znajdziesz w podanych przykładach.
        """
        logger.debug(f"System prompt V2 created with length {len(prompt)} characters")
        return prompt
    
    def _create_user_prompt(self, query: str) -> str:
        """Create a user prompt based on the query."""
        logger.info(f"Creating user prompt for query: '{query}'")
        prompt = f"""Stwórz nowy przepis dla "{query}" WYŁĄCZNIE na podstawie podanych przykładów. 
        
NIE dodawaj żadnych składników ani technik, których nie ma w przykładach.
Odpowiedź powinna być W CAŁOŚCI PO POLSKU i zawierać wszystkie wymagane sekcje w formacie JSON.
Upewnij się, że przepis jest praktyczny i bazuje tylko na informacjach z przykładowych przepisów."""
        logger.debug(f"User prompt created: {prompt}")
        return prompt
    
    def _create_user_prompt_v2(self, query: str) -> str:
        prompt = f"""Na podstawie podanych przykładów przepisów utwórz nowy, kompletny przepis na "{query}".

        Ważne zasady:
        - NIE dodawaj żadnych składników ani metod przygotowania, które nie zostały wymienione w dostarczonych przykładach.
        - Bazuj WYŁĄCZNIE na istniejących składnikach, proporcjach oraz sposobach przygotowania widocznych w podanych przykładach.
        - Całość odpowiedzi MUSI być w języku polskim i w formacie JSON, zgodnym z podanym wcześniej wzorem.
        - Twój przepis MUSI być realistyczny i praktyczny oraz ściśle opierać się na podanych przykładach.

        Odpowiedź zwróć WYŁĄCZNIE w podanym formacie JSON. Nie dodawaj komentarzy ani dodatkowych informacji.
        """
        return prompt
    
    def _save_recipe_to_database(self, title: str, recipe_content: str) -> Recipe:
        """Save the generated recipe to the database."""
        logger.info(f"Saving recipe to database with title: '{title}'")
        # Parse the JSON content if needed
        try:
            # Remove markdown code block markers if present
            logger.debug(f"Processing raw recipe content ({len(recipe_content)} chars)")
            cleaned_content = recipe_content.replace("```json", "").replace("```", "").strip()
            logger.debug(f"Cleaned content for JSON parsing")
            
            try:
                recipe_data = json.loads(cleaned_content)
                logger.info(f"Successfully parsed JSON content")
                
                # Log recipe structure
                logger.debug(f"Recipe structure: title='{recipe_data.get('title')}'")
                logger.debug(f"Recipe has {len(recipe_data.get('ingredients', []))} ingredients")
                logger.debug(f"Recipe has {len(recipe_data.get('instructions', []))} instruction steps")
                
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
                
                logger.debug(f"Formatted instructions text created ({len(instructions_text)} chars)")
                
                new_recipe = Recipe.objects.create(
                    title=recipe_data.get("title", title),
                    description=recipe_data.get("description", ""),
                    instructions=instructions_text
                )
                logger.info(f"Recipe created in database with ID: {new_recipe.id}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON content: {e}")
                logger.debug(f"Problematic content: {cleaned_content[:500]}...")
                
                # Fallback if JSON parsing fails
                new_recipe = Recipe.objects.create(
                    title=title,
                    description="Generated recipe",
                    instructions=recipe_content
                )
                logger.info(f"Created fallback recipe with raw content, ID: {new_recipe.id}")
            
        except Exception as e:
            logger.error(f"Unexpected error saving recipe: {e}", exc_info=True)
            # Last resort fallback
            new_recipe = Recipe.objects.create(
                title=title,
                description="Recipe generation encountered an error",
                instructions="Error occurred during recipe generation and formatting."
            )
            logger.info(f"Created error fallback recipe, ID: {new_recipe.id}")
            
        return new_recipe

    def _generate_recipe_image(self, recipe) -> str:
        """
        Generate an image for the recipe using OpenAI's DALL-E model,
        download it, and save it locally.
        """
        try:
            logger.info(f"Generating image for recipe: '{recipe.title}'")
            
            # Create a detailed prompt that describes the dish
            recipe_description = recipe.description if hasattr(recipe, 'description') else ""
            prompt = f"""
            A professional, appetizing food photograph of a Polish dish: {recipe.title}.
            {recipe_description}

            The image should be a top-down view or slight angle of the beautifully plated dish, 
            with natural lighting, shallow depth of field, and styled as a professional 
            food photography shot. Show the prepared dish clearly with appropriate garnishes 
            and styling elements. No text or watermarks.
            """

            # 1. Generujemy tymczasowy URL z OpenAI
            temp_image_url = self.openai_service.generate_image(
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                model="dall-e-3"
            )

            # 2. Pobieramy fizyczny plik z OpenAI zanim link wygaśnie
            logger.info(f"Downloading image from OpenAI: {temp_image_url}")
            response = requests.get(temp_image_url)

            if response.status_code == 200:
                # 3. Tworzymy unikalną nazwę pliku
                file_ext = "png"  # DALL-E zwraca PNG
                filename = f"recipes/{recipe.id}_{uuid.uuid4().hex[:8]}.{file_ext}"

                # 4. Zapisujemy plik w MEDIA_ROOT
                saved_path = default_storage.save(filename, ContentFile(response.content))

                # 5. Tworzymy trwały, lokalny URL
                # Zakładamy, że WordPress widzi Django pod localhost:8000
                local_url = f"http://localhost:8000{settings.MEDIA_URL}{saved_path}"

                logger.info(f"Image saved locally at: {saved_path}")
                logger.info(f"Permanent local URL: {local_url}")

                return local_url
            else:
                logger.error(f"Failed to download image from OpenAI. Status: {response.status_code}")
                return "https://placeholder.com/food-placeholder-image"

        except Exception as e:
            logger.error(f"Error generating image for recipe: {e}", exc_info=True)
            return "https://placeholder.com/food-placeholder-image"