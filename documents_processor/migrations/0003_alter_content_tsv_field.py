from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('documents_processor', '0002_update_embedding_and_add_indices'),
    ]
    
    operations = [
        # Update the existing content_tsv column
        migrations.RunSQL(
            """
            -- First drop the existing constraints and definition
            ALTER TABLE documents_processor_documentchunk 
            ALTER COLUMN content_tsv DROP NOT NULL,
            ALTER COLUMN content_tsv DROP EXPRESSION;
            
            -- Then recreate as a normal column
            COMMENT ON COLUMN documents_processor_documentchunk.content_tsv IS 
            'Generated search vector column that should not be set directly';
            """,
            # Reverse SQL (optional)
            """
            ALTER TABLE documents_processor_documentchunk 
            ALTER COLUMN content_tsv SET GENERATED ALWAYS AS 
                (to_tsvector('simple', coalesce(content, ''))) STORED;
            """
        ),
    ] 