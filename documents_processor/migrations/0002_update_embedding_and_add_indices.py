from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('documents_processor', '0001_initial'),
    ]
    
    operations = [
        # 1. Add dedicated tsvector column
        migrations.RunSQL(
            """
            ALTER TABLE documents_processor_documentchunk 
            ADD COLUMN content_tsv tsvector GENERATED ALWAYS AS 
                (to_tsvector('simple', coalesce(content, ''))) STORED;
            """,
            "ALTER TABLE documents_processor_documentchunk DROP COLUMN IF EXISTS content_tsv;"
        ),
        
        # 2. Add GIN index for text search
        migrations.RunSQL(
            """
            CREATE INDEX document_chunk_content_tsv_idx 
            ON documents_processor_documentchunk USING GIN(content_tsv);
            """,
            "DROP INDEX IF EXISTS document_chunk_content_tsv_idx;"
        ),
        
        # 3. Add IVFFlat index for vector search (works for dimensions <= 2000)
        migrations.RunSQL(
            """
            CREATE INDEX document_chunk_embedding_ivfflat_idx 
            ON documents_processor_documentchunk 
            USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
            """,
            "DROP INDEX IF EXISTS document_chunk_embedding_ivfflat_idx;"
        ),
    ]
