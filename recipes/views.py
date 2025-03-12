from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Recipe
from .serializers import RecipeSerializer
from .services.recipe_search_service import RecipeSearchService

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
