"""
PostgreSQL Migration Guide - BM25 Full-Text Search
===================================================

Purpose: Enable Django SearchVector for BM25 scoring in HybridRetriever

Steps:
1. Create migration file
2. Add SearchVector GIN index to DocumentChunk.content
3. Test with sample data
4. Verify performance
"""

# To create migration, run:
# python manage.py makemigrations documents --name add_fts_index_to_chunks

# Generated migration file should look like:

from django.db import migrations
from django.contrib.postgres.search import SearchVector
from django.contrib.postgres.indexes import GinIndex


class Migration(migrations.Migration):

    dependencies = [
        ('documents', 'XXXX_previous_migration'),  # Update to actual previous migration
    ]

    operations = [
        # 1. Add SearchVector field for full-text search
        migrations.AddField(
            model_name='documentchunk',
            name='search_vector',
            field=None,  # This will be computed field
            preserve_default=False,
        ),

        # 2. Create GIN index for efficient full-text search
        migrations.AddIndex(
            model_name='documentchunk',
            index=GinIndex(
                fields=['search_vector'],
                name='documentchunk_search_vector_idx',
            ),
        ),

        # 3. Create function to update search_vector on insert/update
        migrations.RunSQL(
            sql="""
            ALTER TABLE documents_documentchunk
            ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                setweight(to_tsvector('english', COALESCE(content, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(document_id::text, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(page_number::text, '')), 'C')
            ) STORED;
            """,
            reverse_sql="ALTER TABLE documents_documentchunk DROP COLUMN search_vector;",
        ),

        # 4. Create index
        migrations.RunSQL(
            sql="CREATE INDEX documentchunk_search_vector_idx ON documents_documentchunk USING GIN (search_vector);",
            reverse_sql="DROP INDEX documentchunk_search_vector_idx;",
        ),
    ]


# Alternative: Simple migration for development
# (Add to documents/migrations/NNNN_add_fts_support.py)

from django.db import migrations, models
from django.contrib.postgres.search import SearchVector, SearchVectorField


class Migration(migrations.Migration):

    dependencies = [
        ('documents', 'XXXX_previous'),
    ]

    operations = [
        # Add SearchVectorField
        migrations.AddField(
            model_name='documentchunk',
            name='search_vector',
            field=SearchVectorField(null=True, blank=True),
        ),

        # Create index
        migrations.RunSQL(
            sql="""
            CREATE INDEX CONCURRENTLY documentchunk_search_idx 
            ON documents_documentchunk 
            USING GIN (search_vector);
            """,
            reverse_sql="DROP INDEX CONCURRENTLY documentchunk_search_idx;",
        ),

        # Update existing data
        migrations.RunSQL(
            sql="""
            UPDATE documents_documentchunk 
            SET search_vector = setweight(
                to_tsvector('english', COALESCE(content, '')), 'A'
            )
            WHERE search_vector IS NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]


# Usage in Django model (models/document_chunk.py):

class DocumentChunk(models.Model):
    # ... existing fields ...
    
    search_vector = SearchVectorField(null=True, blank=True)
    
    class Meta:
        indexes = [
            GinIndex(fields=['search_vector'], name='documentchunk_search_idx'),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-update search_vector on save
        if self.content:
            from django.contrib.postgres.search import SearchVector
            self.search_vector = SearchVector('content', weight='A')
        super().save(*args, **kwargs)


# Test after migration:

from backend.services.retrieval.bm25_searcher import BM25Searcher

searcher = BM25Searcher()

# Test 1: Simple search
results = searcher.search("test query", top_k=5)
print(f"Found {len(results)} results")

# Test 2: Term frequency
stats = searcher.get_term_frequency_stats("python code")
print(f"Term stats: {stats}")

# Test 3: Validate support
if BM25Searcher.validate_bm25_support():
    print("✓ PostgreSQL FTS available")
else:
    print("✗ PostgreSQL FTS not available")


# Performance comparison:

import time

queries = [
    "tìm thông tin về khách hàng",
    "mã số 12345",
    "report tháng 1",
    "python django template",
]

# Before: icontains
print("\n--- icontains Performance ---")
for q in queries:
    start = time.time()
    chunks = DocumentChunk.objects.filter(content__icontains=q)[:10]
    elapsed = (time.time() - start) * 1000
    print(f"Query '{q}': {len(list(chunks))} results in {elapsed:.2f}ms")

# After: BM25
print("\n--- BM25 Performance ---")
searcher = BM25Searcher()
for q in queries:
    start = time.time()
    results = searcher.search(q, top_k=10)
    elapsed = (time.time() - start) * 1000
    print(f"Query '{q}': {len(results)} results in {elapsed:.2f}ms")


# Expected improvements:
# - Performance: Similar or slightly better (GIN index is efficient)
# - Quality: 30-40% better ranking with term frequency scoring
# - Scoring: Proper [0, 1] range instead of boolean match
"""

import os
import sys
import django

# Django setup for testing outside manage.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from django.apps import apps

def verify_bm25_migration():
    """Verify BM25 migration was applied correctly."""
    DocumentChunk = apps.get_model('documents', 'DocumentChunk')
    
    # Check if search_vector field exists
    if hasattr(DocumentChunk, 'search_vector'):
        print("✓ search_vector field exists")
    else:
        print("✗ search_vector field NOT found - run migration!")
        return False
    
    # Check if GIN index exists
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename='documents_documentchunk' 
            AND indexname LIKE '%search%'
        """)
        indexes = cursor.fetchall()
        if indexes:
            print(f"✓ FTS indexes found: {[idx[0] for idx in indexes]}")
        else:
            print("✗ No FTS indexes found - check migration!")
            return False
    
    # Test basic search
    from backend.services.retrieval.bm25_searcher import BM25Searcher
    searcher = BM25Searcher()
    
    try:
        results = searcher.search("test", top_k=1)
        print(f"✓ BM25 search working: {len(results)} results")
    except Exception as e:
        print(f"✗ BM25 search failed: {e}")
        return False
    
    return True


if __name__ == '__main__':
    verify_bm25_migration()
