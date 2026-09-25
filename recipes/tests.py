from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from rest_framework.settings import api_settings
from rest_framework.test import APITestCase
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle

from recipes.models import Recipe
from recipes.services.recipe_generator_service import RecipeGeneratorService

THROTTLED_REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",
        "user": "1000/day",
        "search": "30/hour",
        "generate": "1/hour",
    },
    "NUM_PROXIES": 0,
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
}


@override_settings(REST_FRAMEWORK=THROTTLED_REST_FRAMEWORK)
class RecipeApiSecurityTests(APITestCase):
    def setUp(self):
        cache.clear()
        api_settings.reload()
        self._original_rates = ScopedRateThrottle.THROTTLE_RATES
        rates = {
            "anon": "100/day",
            "user": "1000/day",
            "search": "30/hour",
            "generate": "1/hour",
        }
        AnonRateThrottle.THROTTLE_RATES = rates
        UserRateThrottle.THROTTLE_RATES = rates
        ScopedRateThrottle.THROTTLE_RATES = rates

    def tearDown(self):
        cache.clear()
        AnonRateThrottle.THROTTLE_RATES = self._original_rates
        UserRateThrottle.THROTTLE_RATES = self._original_rates
        ScopedRateThrottle.THROTTLE_RATES = self._original_rates
        api_settings.reload()

    def test_anonymous_recipe_create_is_forbidden(self):
        response = self.client.post(
            "/api/recipes/",
            {"title": "Zupa", "description": "Opis", "instructions": "Kroki"},
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))

    def test_anonymous_document_process_is_forbidden(self):
        response = self.client.post(
            "/api/documents/process_document/",
            {"file_name": "notes.pdf"},
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))

    @patch("recipes.views.RecipeSearchService")
    def test_anonymous_search_is_allowed(self, search_service):
        search_service.return_value.search_recipes_by_semantic.return_value = []
        response = self.client.get("/api/recipes/search/", {"meal_name": "zupa"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results_count"], 0)

    @patch("recipes.views.RecipeGeneratorService")
    def test_generate_returns_429_after_configured_limit(self, generator_service):
        generator_service.return_value.generate_recipe.return_value = {
            "status": "success",
            "recipe": {},
        }
        first = self.client.post(
            "/api/recipes/generate/",
            {"query": "zupa pomidorowa"},
            format="json",
        )
        second = self.client.post(
            "/api/recipes/generate/",
            {"query": "zupa pomidorowa"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(generator_service.return_value.generate_recipe.call_count, 1)

    def test_generate_is_disabled_by_kill_switch(self):
        with override_settings(RECIPE_GENERATION_ENABLED=False):
            with patch("recipes.views.RecipeGeneratorService") as generator_service:
                response = self.client.post(
                    "/api/recipes/generate/",
                    {"query": "zupa"},
                    format="json",
                )
        self.assertEqual(response.status_code, 503)
        generator_service.assert_not_called()


class DemoSurfaceTests(APITestCase):
    def test_landing_page_renders_forms(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="search-form"')
        self.assertContains(response, 'id="generate-form"')

    def test_schema_endpoint(self):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("openapi", response.data)


class RecipeImageFlagTests(APITestCase):
    @override_settings(RECIPE_IMAGE_GENERATION_ENABLED=False)
    @patch("recipes.services.recipe_generator_service.OpenAIService")
    @patch("recipes.services.recipe_generator_service.VectorService")
    @patch("recipes.services.recipe_generator_service.RecipeSearchService")
    @patch.object(RecipeGeneratorService, "_save_recipe_to_database")
    @patch.object(RecipeGeneratorService, "_generate_recipe_image")
    def test_image_generation_is_skipped_when_flag_is_off(
        self,
        image_generation,
        save_recipe,
        search_service,
        vector_service,
        openai_service,
    ):
        save_recipe.return_value = Recipe(
            title="Zupa",
            description="Opis",
            instructions="Kroki",
        )
        search_service.return_value.search_recipes_by_semantic.return_value = []
        openai_service.return_value.create_completion.return_value = SimpleNamespace(
            content="{}"
        )

        result = RecipeGeneratorService().generate_recipe("zupa")

        image_generation.assert_not_called()
        vector_service.assert_called()
        self.assertEqual(result["recipe"]["image_url"], "")
