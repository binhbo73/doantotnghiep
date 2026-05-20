from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('documents', '0012_use_simple_fts_for_document_chunks'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE EXTENSION IF NOT EXISTS unaccent;

            CREATE OR REPLACE FUNCTION update_documentchunk_search_vector() RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector := setweight(
                    to_tsvector('simple', COALESCE(NEW.content, '')), 'A'
                ) ||
                setweight(
                    to_tsvector('simple', unaccent(COALESCE(NEW.content, ''))), 'A'
                ) ||
                setweight(
                    to_tsvector('simple', COALESCE(NEW.summary, '')), 'B'
                ) ||
                setweight(
                    to_tsvector('simple', unaccent(COALESCE(NEW.summary, ''))), 'B'
                );
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            UPDATE document_chunks
            SET search_vector = setweight(
                to_tsvector('simple', COALESCE(content, '')), 'A'
            ) ||
            setweight(
                to_tsvector('simple', unaccent(COALESCE(content, ''))), 'A'
            ) ||
            setweight(
                to_tsvector('simple', COALESCE(summary, '')), 'B'
            ) ||
            setweight(
                to_tsvector('simple', unaccent(COALESCE(summary, ''))), 'B'
            );
            """,
            reverse_sql="""
            CREATE OR REPLACE FUNCTION update_documentchunk_search_vector() RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector := setweight(
                    to_tsvector('simple', COALESCE(NEW.content, '')), 'A'
                ) ||
                setweight(
                    to_tsvector('simple', COALESCE(NEW.summary, '')), 'B'
                );
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            UPDATE document_chunks
            SET search_vector = setweight(
                to_tsvector('simple', COALESCE(content, '')), 'A'
            ) ||
            setweight(
                to_tsvector('simple', COALESCE(summary, '')), 'B'
            );
            """,
        ),
    ]
