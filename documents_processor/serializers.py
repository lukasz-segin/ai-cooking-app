from rest_framework import serializers
from .models import StoredDocument, DocumentChunk

class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = ['id', 'chunk_index', 'content', 'created_at']

class StoredDocumentSerializer(serializers.ModelSerializer):
    chunks = DocumentChunkSerializer(many=True, read_only=True)

    class Meta:
        model = StoredDocument
        fields = ['id', 'file_path', 'title', 'description', 'status', 'created_at', 'updated_at', 'chunks'] 