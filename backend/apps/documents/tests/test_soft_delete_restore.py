from unittest.mock import Mock, patch

from django.test import TestCase

from apps.documents.models import (
    Document,
    DocumentChunk,
    DocumentEmbedding,
    Folder,
    FolderDeletionOperation,
)
from apps.users.models import Account
from services.document_service import DocumentService
from services.folder_service import FolderService


class DocumentSoftDeleteRestoreTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create_user(
            username='soft-delete-owner',
            email='soft-delete-owner@example.com',
            password='pass',
        )

    def create_document(self, name, folder=None):
        document = Document.objects.create(
            filename=name,
            original_name=name,
            storage_path=f'/retained/{name}',
            file_type='pdf',
            uploader=self.account,
            folder=folder,
        )
        chunk = DocumentChunk.objects.create(
            document=document,
            content=f'content for {name}',
            chunk_index=0,
            vector_id=f'vector-{document.id}',
        )
        embedding = DocumentEmbedding.objects.create(
            chunk=chunk,
            qdrant_vector_id=f'qdrant-{document.id}',
        )
        return document, chunk, embedding

    def test_folder_delete_and_restore_tracks_exact_subtree(self):
        root = Folder.objects.create(
            name='Root',
            created_by=self.account,
            access_scope='personal',
        )
        child = Folder.objects.create(
            name='Child',
            parent=root,
            created_by=self.account,
            access_scope='personal',
        )
        root_document, root_chunk, root_embedding = self.create_document(
            'root.pdf',
            root,
        )
        child_document, _, _ = self.create_document('child.pdf', child)
        previously_deleted, _, _ = self.create_document('old.pdf', root)
        previously_deleted.delete()

        result = FolderService().delete_folder_recursive(
            folder_id=str(root.id),
            user_id=str(self.account.id),
        )

        self.assertEqual(result['folders_deleted'], 2)
        self.assertEqual(result['documents_deleted'], 2)
        self.assertEqual(result['external_files_deleted'], 0)
        self.assertEqual(result['vectors_deleted'], 0)
        self.assertFalse(Folder.objects.filter(id__in=[root.id, child.id]).exists())
        self.assertFalse(
            Document.objects.filter(
                id__in=[root_document.id, child_document.id],
            ).exists()
        )

        deleted_document = Document.objects.all_records().get(id=root_document.id)
        deleted_chunk = DocumentChunk.objects.all_records().get(id=root_chunk.id)
        deleted_embedding = DocumentEmbedding.objects.all_records().get(
            id=root_embedding.id,
        )
        self.assertEqual(deleted_document.storage_path, '/retained/root.pdf')
        self.assertEqual(deleted_chunk.vector_id, f'vector-{root_document.id}')
        self.assertEqual(
            deleted_embedding.qdrant_vector_id,
            f'qdrant-{root_document.id}',
        )

        restore_result = FolderService().restore_deleted_folder(str(root.id))

        self.assertEqual(restore_result['folders_restored'], 2)
        self.assertEqual(restore_result['documents_restored'], 2)
        self.assertEqual(Folder.objects.filter(id__in=[root.id, child.id]).count(), 2)
        self.assertEqual(
            Document.objects.filter(
                id__in=[root_document.id, child_document.id],
            ).count(),
            2,
        )
        self.assertFalse(Document.objects.filter(id=previously_deleted.id).exists())
        self.assertEqual(
            FolderDeletionOperation.objects.get(id=result['operation_id']).status,
            FolderDeletionOperation.STATUS_RESTORED,
        )

    @patch('services.ai.qdrant_client.QdrantClient')
    @patch('core.permissions.get_permission_manager')
    def test_document_service_delete_retains_qdrant_data(
        self,
        get_permission_manager,
        qdrant_client,
    ):
        permission_manager = Mock()
        permission_manager.check_document_access.return_value = True
        get_permission_manager.return_value = permission_manager
        document, chunk, embedding = self.create_document('single.pdf')

        self.assertTrue(
            DocumentService().delete_document(
                document_id=str(document.id),
                user_id=str(self.account.id),
            )
        )

        qdrant_client.assert_not_called()
        deleted_document = Document.objects.all_records().get(id=document.id)
        self.assertTrue(deleted_document.is_deleted)
        self.assertEqual(deleted_document.storage_path, '/retained/single.pdf')
        self.assertEqual(
            DocumentChunk.objects.all_records().get(id=chunk.id).vector_id,
            f'vector-{document.id}',
        )
        self.assertEqual(
            DocumentEmbedding.objects.all_records()
            .get(id=embedding.id)
            .qdrant_vector_id,
            f'qdrant-{document.id}',
        )

        deleted_document.restore()

        self.assertTrue(Document.objects.filter(id=document.id).exists())
        self.assertTrue(DocumentChunk.objects.filter(id=chunk.id).exists())
        self.assertTrue(DocumentEmbedding.objects.filter(id=embedding.id).exists())
