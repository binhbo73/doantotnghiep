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
from core.constants import AccessScope
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class PermissionManagerRepository(BaseRepository):
    """
    Repository for PermissionManager ORM operations
    
    Methods are organized by entity:
    - Document operations
    - Folder operations
    - Role/Permission operations
    - Account operations
    """
    
    # Document Methods
    
    def get_document_by_id(self, document_id: int):
        """Get document by ID with related data"""
        try:
            Document = apps.get_model('documents', 'Document')
            return Document.objects.select_related(
                'uploader', 'department', 'folder'
            ).get(pk=document_id, is_deleted=False)
        except Document.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting document {document_id}: {str(e)}")
            return None
    
    def get_documents_by_uploader(self, uploader_id: int) -> QuerySet:
        """Get all documents uploaded by user"""
        try:
            Document = apps.get_model('documents', 'Document')
            return Document.objects.filter(
                uploader_id=uploader_id, is_deleted=False
            )
        except Exception as e:
            logger.error(f"Error getting documents by uploader {uploader_id}: {str(e)}")
            return Document.objects.none()
    
    def get_documents_with_explicit_permission(
        self, 
        user_id: int,
        access_scopes: List[str] = None
    ) -> QuerySet:
        """Get documents where user has explicit permission"""
        try:
            if access_scopes is None:
                access_scopes = [AccessScope.READ, AccessScope.WRITE, AccessScope.ADMIN]
            
            Document = apps.get_model('documents', 'Document')
            
            return Document.objects.filter(
                is_deleted=False,
                documentpermission__account_id=user_id,
                documentpermission__access_scope__in=access_scopes
            ).distinct()
        except Exception as e:
            logger.error(f"Error getting documents with explicit permission: {str(e)}")
            Document = apps.get_model('documents', 'Document')
            return Document.objects.none()
    
    def get_documents_by_folder_ids(self, folder_ids: List) -> QuerySet:
        """Get documents in specified folders"""
        try:
            if not folder_ids:
                Document = apps.get_model('documents', 'Document')
                return Document.objects.none()
            
            Document = apps.get_model('documents', 'Document')
            return Document.objects.filter(
                folder_id__in=folder_ids, is_deleted=False
            )
        except Exception as e:
            logger.error(f"Error getting documents by folder IDs: {str(e)}")
            Document = apps.get_model('documents', 'Document')
            return Document.objects.none()
    
    # Account Methods
    
    def get_account_by_id(self, account_id: int):
        """Get account by ID"""
        try:
            Account = apps.get_model('users', 'Account')
            return Account.objects.select_related('department').get(
                pk=account_id, is_deleted=False
            )
        except Account.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting account {account_id}: {str(e)}")
            return None
    
    # Folder Methods
    
    def get_folder_by_id(self, folder_id: int):
        """Get folder by ID with department relation"""
        try:
            Folder = apps.get_model('documents', 'Folder')
            return Folder.objects.select_related('department').get(
                pk=folder_id, is_deleted=False
            )
        except Folder.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting folder {folder_id}: {str(e)}")
            return None
    
    def get_accessible_folder_ids(
        self,
        user_id: int,
        access_scopes: List[str] = None
    ) -> List:
        """Get IDs of folders user can access via roles"""
        try:
            if access_scopes is None:
                access_scopes = [AccessScope.READ, AccessScope.WRITE, AccessScope.ADMIN]
            
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            
            return list(
                FolderPermission.objects.filter(
                    role_id__in=self._get_user_role_ids(user_id),
                    is_deleted=False,
                    access_scope__in=access_scopes
                ).values_list('folder_id', flat=True).distinct()
            )
        except Exception as e:
            logger.error(f"Error getting accessible folder IDs: {str(e)}")
            return []
    
    def get_accessible_folders(self, user_id: int) -> QuerySet:
        """Get all folders user can access via roles"""
        try:
            Folder = apps.get_model('documents', 'Folder')
            
            accessible_folder_ids = self.get_accessible_folder_ids(user_id)
            
            if not accessible_folder_ids:
                return Folder.objects.none()
            
            return Folder.objects.filter(
                id__in=accessible_folder_ids, is_deleted=False
            ).distinct()
        except Exception as e:
            logger.error(f"Error getting accessible folders: {str(e)}")
            return Folder.objects.none()
    
    # Permission Methods
    
    def get_document_deny_permission(self, document_id: int, account_id: int):
        """Check if user has DENY permission on document"""
        try:
            DocumentPermission = apps.get_model('documents', 'DocumentPermission')
            
            return DocumentPermission.objects.filter(
                document_id=document_id,
                account_id=account_id,
                access_scope=AccessScope.DENY,
                is_deleted=False
            ).first()
        except Exception as e:
            logger.error(f"Error checking document deny permission: {str(e)}")
            return None
    
    def get_document_allow_permission(self, document_id: int, account_id: int):
        """Get user's explicit permission on document"""
        try:
            DocumentPermission = apps.get_model('documents', 'DocumentPermission')
            
            return DocumentPermission.objects.filter(
                document_id=document_id,
                account_id=account_id,
                access_scope__in=[AccessScope.READ, AccessScope.WRITE, AccessScope.ADMIN],
                is_deleted=False
            ).first()
        except Exception as e:
            logger.error(f"Error getting document allow permission: {str(e)}")
            return None
    
    def get_folder_role_permissions(self, folder_id: int) -> QuerySet:
        """Get all role permissions for folder"""
        try:
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            
            return FolderPermission.objects.filter(
                folder_id=folder_id,
                is_deleted=False
            )
        except Exception as e:
            logger.error(f"Error getting folder permissions: {str(e)}")
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            return FolderPermission.objects.none()
    
    def get_folder_permission_for_role(self, folder_id: int, role_id):
        """Get permission for specific role on folder"""
        try:
            FolderPermission = apps.get_model('documents', 'FolderPermission')
            
            return FolderPermission.objects.filter(
                folder_id=folder_id,
                role_id=role_id,
                is_deleted=False
            ).first()
        except Exception as e:
            logger.error(f"Error getting folder permission for role: {str(e)}")
            return None
    
    # Role Methods
    
    def _get_user_role_ids(self, user_id: int) -> List:
        """Get all role IDs for user"""
        try:
            AccountRole = apps.get_model('users', 'AccountRole')
            
            return list(
                AccountRole.objects.filter(
                    account_id=user_id, is_deleted=False
                ).values_list('role_id', flat=True)
            )
        except Exception as e:
            logger.error(f"Error getting user role IDs: {str(e)}")
            return []
    
    def get_user_role_ids(self, user_id: int) -> List:
        """Get all role IDs for user (public method)"""
        return self._get_user_role_ids(user_id)
    
    def get_user_roles(self, user_id: int) -> QuerySet:
        """Get all Role objects for user"""
        try:
            Role = apps.get_model('users', 'Role')
            AccountRole = apps.get_model('users', 'AccountRole')
            
            role_ids = list(
                AccountRole.objects.filter(
                    account_id=user_id, is_deleted=False
                ).values_list('role_id', flat=True)
            )
            
            if not role_ids:
                return Role.objects.none()
            
            return Role.objects.filter(id__in=role_ids)
        except Exception as e:
            logger.error(f"Error getting user roles: {str(e)}")
            Role = apps.get_model('users', 'Role')
            return Role.objects.none()
    
    def check_user_has_role(self, user_id: int, role_id) -> bool:
        """Check if user has specific role"""
        try:
            AccountRole = apps.get_model('users', 'AccountRole')
            
            return AccountRole.objects.filter(
                account_id=user_id,
                role_id=role_id,
                is_deleted=False
            ).exists()
        except Exception as e:
            logger.error(f"Error checking user role: {str(e)}")
            return False
    
    # Department Methods
    
    def check_department_hierarchy(self, user_dept_id, resource_dept_id) -> bool:
        """Check if user's department can access resource's department (hierarchy)"""
        try:
            if user_dept_id == resource_dept_id:
                return True
            
            Department = apps.get_model('organizations', 'Department')
            
            # Check if resource dept is child of user's dept
            # A user can see own dept + all sub-departments
            resource_dept = Department.objects.get(pk=resource_dept_id)
            
            # Get user's department
            user_dept = Department.objects.get(pk=user_dept_id)
            
            # Check if resource dept starts with user dept path
            # Assuming department has some hierarchy (parent_id or path field)
            if hasattr(resource_dept, 'parent_id'):
                # Check if parent chain includes user's dept
                current = resource_dept
                while current:
                    if current.id == user_dept_id:
                        return True
                    current = current.parent if hasattr(current, 'parent') else None
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking department hierarchy: {str(e)}")
            return False
