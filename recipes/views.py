from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Recipe
from .serializers import RecipeSerializer
from .services.recipe_search_service import RecipeSearchService
from .services.recipe_generator_service import RecipeGeneratorService
from recipes.models.chat_models import ChatRequest, Message

class RecipeListCreateAPIView(generics.ListCreateAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer

@api_view(['GET'])
def search_recipes(request):
    """
    Search for recipes semantically similar to the provided meal name.
    
    Query Parameters:
        meal_name: The name of the meal to search for
        limit: Maximum number of results to return (default: 5)
    """
    meal_name = request.query_params.get('meal_name', '')
    if not meal_name:
        return Response(
            {"error": "meal_name parameter is required"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        limit = int(request.query_params.get('limit', '5'))
    except ValueError:
        limit = 5
    
    try:
        search_service = RecipeSearchService()
        results = search_service.search_recipes_by_semantic(meal_name, limit=limit)
        
        return Response({
            "query": meal_name,
            "results_count": len(results),
            "results": results
        })
        
    except Exception as e:
        return Response(
            {"error": f"Error performing semantic search: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def generate_recipe(request):
    """
    Generate a new recipe based on provided query, using similar existing recipes.
    
    Request Body:
        query: The recipe name or concept to generate
        num_examples: (Optional) Number of similar recipes to use as examples (default: 3)
    """
    query = request.data.get('query', '')
    if not query:
        return Response(
            {"error": "query parameter is required"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        num_examples = int(request.data.get('num_examples', '3'))
    except ValueError:
        num_examples = 3
    
    try:
        # Initialize the generator service
        generator_service = RecipeGeneratorService()
        
        # Call the generation method (now synchronous)
        result = generator_service.generate_recipe(query, num_examples=num_examples)
        
        return Response(result)
        
    except Exception as e:
        return Response(
            {"error": f"Error generating recipe: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
