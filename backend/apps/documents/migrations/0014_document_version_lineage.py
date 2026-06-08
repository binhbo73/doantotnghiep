import uuid

from django.db import migrations, models
import django.db.models.deletion


def backfill_version_lineage(apps, schema_editor):
    Document = apps.get_model('documents', 'Document')
    DocumentChunk = apps.get_model('documents', 'DocumentChunk')

    for document in Document.objects.all().only('id'):
        Document.objects.filter(pk=document.pk).update(
            logical_document_id=document.pk,
            is_current=not document.is_deleted,
            version_state='active' if not document.is_deleted else 'superseded',
            valid_from=document.created_at,
        )

    for chunk in DocumentChunk.objects.all().only('id', 'document_id'):
        document = Document.objects.filter(pk=chunk.document_id).only('is_current').first()
        DocumentChunk.objects.filter(pk=chunk.pk).update(
            lineage_id=chunk.pk,
            is_current=bool(document and document.is_current and not chunk.is_deleted),
            change_type='original',
        )


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0013_add_unaccent_to_document_chunk_fts'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='change_summary',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='document',
            name='is_current',
            field=models.BooleanField(db_index=True, default=True, help_text='Whether this is the effective version used by default retrieval'),
        ),
        migrations.AddField(
            model_name='document',
            name='logical_document_id',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, help_text='Stable identity shared by all versions of the same document'),
        ),
        migrations.AddField(
            model_name='document',
            name='previous_version',
            field=models.ForeignKey(blank=True, help_text='Immediately preceding document version', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='next_versions', to='documents.document'),
        ),
        migrations.AddField(
            model_name='document',
            name='valid_from',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='document',
            name='valid_to',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='document',
            name='version_state',
            field=models.CharField(choices=[('staging', 'Staging'), ('active', 'Active'), ('superseded', 'Superseded'), ('failed', 'Failed')], default='active', help_text='Lifecycle state of this document version', max_length=20),
        ),
        migrations.AddField(
            model_name='documentchunk',
            name='change_type',
            field=models.CharField(choices=[('original', 'Original'), ('unchanged', 'Unchanged'), ('modified', 'Modified'), ('added', 'Added'), ('removed', 'Removed')], default='original', help_text='How this chunk differs from its previous version', max_length=20),
        ),
        migrations.AddField(
            model_name='documentchunk',
            name='is_current',
            field=models.BooleanField(db_index=True, default=True, help_text='Whether the chunk belongs to the effective document version'),
        ),
        migrations.AddField(
            model_name='documentchunk',
            name='lineage_id',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, help_text='Stable logical identity for a chunk across document versions'),
        ),
        migrations.AddField(
            model_name='documentchunk',
            name='previous_version_chunk',
            field=models.ForeignKey(blank=True, help_text='Best matching chunk in the previous document version', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='next_version_chunks', to='documents.documentchunk'),
        ),
        migrations.CreateModel(
            name='ChunkRevisionLink',
            fields=[
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='Soft delete flag - True = deleted, False = active')),
                ('deleted_at', models.DateTimeField(blank=True, help_text='Deletion timestamp (null = not deleted)', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Creation timestamp (auto-filled)')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Last update timestamp (auto-updated)')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('relation', models.CharField(choices=[('replaces', 'Replaces'), ('unchanged', 'Unchanged'), ('splits', 'Splits'), ('merges', 'Merges'), ('references', 'References')], default='replaces', max_length=20)),
                ('confidence', models.FloatField(default=1.0)),
                ('match_method', models.CharField(default='deterministic', max_length=50)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('from_chunk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='revision_links_from', to='documents.documentchunk')),
                ('to_chunk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='revision_links_to', to='documents.documentchunk')),
            ],
            options={
                'db_table': 'chunk_revision_links',
            },
        ),
        migrations.RunPython(backfill_version_lineage, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['logical_document_id', '-version'], name='documents_logical_d6949b_idx'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['is_current', 'status', 'is_deleted'], name='documents_is_curr_8cb26e_idx'),
        ),
        migrations.AddConstraint(
            model_name='document',
            constraint=models.UniqueConstraint(condition=models.Q(('is_current', True), ('is_deleted', False)), fields=('logical_document_id',), name='uniq_current_document_version'),
        ),
        migrations.AddIndex(
            model_name='documentchunk',
            index=models.Index(fields=['previous_version_chunk_id'], name='idx_chunk_prev_version'),
        ),
        migrations.AddIndex(
            model_name='documentchunk',
            index=models.Index(fields=['lineage_id', 'is_current'], name='idx_chunk_lineage_current'),
        ),
        migrations.AddIndex(
            model_name='chunkrevisionlink',
            index=models.Index(fields=['from_chunk_id'], name='chunk_revis_from_ch_9b19bb_idx'),
        ),
        migrations.AddIndex(
            model_name='chunkrevisionlink',
            index=models.Index(fields=['to_chunk_id'], name='chunk_revis_to_chun_54dce7_idx'),
        ),
        migrations.AddIndex(
            model_name='chunkrevisionlink',
            index=models.Index(fields=['relation'], name='chunk_revis_relatio_bc696a_idx'),
        ),
        migrations.AddConstraint(
            model_name='chunkrevisionlink',
            constraint=models.UniqueConstraint(fields=('from_chunk', 'to_chunk', 'relation'), name='uniq_chunk_revision_relation'),
        ),
    ]
