from django.conf import settings
from django.core.cache import cache
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from .models import Recipe
from .serializers import RecipeSerializer
from .services.recipe_search_service import RecipeSearchService
from .services.recipe_generator_service import RecipeGeneratorService

GENERATE_DAILY_CACHE_KEY = "recipe_generate_daily_count"
GENERATE_DAILY_CACHE_SECONDS = 60 * 60 * 24


class RecipeListCreateAPIView(generics.ListCreateAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return [AllowAny()]


def _bounded_positive_int(raw_value, default, maximum):
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    if value < 1:
        return 1
    if value > maximum:
        return maximum
    return value


def _text_within_limit(value, maximum):
    text = (value or "").strip()
    if len(text) > maximum:
        return None
    return text


def _consume_generate_daily_allowance():
    cap = settings.THROTTLE_GENERATE_DAILY_CAP
    if cap < 1:
        return False
    if cache.add(GENERATE_DAILY_CACHE_KEY, 1, GENERATE_DAILY_CACHE_SECONDS):
        return True
    try:
        count = cache.incr(GENERATE_DAILY_CACHE_KEY)
    except ValueError:
        cache.set(GENERATE_DAILY_CACHE_KEY, 1, GENERATE_DAILY_CACHE_SECONDS)
        return True
    return count <= cap


@api_view(["GET"])
@permission_classes([AllowAny])
def search_recipes(request):
    """
    Search for recipes semantically similar to the provided meal name.

    Query Parameters:
        meal_name: The name of the meal to search for
        limit: Maximum number of results to return (default: 5)
    """
    meal_name = _text_within_limit(
        request.query_params.get("meal_name", ""),
        settings.RECIPE_QUERY_MAX_LENGTH,
    )
    if meal_name is None:
        return Response(
            {
                "error": (
                    f"meal_name must be at most {settings.RECIPE_QUERY_MAX_LENGTH} characters"
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not meal_name:
        return Response(
            {"error": "meal_name parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    limit = _bounded_positive_int(
        request.query_params.get("limit", "5"),
        default=5,
        maximum=settings.RECIPE_RESULT_LIMIT_MAX,
    )

    try:
        search_service = RecipeSearchService()
        results = search_service.search_recipes_by_semantic(meal_name, limit=limit)

        return Response(
            {
                "query": meal_name,
                "results_count": len(results),
                "results": results,
            }
        )

    except Exception as e:
        return Response(
            {"error": f"Error performing semantic search: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


search_recipes.cls.throttle_scope = "search"


@api_view(["POST"])
@permission_classes([AllowAny])
def generate_recipe(request):
    """
    Generate a new recipe based on provided query, using similar existing recipes.

    Request Body:
        query: The recipe name or concept to generate
        num_examples: (Optional) Number of similar recipes to use as examples (default: 3)
    """
    if not settings.RECIPE_GENERATION_ENABLED:
        return Response(
            {"error": "Recipe generation is temporarily disabled"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    query = _text_within_limit(
        request.data.get("query", ""),
        settings.RECIPE_QUERY_MAX_LENGTH,
    )
    if query is None:
        return Response(
            {
                "error": (
                    f"query must be at most {settings.RECIPE_QUERY_MAX_LENGTH} characters"
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not query:
        return Response(
            {"error": "query parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    num_examples = _bounded_positive_int(
        request.data.get("num_examples", "3"),
        default=3,
        maximum=settings.RECIPE_RESULT_LIMIT_MAX,
    )

    if not _consume_generate_daily_allowance():
        return Response(
            {"error": "Daily recipe generation limit reached"},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    try:
        generator_service = RecipeGeneratorService()
        public_base_url = request.build_absolute_uri("/").rstrip("/")
        result = generator_service.generate_recipe(
            query,
            num_examples=num_examples,
            public_base_url=public_base_url,
        )

        return Response(result)

    except Exception as e:
        return Response(
            {"error": f"Error generating recipe: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


generate_recipe.cls.throttle_scope = "generate"
