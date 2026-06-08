from django.core.management.base import BaseCommand

from apps.documents.models import Document
from services.ai.qdrant_client import QdrantClient
from services.document_version_service import DocumentVersionService


class Command(BaseCommand):
    help = "Backfill document version fields into existing Qdrant point payloads."

    def handle(self, *args, **options):
        qdrant = QdrantClient()
        updated = 0
        failed = 0

        documents = Document.objects.all().only(
            'id',
            'logical_document_id',
            'version',
            'is_current',
        ).iterator(chunk_size=200)
        for document in documents:
            ok = qdrant.set_payload_by_filter(
                {'document_id': str(document.id)},
                {
                    'logical_document_id': str(document.logical_document_id),
                    'version_number': document.version,
                    'is_current': document.is_current,
                },
            )
            if ok:
                updated += 1
            else:
                failed += 1

        document_ids = list(
            Document.objects.filter(is_deleted=False).values_list('id', flat=True)
        )
        DocumentVersionService._sync_chunk_lineage_payloads(
            qdrant,
            [str(document_id) for document_id in document_ids],
        )

        self.stdout.write(self.style.SUCCESS(
            f"Qdrant version payload backfill complete: updated={updated}, failed={failed}"
        ))
