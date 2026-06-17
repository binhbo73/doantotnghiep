from django.test import TestCase

from api.serializers.department_serializers import DepartmentDetailSerializer
from apps.documents.models import (
    Document,
    DocumentChunk,
    Folder,
    FolderPermission,
)
from apps.users.models import (
    Account,
    AccountRole,
    Department,
    DepartmentDeletionOperation,
    Role,
    UserProfile,
)
from services.department_service import DepartmentService


class DepartmentCascadeDeleteTests(TestCase):
    def create_account(self, username, department=None):
        account = Account.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='pass',
        )
        profile = UserProfile.objects.create(
            account=account,
            full_name=username,
            department=department,
        )
        return account, profile

    def create_document(self, name, uploader, department=None, folder=None):
        document = Document.objects.create(
            filename=name,
            original_name=name,
            storage_path=f'/tmp/{name}',
            file_type='pdf',
            uploader=uploader,
            department=department,
            folder=folder,
            access_scope='department',
        )
        DocumentChunk.objects.create(
            document=document,
            content=f'content for {name}',
            chunk_index=0,
        )
        return document

    def test_delete_and_restore_department_subtree_without_deleting_accounts(self):
        root = Department.objects.create(name='Engineering')
        child = Department.objects.create(name='Platform', parent=root)
        destination = Department.objects.create(name='Operations')

        manager, manager_profile = self.create_account('manager', root)
        employee, employee_profile = self.create_account('employee', child)
        root.manager = manager
        root.save(update_fields=['manager', 'updated_at'])
        root.managers.add(manager)

        manager_role = Role.objects.create(code='manager_test', name='Manager Test')
        manager_assignment = AccountRole.objects.create(
            account=manager,
            role=manager_role,
        )

        root_folder = Folder.objects.create(
            name='Root folder',
            department=root,
            created_by=manager,
            access_scope='department',
        )
        child_folder = Folder.objects.create(
            name='Child folder',
            parent=root_folder,
            department=child,
            created_by=manager,
            access_scope='department',
        )
        folder_permission = FolderPermission.objects.create(
            folder=root_folder,
            subject_type='account',
            subject_id=str(employee.id),
            permission='read',
        )
        root_document = self.create_document(
            'root.pdf',
            manager,
            department=root,
            folder=root_folder,
        )
        child_document = self.create_document(
            'child.pdf',
            employee,
            department=child,
            folder=child_folder,
        )
        previously_deleted_document = self.create_document(
            'already-deleted.pdf',
            manager,
            department=root,
        )
        previously_deleted_document.delete()

        result = DepartmentService().delete_department(str(root.id))

        self.assertEqual(result['departments_deleted'], 2)
        self.assertEqual(result['folders_deleted'], 2)
        self.assertEqual(result['documents_deleted'], 2)
        self.assertEqual(result['users_detached'], 2)
        self.assertEqual(result['accounts_deleted'], 0)
        self.assertEqual(result['roles_deleted'], 0)

        self.assertFalse(Department.objects.filter(id__in=[root.id, child.id]).exists())
        self.assertFalse(Folder.objects.filter(id__in=[root_folder.id, child_folder.id]).exists())
        self.assertFalse(Document.objects.filter(id__in=[root_document.id, child_document.id]).exists())

        manager.refresh_from_db()
        employee.refresh_from_db()
        manager_profile.refresh_from_db()
        employee_profile.refresh_from_db()
        manager_assignment.refresh_from_db()
        self.assertFalse(manager.is_deleted)
        self.assertFalse(employee.is_deleted)
        self.assertFalse(manager_assignment.is_deleted)
        self.assertIsNone(manager_profile.department_id)
        self.assertIsNone(employee_profile.department_id)
        self.assertTrue(
            DepartmentDeletionOperation.objects.filter(
                id=result['operation_id'],
                status=DepartmentDeletionOperation.STATUS_DELETED,
            ).exists()
        )

        # A newer reassignment must win over rollback.
        manager_profile.department = destination
        manager_profile.save(update_fields=['department', 'updated_at'])

        restore_result = DepartmentService().restore_deleted_department(str(root.id))

        self.assertEqual(restore_result['departments_restored'], 2)
        self.assertEqual(restore_result['documents_restored'], 2)
        manager_profile.refresh_from_db()
        employee_profile.refresh_from_db()
        self.assertEqual(manager_profile.department_id, destination.id)
        self.assertEqual(employee_profile.department_id, child.id)

        self.assertEqual(Department.objects.filter(id__in=[root.id, child.id]).count(), 2)
        self.assertEqual(Folder.objects.filter(id__in=[root_folder.id, child_folder.id]).count(), 2)
        self.assertEqual(Document.objects.filter(id__in=[root_document.id, child_document.id]).count(), 2)
        self.assertFalse(
            Document.objects.filter(id=previously_deleted_document.id).exists()
        )
        self.assertFalse(
            FolderPermission.objects.all_records().get(id=folder_permission.id).is_deleted
        )
        self.assertEqual(
            DepartmentDeletionOperation.objects.get(id=result['operation_id']).status,
            DepartmentDeletionOperation.STATUS_RESTORED,
        )

    def test_deleted_account_is_hidden_as_department_manager_and_restores(self):
        department = Department.objects.create(name='Finance')
        manager, _ = self.create_account('finance-manager', department)
        department.manager = manager
        department.save(update_fields=['manager', 'updated_at'])
        department.managers.add(manager)

        manager.delete()
        department = Department.objects.all_records().get(id=department.id)
        deleted_data = DepartmentDetailSerializer(department).data

        self.assertIsNone(deleted_data['manager'])
        self.assertEqual(deleted_data['manager_ids'], [])

        Account.objects.all_records().get(id=manager.id).restore()
        department = Department.objects.get(id=department.id)
        restored_data = DepartmentDetailSerializer(department).data

        self.assertEqual(restored_data['manager']['id'], str(manager.id))
        self.assertIn(str(manager.id), restored_data['manager_ids'])
