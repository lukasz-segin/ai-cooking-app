from rest_framework import serializers
from .models import Recipe

class RecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ['id', 'title', 'description', 'blog_content', 'difficulty', 'season',  'keywords',  'ingredients', 'instructions', 'image_url', 'created_at', 'updated_at']
