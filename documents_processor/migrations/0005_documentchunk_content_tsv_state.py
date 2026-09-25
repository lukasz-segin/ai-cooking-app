import django.contrib.postgres.search
from django.db import migrations


class Migration(migrations.Migration):
    """Record content_tsv in Django's migration state.

    0002 created the column with raw SQL and 0004 fills it with a trigger, so
    the database already has it. This migration only updates the state, so a
    later makemigrations does not try to add the column again.
    """

    dependencies = [
        ("documents_processor", "0004_add_content_tsv_trigger"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="documentchunk",
                    name="content_tsv",
                    field=django.contrib.postgres.search.SearchVectorField(
                        db_default=True, null=True
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
