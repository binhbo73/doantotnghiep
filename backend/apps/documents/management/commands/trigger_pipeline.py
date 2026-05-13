Ưfrom django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Trigger document ingestion pipeline for a given file path (local to container)'

    def add_arguments(self, parser):
        parser.add_argument('--file-path', required=True, help='Absolute path to file inside container')
        parser.add_argument('--user-id', required=True, help='Uploader user id')
        parser.add_argument('--document-id', required=False, help='Optional existing document id')

    def handle(self, *args, **options):
        file_path = options.get('file_path')
        user_id = options.get('user_id')
        document_id = options.get('document_id')

        from services.pipeline.orchestrator import DocumentIngestPipeline
        import uuid as _uuid

        # If provided user_id is not a UUID, pass None so Document row can be created
        try:
            valid_user_id = str(_uuid.UUID(str(user_id))) if user_id else None
        except Exception:
            valid_user_id = None

        pipeline = DocumentIngestPipeline()
        success, ctx = pipeline.execute(file_path=file_path, user_id=valid_user_id or '', document_id=document_id)

        if success:
            self.stdout.write(self.style.SUCCESS(
                f"Pipeline succeeded: document={ctx.document_id}, chunks={len(ctx.chunks)}"
            ))
        else:
            self.stdout.write(self.style.ERROR(f"Pipeline failed: errors={ctx.errors}"))
            raise SystemExit(2)
