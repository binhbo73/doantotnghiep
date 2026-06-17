from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.documents.models import (
    Document,
    DocumentAsset,
    DocumentChunk,
    DocumentEmbedding,
    DocumentPermission,
)
from apps.operations.models import AsyncTask, Conversation, Message, UserDocumentCache
from apps.users.models import (
    Account,
    AccountRole,
    Department,
    PasswordResetToken,
    Permission,
    Role,
    RolePermission,
    UserProfile,
)


class SoftDeleteBehaviorTests(TestCase):
    def create_account(self, username="user"):
        return Account.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="pass",
        )

    def test_queryset_delete_soft_deletes_base_models(self):
        department = Department.objects.create(name="Soft Delete Department")

        deleted_count, _ = Department.objects.filter(id=department.id).delete()

        self.assertEqual(deleted_count, 1)
        self.assertFalse(Department.objects.filter(id=department.id).exists())
        deleted_department = Department.objects.all_records().get(id=department.id)
        self.assertTrue(deleted_department.is_deleted)
        self.assertIsNotNone(deleted_department.deleted_at)

    def test_account_delete_soft_deletes_cascade_relations(self):
        account = self.create_account("account_soft_delete")
        UserProfile.objects.create(account=account, full_name="Soft Delete User")
        PasswordResetToken.objects.create(
            account=account,
            token="reset-token",
            expires_at=timezone.now() + timedelta(hours=1),
        )
        conversation = Conversation.objects.create(account=account, title="Chat")
        Message.objects.create(conversation=conversation, role="user", content="hello")

        account.delete()

        deleted_account = Account.objects.all_records().get(id=account.id)
        self.assertTrue(deleted_account.is_deleted)
        self.assertTrue(UserProfile.objects.all_records().get(account=account).is_deleted)
        self.assertTrue(PasswordResetToken.objects.all_records().get(account=account).is_deleted)
        self.assertTrue(Conversation.objects.all_records().get(id=conversation.id).is_deleted)
        self.assertTrue(Message.objects.all_records().get(conversation=conversation).is_deleted)

        deleted_account.restore()

        self.assertFalse(Account.objects.all_records().get(id=account.id).is_deleted)
        self.assertFalse(UserProfile.objects.all_records().get(account=account).is_deleted)
        self.assertFalse(PasswordResetToken.objects.all_records().get(account=account).is_deleted)
        self.assertFalse(Conversation.objects.all_records().get(id=conversation.id).is_deleted)
        self.assertFalse(Message.objects.all_records().get(conversation=conversation).is_deleted)

    def test_role_delete_soft_deletes_role_mappings(self):
        account = self.create_account("role_soft_delete")
        role = Role.objects.create(code="custom_role", name="Custom Role")
        permission = Permission.objects.create(
            code="custom_permission",
            name="Custom Permission",
            resource="document",
            action="read",
        )
        account_role = AccountRole.objects.create(account=account, role=role)
        role_permission = RolePermission.objects.create(role=role, permission=permission)

        role.delete()

        self.assertTrue(Role.objects.all_records().get(id=role.id).is_deleted)
        self.assertTrue(AccountRole.objects.all_records().get(id=account_role.id).is_deleted)
        self.assertTrue(RolePermission.objects.all_records().get(id=role_permission.id).is_deleted)

        Role.objects.all_records().get(id=role.id).restore()

        self.assertFalse(Role.objects.all_records().get(id=role.id).is_deleted)
        self.assertFalse(AccountRole.objects.all_records().get(id=account_role.id).is_deleted)
        self.assertFalse(RolePermission.objects.all_records().get(id=role_permission.id).is_deleted)

    def test_document_delete_soft_deletes_document_dependents(self):
        account = self.create_account("document_soft_delete")
        document = Document.objects.create(
            filename="stored.pdf",
            original_name="Original.pdf",
            storage_path="/tmp/stored.pdf",
            file_type="pdf",
            uploader=account,
        )
        chunk = DocumentChunk.objects.create(
            document=document,
            content="content",
            page_number=1,
            chunk_index=0,
        )
        embedding = DocumentEmbedding.objects.create(
            chunk=chunk,
            embedding_model="test-embedding",
            qdrant_vector_id="vector-1",
        )
        asset = DocumentAsset.objects.create(
            document=document,
            chunk=chunk,
            asset_type="pdf_embedded",
            image_path="/tmp/image.png",
        )
        permission = DocumentPermission.objects.create(
            document=document,
            subject_type="account",
            subject_id=str(account.id),
            permission="read",
        )
        cache = UserDocumentCache.objects.create(
            account=account,
            document=document,
            max_permission="read",
            expires_at=timezone.now() + timedelta(hours=1),
        )
        task = AsyncTask.objects.create(
            task_type="INDEX_DOCUMENT",
            document=document,
            payload={},
        )

        document.delete()

        self.assertTrue(Document.objects.all_records().get(id=document.id).is_deleted)
        self.assertTrue(DocumentChunk.objects.all_records().get(id=chunk.id).is_deleted)
        self.assertTrue(DocumentEmbedding.objects.all_records().get(id=embedding.id).is_deleted)
        self.assertTrue(DocumentAsset.objects.all_records().get(id=asset.id).is_deleted)
        self.assertTrue(DocumentPermission.objects.all_records().get(id=permission.id).is_deleted)
        self.assertTrue(UserDocumentCache.objects.all_records().get(id=cache.id).is_deleted)
        self.assertTrue(AsyncTask.objects.all_records().get(id=task.id).is_deleted)

        Document.objects.all_records().get(id=document.id).restore()

        self.assertFalse(Document.objects.all_records().get(id=document.id).is_deleted)
        self.assertFalse(DocumentChunk.objects.all_records().get(id=chunk.id).is_deleted)
        self.assertFalse(DocumentEmbedding.objects.all_records().get(id=embedding.id).is_deleted)
        self.assertFalse(DocumentAsset.objects.all_records().get(id=asset.id).is_deleted)
        self.assertFalse(DocumentPermission.objects.all_records().get(id=permission.id).is_deleted)
        self.assertFalse(UserDocumentCache.objects.all_records().get(id=cache.id).is_deleted)
        self.assertFalse(AsyncTask.objects.all_records().get(id=task.id).is_deleted)
