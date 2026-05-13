"""
Migration: Add Full-Text Search (FTS) support for BM25

Purpose:
- Enable PostgreSQL SearchVector for efficient BM25 scoring
- Create GIN index on DocumentChunk content field
- Support BM25Searcher implementation

Usage:
    python manage.py migrate documents

Note:
    This migration requires PostgreSQL extension: pg_trgm (trigram)
    Enable with: CREATE EXTENSION IF NOT EXISTS pg_trgm;
"""

from django.db import migrations, models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('documents', '0008_add_granted_by_to_permissions'),
    ]

    operations = [
        # Step 1: Add SearchVector field to DocumentChunk
        migrations.RunSQL(
            sql="""
            ALTER TABLE document_chunks
            ADD COLUMN IF NOT EXISTS search_vector tsvector;
            """,
            reverse_sql="""
            ALTER TABLE document_chunks
            DROP COLUMN IF EXISTS search_vector;
            """,
            state_operations=[
                migrations.AddField(
                    model_name='documentchunk',
                    name='search_vector',
                    field=SearchVectorField(null=True, blank=True, verbose_name='FTS Search Vector'),
                    preserve_default=False,
                ),
            ],
        ),

        # Step 2: Create GIN index for efficient FTS queries
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS documentchunk_search_vector_gin_idx
            ON document_chunks USING gin (search_vector);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS documentchunk_search_vector_gin_idx;
            """,
            state_operations=[
                migrations.AddIndex(
                    model_name='documentchunk',
                    index=GinIndex(
                        fields=['search_vector'],
                        name='documentchunk_search_vector_gin_idx',
                    ),
                ),
            ],
        ),

        # Step 3: Ensure trigram support is enabled before creating the fallback index
        migrations.RunSQL(
            sql="""
            CREATE EXTENSION IF NOT EXISTS pg_trgm;
            """,
            reverse_sql=migrations.RunSQL.noop,
            state_operations=[],
        ),

        # Step 4: Create trigram index for ILIKE fallback
        migrations.RunSQL(
            sql="""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS documentchunk_content_trgm_idx 
            ON document_chunks USING gin (content gin_trgm_ops);
            """,
            reverse_sql="""
            DROP INDEX CONCURRENTLY IF EXISTS documentchunk_content_trgm_idx;
            """,
            state_operations=[],
        ),

        # Step 5: Create function to auto-update search_vector on insert/update
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION update_documentchunk_search_vector() RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector := setweight(
                    to_tsvector('english', COALESCE(NEW.content, '')), 'A'
                ) ||
                setweight(
                    to_tsvector('english', COALESCE(NEW.summary, '')), 'B'
                );
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            
            DROP TRIGGER IF EXISTS documentchunk_search_vector_trigger ON document_chunks;
            
            CREATE TRIGGER documentchunk_search_vector_trigger
            BEFORE INSERT OR UPDATE ON document_chunks
            FOR EACH ROW
            EXECUTE PROCEDURE update_documentchunk_search_vector();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS documentchunk_search_vector_trigger ON document_chunks;
            DROP FUNCTION IF EXISTS update_documentchunk_search_vector();
            """,
            state_operations=[],
        ),

        # Step 6: Update existing records with search_vector
        migrations.RunSQL(
            sql="""
            UPDATE document_chunks 
            SET search_vector = setweight(
                to_tsvector('english', COALESCE(content, '')), 'A'
            ) ||
            setweight(
                to_tsvector('english', COALESCE(summary, '')), 'B'
            )
            WHERE search_vector IS NULL;
            """,
            reverse_sql="""
            UPDATE document_chunks SET search_vector = NULL;
            """,
            state_operations=[],
        ),
    ]