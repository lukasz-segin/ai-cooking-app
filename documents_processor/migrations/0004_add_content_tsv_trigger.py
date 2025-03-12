from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('documents_processor', '0003_alter_content_tsv_field'),
    ]
    
    operations = [
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION update_document_chunk_tsvector() RETURNS TRIGGER AS $$
            BEGIN
                NEW.content_tsv = to_tsvector('simple', coalesce(NEW.content, ''));
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            
            CREATE TRIGGER document_chunk_tsvector_update
            BEFORE INSERT OR UPDATE OF content
            ON documents_processor_documentchunk
            FOR EACH ROW
            EXECUTE FUNCTION update_document_chunk_tsvector();
            """,
            # Reverse SQL (optional)
            """
            DROP TRIGGER IF EXISTS document_chunk_tsvector_update ON documents_processor_documentchunk;
            DROP FUNCTION IF EXISTS update_document_chunk_tsvector();
            """
        ),
    ] 