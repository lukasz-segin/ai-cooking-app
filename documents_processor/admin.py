from django.contrib import admin
from django.utils.html import format_html
from .models import StoredDocument, DocumentChunk

class DocumentChunkInline(admin.TabularInline):
    model = DocumentChunk
    fields = ('chunk_index', 'content_preview', 'created_at')
    readonly_fields = ('chunk_index', 'content_preview', 'created_at')
    can_delete = False
    extra = 0
    max_num = 0
    
    def content_preview(self, obj):
        if obj.content:
            preview = obj.content[:150] + "..." if len(obj.content) > 150 else obj.content
            return preview
        return "-"
    content_preview.short_description = "Content"
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(StoredDocument)
class StoredDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'chunks_count', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'description', 'file_path')
    readonly_fields = ('id', 'created_at', 'updated_at', 'chunks_count')
    inlines = [DocumentChunkInline]
    
    def chunks_count(self, obj):
        count = obj.chunks.count()
        if count > 0:
            return format_html(
                '<a href="{}?document__id={}">{} chunks</a>',
                '/admin/documents_processor/documentchunk/',
                obj.id,
                count
            )
        return "No chunks"
    chunks_count.short_description = "Chunks"

@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ('id', 'document_link', 'chunk_index', 'content_preview', 'created_at')
    list_filter = ('created_at', 'document')
    search_fields = ('content', 'document__title')
    readonly_fields = ('embedding_dimensions', 'document', 'chunk_index', 'created_at')
    
    def content_preview(self, obj):
        if obj.content:
            preview = obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
            return preview
        return "-"
    content_preview.short_description = "Content"
    
    def document_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            f'/admin/documents_processor/storeddocument/{obj.document.id}/change/',
            obj.document.title
        )
    document_link.short_description = "Document"
    
    def embedding_dimensions(self, obj):
        if hasattr(obj, 'embedding') and obj.embedding is not None:
            return f"{len(obj.embedding)} dimensions"
        return "No embedding"
    embedding_dimensions.short_description = "Embedding"
