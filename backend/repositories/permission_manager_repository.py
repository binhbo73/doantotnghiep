"""
Permission Manager Repository
===============================
Encapsulates ALL ORM operations used by PermissionManager

This repository handles:
- Document / Account / Role fetching
- DocumentPermission / FolderPermission queries
- AccountRole lookups
- Folder access queries

Purpose:
- Centralize ORM operations for permission checking
- Remove direct ORM calls from PermissionManager (business logic layer)
- Keep PermissionManager clean for ACL logic only

No ORM calls should exist outside this repository for permission checking.
"""

import logging
from typing import List, Optional, Set
from django.db.models import Q, QuerySet
from django.apps import apps
from core.constants import ObjectPermissionLevel
logger = logging.getLogger(__name__)


class PermissionManagerRepository:
    """
    Repository for PermissionManager ORM operations
    
    Methods are organized by entity:
    - Document operations
    - Folder operations
    - Role/Permission operations
    - Account operations
    """
    
    # Document Methods
    
    def get_document_by_id(self, document_id: str):
        """Get document by ID with related data"""
        try:
            Document = apps.get_model('documents', 'Document')
            return Document.objects.select_related(
                'uploader', 'department', 'folder'
            ).get(pk=document_id, is_deleted=False)
        except Exception as e:
            logger.error(f"Error getting document {document_id}: {str(e)}")
            return None
    
    def get_documents_by_uploader(self, account_id: str) -> QuerySet:
        """Get all documents uploaded by account"""
        try:
            Document = apps.get_model('documents', 'Document')
            return Document.objects.filter(
                uploader_id=account_id, is_deleted=False
            )
        except Exception as e:
            logger.error(f"Error getting documents by uploader {account_id}: {str(e)}")
            Document = apps.get_model('documents', 'Document')
            return Document.objects.none()
    
    def get_documents_with_explicit_permission(
        self, 
        account_id: str,
        permission_levels: List[str] = None
    ) -> QuerySet:
        """Get documents where account has explicit permission"""
        try:
            if permission_levels is None:
                permission_levels = [ObjectPermissionLevel.READ, ObjectPermissionLevel.WRITE, ObjectPermissionLevel.DELETE]
            
            Document = apps.get_model('documents', 'Document')
            
            return Document.objects.filter(
                is_deleted=False,
                permissions__subject_id=str(account_id),
                permissions__subject_type='account',
                permissions__permission__in=permission_levels,
                permissions__is_active=True,
                permissions__is_deleted=False
            ).distinct()
        except Exception as e:
            logger.error(f"Error getting documents with explicit permission for {account_id}: {str(e)}")
            Document = apps.get_model('documents', 'Document')
            return Document.objects.none()
    
    def get_documents_by_folder_ids(self, folder_ids: List) -> QuerySet:
        """Get documents in specified folders"""
        try:
            Document = apps.get_model('documents', 'Document')
            if not folder_ids:
                return Document.objects.none()
            
            return Document.objects.filter(
                folder_id__in=folder_ids, is_deleted=False
            )
        except Exception as e:
            logger.error(f"Error getting documents by folder IDs: {str(e)}")
            Document = apps.get_model('documents', 'Document')
            return Document.objects.none()
    
    # Account Methods
    
    def get_account_by_id(self, account_id: str):
        """Get account by ID"""
        try:
            Account = apps.get_model('users', 'Account')
            return Account.objects.select_related('user_profile__department').get(
                pk=account_id, is_deleted=False
            )
        except Exception as e:
            logger.error(f"Error getting account {account_id}: {str(e)}")
            return None
    
    # Folder Methods
    
    def get_folder_by_id(self, folder_id: str):
        """Get folder by ID with department relation"""
        try:
            Folder = apps.get_model('documents', 'Folder')
            return Folder.objects.select_related('department').get(
                pk=folder_id, is_deleted=False
            )
        except Exception as e:
            logger.error(f"Error getting folder {folder_id}: {str(e)}")
            return None
    
    def get_accessible_folder_ids(
        self,
        account_id: str,
        permission_levels: List[str] = None
    ) -> List:
        """Get IDs of folders account can access via roles, direct permission, or access scope."""
        try:
            if permission_levels is None:
                permission_levels = [ObjectPermissionLevel.READ, ObjectPermissionLevel.WRITE, ObjectPermissionLevel.DELETE]
            
            Folder = apps.get_model('documents', 'Folder')
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            Account = apps.get_model('users', 'Account')
            
            # 1. Get user info for scope checks
            user = Account.objects.select_related('user_profile').get(pk=account_id)
            user_dept_id = user.user_profile.department_id if hasattr(user, 'user_profile') else None
            
            # 2. Folders accessible via scope
            scope_query = Folder.objects.filter(
                Q(access_scope='company') |
                Q(access_scope='department', department_id=user_dept_id) |
                Q(access_scope='personal', created_by_id=account_id)
            ).filter(is_deleted=False).values_list('id', flat=True)
            
            # 3. Direct account permissions (ACL)
            account_folders = FolderPermission.objects.filter(
                subject_id=str(account_id),
                subject_type='account',
                permission__in=permission_levels,
                is_active=True,
                is_deleted=False
            ).values_list('folder_id', flat=True)
            
            # 4. Role permissions (ACL)
            role_ids = [str(rid) for rid in self.get_user_role_ids(account_id)]
            role_folders = FolderPermission.objects.filter(
                subject_id__in=role_ids,
                subject_type='role',
                permission__in=permission_levels,
                is_active=True,
                is_deleted=False
            ).values_list('folder_id', flat=True)
            
            return list(set(scope_query) | set(account_folders) | set(role_folders))
        except Exception as e:
            logger.error(f"Error getting accessible folder IDs for {account_id}: {str(e)}")
            return []
    
    def get_accessible_folders(self, account_id: str) -> QuerySet:
        """Get all folders account can access via roles or direct permission"""
        try:
            Folder = apps.get_model('documents', 'Folder')
            accessible_folder_ids = self.get_accessible_folder_ids(account_id)
            
            if not accessible_folder_ids:
                return Folder.objects.none()
            
            return Folder.objects.filter(
                id__in=accessible_folder_ids, is_deleted=False
            ).distinct()
        except Exception as e:
            logger.error(f"Error getting accessible folders for {account_id}: {str(e)}")
            Folder = apps.get_model('documents', 'Folder')
            return Folder.objects.none()
    
    # Permission Methods
    
    def get_document_deny_permission(self, document_id: str, account_id: str):
        """Check if account has DENY permission on document"""
        try:
            DocumentPermission = apps.get_model('documents', 'DocumentPermission')
            
            return DocumentPermission.objects.filter(
                document_id=document_id,
                subject_id=str(account_id),
                subject_type='account',
                permission_precedence='deny',
                is_active=True,
                is_deleted=False
            ).first()
        except Exception as e:
            logger.error(f"Error checking document deny permission: {str(e)}")
            return None
    
    def get_document_allow_permission(self, document_id: str, account_id: str):
        """Get account's explicit permission on document"""
        try:
            DocumentPermission = apps.get_model('documents', 'DocumentPermission')
            
            return DocumentPermission.objects.filter(
                document_id=document_id,
                subject_id=str(account_id),
                subject_type='account',
                permission__in=[ObjectPermissionLevel.READ, ObjectPermissionLevel.WRITE, ObjectPermissionLevel.DELETE],
                permission_precedence='override',
                is_active=True,
                is_deleted=False
            ).first()
        except Exception as e:
            logger.error(f"Error getting document allow permission: {str(e)}")
            return None
    
    def get_folder_role_permissions(self, folder_id: str) -> QuerySet:
        """Get all role permissions for folder"""
        try:
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            
            return FolderPermission.objects.filter(
                folder_id=folder_id,
                subject_type='role',
                is_active=True,
                is_deleted=False
            )
        except Exception as e:
            logger.error(f"Error getting folder permissions: {str(e)}")
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            return FolderPermission.objects.none()
    
    def get_folder_permission_for_subject(self, folder_id: str, subject_type: str, subject_id: str):
        """Get permission for a specific subject on folder."""
        try:
            FolderPermission = apps.get_model('documents', 'FolderPermission')

            return FolderPermission.objects.filter(
                folder_id=folder_id,
                subject_type=subject_type,
                subject_id=str(subject_id),
                is_active=True,
                is_deleted=False,
            ).first()
        except Exception as e:
            logger.error(f"Error getting folder permission for subject: {str(e)}")
            return None

    def get_folder_permissions_for_subject_ids(self, folder_id: str, subject_type: str, subject_ids: List[str]) -> QuerySet:
        """Get all active permissions for a folder for a set of subject IDs."""
        try:
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            if not subject_ids:
                return FolderPermission.objects.none()

            return FolderPermission.objects.filter(
                folder_id=folder_id,
                subject_type=subject_type,
                subject_id__in=[str(sid) for sid in subject_ids],
                is_active=True,
                is_deleted=False,
            )
        except Exception as e:
            logger.error(f"Error getting folder permissions for subjects: {str(e)}")
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            return FolderPermission.objects.none()
    
    # Role Methods
    
    def get_user_role_ids(self, account_id: str) -> List:
        """Get all role IDs for account"""
        try:
            AccountRole = apps.get_model('users', 'AccountRole')
            
            return list(
                AccountRole.objects.filter(
                    account_id=account_id, is_deleted=False
                ).values_list('role_id', flat=True)
            )
        except Exception as e:
            logger.error(f"Error getting user role IDs: {str(e)}")
            return []
    
    def get_user_roles(self, account_id: str) -> QuerySet:
        """Get all Role objects for account"""
        try:
            Role = apps.get_model('users', 'Role')
            AccountRole = apps.get_model('users', 'AccountRole')
            
            role_ids = self.get_user_role_ids(account_id)
            
            if not role_ids:
                return Role.objects.none()
            
            return Role.objects.filter(id__in=role_ids, is_deleted=False)
        except Exception as e:
            logger.error(f"Error getting user roles: {str(e)}")
            Role = apps.get_model('users', 'Role')
            return Role.objects.none()
    
    def check_user_has_role(self, account_id: str, role_id: str) -> bool:
        """Check if account has specific role"""
        try:
            AccountRole = apps.get_model('users', 'AccountRole')
            
            return AccountRole.objects.filter(
                account_id=account_id,
                role_id=role_id,
                is_deleted=False
            ).exists()
        except Exception as e:
            logger.error(f"Error checking user role: {str(e)}")
            return False
    
    # Department Methods
    
    def check_department_hierarchy(self, user_dept_id, resource_dept_id) -> bool:
        """
        Check if user's department can access resource's department (hierarchy)
        DEPRECATED: Use PermissionManager._check_department_hierarchy instead.
        """
        try:
            if user_dept_id == resource_dept_id:
                return True
            
            Department = apps.get_model('users', 'Department')
            
            resource_dept = Department.objects.get(pk=resource_dept_id)
            user_dept = Department.objects.get(pk=user_dept_id)
            
            current = resource_dept
            while current:
                if current.id == user_dept_id:
                    return True
                current = current.parent if hasattr(current, 'parent') else None
            
            return False
        except Exception as e:
            logger.error(f"Error checking department hierarchy: {str(e)}")
            return False
