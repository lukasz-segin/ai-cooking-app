from django.urls import path
from .views import RecipeListCreateAPIView, search_recipes

urlpatterns = [
    path('recipes/', RecipeListCreateAPIView.as_view(), name='recipe-list-create'),
    path('recipes/search/', search_recipes, name='recipe-semantic-search'),
]
