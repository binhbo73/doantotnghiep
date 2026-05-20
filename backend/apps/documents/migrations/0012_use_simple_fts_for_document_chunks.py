from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('documents', '0011_ensure_docchunk_search_vec_gin'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
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
            reverse_sql="""
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

            UPDATE document_chunks
            SET search_vector = setweight(
                to_tsvector('english', COALESCE(content, '')), 'A'
            ) ||
            setweight(
                to_tsvector('english', COALESCE(summary, '')), 'B'
            );
            """,
        ),
    ]
