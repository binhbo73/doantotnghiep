from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('documents', '0010_add_document_asset'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS docchunk_search_vec_gin
            ON document_chunks USING gin (search_vector);
            """,
            reverse_sql="""
            DROP INDEX CONCURRENTLY IF EXISTS docchunk_search_vec_gin;
            """,
            state_operations=[],
        ),
    ]
