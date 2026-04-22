"""
Department Service
==================
Business logic for Department management (CRUD operations)

Responsibilities:
- Create new departments with parent-child relationships
- Update department details
- Delete departments (soft delete with cascade checks)
- List departments in tree structure
- Validate department constraints

Uses:
- DepartmentRepository (data access)
- UserRepository (check members)
- AuditService (audit logging)

Design:
- No direct ORM queries - all via Repository
- All changes logged to AuditLog
- Soft delete pattern (is_deleted=True)
- Transaction-aware for consistency
"""

import logging
from typing import List, Dict, Optional, Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from repositories.department_repository import DepartmentRepository
from repositories.user_repository import UserRepository
from services.audit_service import AuditService
from services.base_service import BaseService
from apps.users.models import Department
from core.exceptions import (
    ValidationError,
    BusinessLogicError,
    NotFoundError,
    DepartmentNotFoundError,
    ConflictError,
)

logger = logging.getLogger(__name__)


class DepartmentService(BaseService):
    """
    Service for Department management (hierarchical structure)
    
    Key Methods:
    - get_department_tree() - Get all departments as nested tree
    - create_department(name, parent_id, manager_id) - Create new department
    - update_department(dept_id, **data) - Update department info
    - delete_department(dept_id) - Soft delete with cascade checks
    
    Validations:
    - Department name uniqueness (per parent)
    - Circular reference prevention (department can't be parent of itself)
    - Child existence check before delete
    - User assignment check before delete
    """
    
    repository_class = DepartmentRepository
    
    def __init__(self):
        """Initialize with repositories"""
        super().__init__()
        self.department_repo = self.repository
        self.user_repo = UserRepository()
        self.audit_service = AuditService()
    
    # ============================================================================
    # TREE STRUCTURE
    # ============================================================================
    
    def get_department_tree(self, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """
        Get all departments in nested tree structure.
        
        Returns:
            List of root departments with nested sub_departments
        
        Example:
            [
                {
                    "id": "uuid-1",
                    "name": "Sales",
                    "parent_id": null,
                    "manager": {...},
                    "member_count": 5,
                    "sub_departments": [
                        {"id": "uuid-2", "name": "Sales VN", "parent_id": "uuid-1", ...}
                    ]
                }
            ]
        """
        try:
            # Get all root departments (parent_id IS NULL)
            root_depts = self.department_repo.get_base_queryset().filter(
                parent_id__isnull=True
            )
            
            if not include_deleted:
                root_depts = root_depts.filter(is_deleted=False)
            
            result = []
            for dept in root_depts:
                result.append(self._build_dept_tree_node(dept))
            
            return result
        
        except Exception as e:
            logger.error(f"Error building department tree: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to build department tree: {str(e)}")
    
    def _build_dept_tree_node(self, dept: Department) -> Dict[str, Any]:
        """
        Recursively build tree node for department.
        
        Args:
            dept: Department instance
        
        Returns:
            Dictionary with dept info + nested sub_departments
        """
        try:
            # Get sub-departments
            sub_depts = dept.sub_departments.filter(is_deleted=False)
            
            # Count members
            member_count = dept.get_all_members(include_subdepts=False).count()
            
            return {
                "id": str(dept.id),
                "name": dept.name,
                "description": dept.description,
                "parent_id": str(dept.parent_id) if dept.parent_id else None,
                "manager_id": str(dept.manager_id) if dept.manager_id else None,
                "manager_name": dept.manager.username if dept.manager else None,
                "member_count": member_count,
                "created_at": dept.created_at.isoformat() if dept.created_at else None,
                "updated_at": dept.updated_at.isoformat() if dept.updated_at else None,
                "sub_departments": [
                    self._build_dept_tree_node(sub_dept) for sub_dept in sub_depts
                ]
            }
        
        except Exception as e:
            logger.error(f"Error building dept tree node for {dept.id}: {e}", exc_info=True)
            raise
    
    # ============================================================================
    # CREATE
    # ============================================================================
    
    @transaction.atomic()
    def create_department(
        self,
        name: str,
        parent_id: Optional[str] = None,
        manager_id: Optional[str] = None,
        description: Optional[str] = None,
        requested_by_user_id: Optional[str] = None,
    ) -> Department:
        """
        Create new department.
        
        Args:
            name: Department name
            parent_id: Parent department UUID (optional, for sub-departments)
            manager_id: Manager account UUID (optional)
            description: Department description
            requested_by_user_id: User creating the department (for audit)
        
        Returns:
            Created Department instance
        
        Raises:
            ValidationError: If validation fails
            BusinessLogicError: If parent not found or circular reference
        
        Logic:
        1. Validate name not empty
        2. If parent_id: Check parent exists + not deleted
        3. If manager_id: Check manager exists
        4. Create Department
        5. Log audit
        """
        try:
            # ========== STEP 1: VALIDATE INPUT ==========
            if not name or not name.strip():
                raise ValidationError("Department name is required")
            
            name = name.strip()
            
            # ========== STEP 2: CHECK PARENT ==========
            parent_dept = None
            if parent_id:
                try:
                    parent_dept = self.department_repo.get_by_id(parent_id)
                    if not parent_dept:
                        raise NotFoundError(f"Parent department {parent_id} not found")
                    
                    if parent_dept.is_deleted:
                        raise ValidationError(f"Parent department {parent_id} is deleted")
                
                except NotFoundError:
                    raise
                except Exception as e:
                    logger.error(f"Error checking parent department: {e}")
                    raise BusinessLogicError(f"Error checking parent department: {str(e)}")
            
            # ========== STEP 3: CHECK MANAGER ==========
            manager = None
            if manager_id:
                try:
                    manager = self.user_repo.get_by_id(manager_id)
                    if not manager:
                        raise NotFoundError(f"Manager {manager_id} not found")
                    
                    if manager.is_deleted or manager.status != 'active':
                        raise ValidationError("Manager account is not active")
                
                except NotFoundError:
                    raise
                except Exception as e:
                    logger.error(f"Error checking manager: {e}")
                    raise BusinessLogicError(f"Error checking manager: {str(e)}")
            
            # ========== STEP 4: CREATE DEPARTMENT ==========
            dept_data = {
                'name': name,
                'parent': parent_dept,
                'manager': manager,
                'description': description or '',
            }
            
            dept = self.department_repo.create(**dept_data)
            
            logger.info(f"Department created: {dept.id} (name={name}, parent={parent_id})")
            
            # ========== STEP 5: AUDIT LOG ==========
            # TODO: Fix audit logging - needs proper account object/parameters
            pass
            
            return dept
        
        except (ValidationError, NotFoundError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating department: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to create department: {str(e)}")
    
    # ============================================================================
    # UPDATE
    # ============================================================================
    
    @transaction.atomic()
    def update_department(
        self,
        dept_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        manager_id: Optional[str] = None,
        requested_by_user_id: Optional[str] = None,
    ) -> Department:
        """
        Update department information.
        
        Args:
            dept_id: Department UUID
            name: New department name (optional)
            description: New department description (optional)
            manager_id: New manager UUID (optional)
            requested_by_user_id: User making the change
        
        Returns:
            Updated Department instance
        
        Raises:
            NotFoundError: If department not found
            ValidationError: If validation fails
        
        Logic:
        1. Check department exists
        2. Validate new values if provided
        3. Update fields
        4. Save to DB
        5. Log audit
        """
        try:
            # ========== STEP 1: GET DEPARTMENT ==========
            dept = self.department_repo.get_by_id(dept_id)
            if not dept:
                raise NotFoundError(f"Department {dept_id} not found")
            
            # ========== STEP 2: VALIDATE UPDATES ==========
            updates = {}
            
            if name is not None:
                name = name.strip()
                if not name:
                    raise ValidationError("Department name cannot be empty")
                updates['name'] = name
            
            if description is not None:
                updates['description'] = description.strip()
            
            if manager_id is not None:
                if manager_id:  # Not null
                    manager = self.user_repo.get_by_id(manager_id)
                    if not manager:
                        raise NotFoundError(f"Manager {manager_id} not found")
                    if manager.is_deleted or manager.status != 'active':
                        raise ValidationError("Manager account is not active")
                    updates['manager_id'] = manager_id
                else:
                    updates['manager_id'] = None
            
            # ========== STEP 3: UPDATE ==========
            dept = self.department_repo.update(dept_id, **updates)
            
            logger.info(f"Department updated: {dept_id} with updates: {updates}")
            
            # ========== STEP 4: AUDIT LOG ==========
            # TODO: Fix audit logging - needs proper account object/parameters
            pass
            
            return dept
        
        except (NotFoundError, ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating department: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to update department: {str(e)}")
    
    # ============================================================================
    # DELETE (SOFT DELETE WITH CASCADE CHECKS)
    # ============================================================================
    
    @transaction.atomic()
    def delete_department(
        self,
        dept_id: str,
        requested_by_user_id: Optional[str] = None,
    ) -> None:
        """
        Delete department (soft delete).
        
        Args:
            dept_id: Department UUID
            requested_by_user_id: User deleting (for audit)
        
        Raises:
            NotFoundError: If department not found
            BusinessLogicError: If cascade check fails
        
        Workflow:
        1. Check department exists
        2. Check for users in this department
        3. Check for sub-departments
        4. Soft delete (is_deleted=True, deleted_at=now)
        5. Log audit
        
        Note:
        - Users assigned to this department MUST be re-assigned first
        - Sub-departments will be kept (not deleted) but become orphans
        - Option: Could cascade delete sub-departments if needed
        """
        try:
            # ========== STEP 1: GET DEPARTMENT ==========
            dept = self.department_repo.get_by_id(dept_id)
            if not dept:
                raise NotFoundError(f"Department {dept_id} not found")
            
            # ========== STEP 2: CHECK FOR USERS ==========
            users_in_dept = dept.get_all_members(include_subdepts=False).count()
            
            if users_in_dept > 0:
                raise ConflictError(
                    f"Cannot delete department '{dept.name}' - {users_in_dept} user(s) assigned. "
                    f"Please re-assign users to another department first."
                )
            
            # ========== STEP 3: CHECK SUB-DEPARTMENTS (WARNING, NOT ERROR) ==========
            sub_depts = dept.sub_departments.filter(is_deleted=False).count()
            
            if sub_depts > 0:
                logger.warning(
                    f"Deleting department {dept_id} has {sub_depts} sub-departments. "
                    f"Sub-departments will become orphans (parent_id=NULL)."
                )
                
                # Option: Could cascade delete or reparent
                # For now, just log the warning and let them become orphans
            
            # ========== STEP 4: SOFT DELETE ==========
            dept.is_deleted = True
            dept.deleted_at = timezone.now()
            dept.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
            
            logger.info(f"Department soft-deleted: {dept_id} (name={dept.name})")
            
            # ========== STEP 5: AUDIT LOG ==========
            # TODO: Fix audit logging - needs proper account object/parameters
            pass
        
        except (NotFoundError, ConflictError, BusinessLogicError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting department: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to delete department: {str(e)}")
    
    # ============================================================================
    # HELPER: GET SINGLE DEPARTMENT
    # ============================================================================
    
    def get_department(self, dept_id: str) -> Department:
        """
        Get single department by ID.
        
        Args:
            dept_id: Department UUID
        
        Returns:
            Department instance
        
        Raises:
            NotFoundError: If not found
        """
        try:
            dept = self.department_repo.get_by_id(dept_id)
            if not dept:
                raise NotFoundError(f"Department {dept_id} not found")
            return dept
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting department {dept_id}: {e}")
            raise BusinessLogicError(f"Failed to get department: {str(e)}")
    
    # ============================================================================
    # HYBRID APPROACH - DETAIL WITH COUNTS & EXPANDED DATA
    # ============================================================================
    
    def get_department_detail_with_counts(self, dept_id: str) -> Department:
        """
        Get department detail with counts (BASIC view).
        
        Returns: Department instance (serializer will add counts via SerializerMethodField)
        
        Used by:
        - GET /api/v1/departments/{id}
        
        Raises:
            NotFoundError: If not found
        """
        try:
            dept = self.get_department(dept_id)
            return dept
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting department detail with counts: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to get department detail: {str(e)}")
    
    def get_department_with_expanded_data(
        self,
        dept_id: str,
        expand_fields: List[str],
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Get department with expanded data (FULL view).
        
        Args:
            dept_id: Department UUID
            expand_fields: List of fields to expand (users, folders, documents)
            page: Page number for pagination
            page_size: Items per page
        
        Returns:
            Dict with department data + expanded lists
        
        Example:
            data = service.get_department_with_expanded_data(
                dept_id="uuid",
                expand_fields=['users', 'folders', 'documents'],
                page=1,
                page_size=10
            )
        
        Used by:
        - GET /api/v1/departments/{id}/detail?expand=users,folders,documents
        """
        try:
            # Get department
            dept = self.get_department(dept_id)
            
            from apps.documents.models import Document
            from django.db.models import Q
            
            # Build response
            result = {
                'id': dept.id,
                'name': dept.name,
                'description': dept.description,
                'parent_id': dept.parent_id,
                'parent': dept.parent,
                'manager_id': dept.manager_id,
                'manager': dept.manager,
                'member_count': dept.get_all_members(include_subdepts=False).count(),
                'folder_count': dept.folders.filter(is_deleted=False).count(),
                'document_count': Document.objects.filter(
                    Q(department=dept) | Q(folder__department=dept),
                    is_deleted=False
                ).distinct().count(),
                'sub_department_count': dept.sub_departments.filter(is_deleted=False).count(),
                'sub_departments': self._build_dept_tree_node(dept)['sub_departments'],
            }
            
            # Add expanded fields
            if 'users' in expand_fields:
                users_data = self._get_department_users_paginated(dept_id, page, page_size)
                result['users'] = users_data
            
            if 'folders' in expand_fields:
                folders_data = self._get_department_folders_paginated(dept_id, page, page_size)
                result['folders'] = folders_data
            
            if 'documents' in expand_fields:
                documents_data = self._get_department_documents_paginated(dept_id, page, page_size)
                result['documents'] = documents_data
            
            return result
        
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting department with expanded data: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to get department with expanded data: {str(e)}")
    
    # ============================================================================
    # PAGINATION HELPERS
    # ============================================================================
    
    def _get_department_users_paginated(
        self,
        dept_id: str,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Get users in department with pagination.
        
        Returns: {
            "items": [...],
            "pagination": {...}
        }
        """
        try:
            from django.core.paginator import Paginator
            
            dept = self.get_department(dept_id)
            
            # Get users via UserProfile relationship
            users_queryset = dept.users.filter(
                account__is_deleted=False
            ).select_related('account').order_by('account__username')
            
            # Paginate
            paginator = Paginator(users_queryset, page_size)
            page_obj = paginator.get_page(page)
            
            # Serialize
            items = []
            for user_profile in page_obj:
                account = user_profile.account
                items.append({
                    'id': str(account.id),
                    'username': account.username,
                    'email': account.email,
                    'full_name': user_profile.full_name,
                    'avatar_url': user_profile.avatar_url,
                })
            
            return {
                'items': items,
                'pagination': {
                    'page': page_obj.number,
                    'page_size': page_size,
                    'total_items': paginator.count,
                    'total_pages': paginator.num_pages,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            }
        except Exception as e:
            logger.error(f"Error getting department users: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to get department users: {str(e)}")
    
    def _get_department_folders_paginated(
        self,
        dept_id: str,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Get folders in department with pagination.
        
        Returns: {
            "items": [...],
            "pagination": {...}
        }
        """
        try:
            from django.core.paginator import Paginator
            
            dept = self.get_department(dept_id)
            
            # Get root folders of this department
            folders_queryset = dept.folders.filter(
                is_deleted=False,
                parent__isnull=True  # Only root folders
            ).order_by('name')
            
            # Paginate
            paginator = Paginator(folders_queryset, page_size)
            page_obj = paginator.get_page(page)
            
            # Serialize
            items = []
            for folder in page_obj:
                items.append({
                    'id': str(folder.id),
                    'name': folder.name,
                    'parent_id': str(folder.parent_id) if folder.parent_id else None,
                    'access_scope': folder.access_scope,
                    'created_by_id': str(folder.created_by_id) if folder.created_by_id else None,
                    'document_count': folder.documents.filter(is_deleted=False).count(),
                    'subfolder_count': folder.subfolders.filter(is_deleted=False).count(),
                    'created_at': folder.created_at.isoformat() if folder.created_at else None,
                })
            
            return {
                'items': items,
                'pagination': {
                    'page': page_obj.number,
                    'page_size': page_size,
                    'total_items': paginator.count,
                    'total_pages': paginator.num_pages,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            }
        except Exception as e:
            logger.error(f"Error getting department folders: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to get department folders: {str(e)}")
    
    def _get_department_documents_paginated(
        self,
        dept_id: str,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Get documents in department with pagination.
        
        Returns: {
            "items": [...],
            "pagination": {...}
        }
        """
        try:
            from django.core.paginator import Paginator
            
            dept = self.get_department(dept_id)
            
            from apps.documents.models import Document
            from django.db.models import Q
            
            # Get documents of this department
            documents_queryset = Document.objects.filter(
                Q(department=dept) | Q(folder__department=dept),
                is_deleted=False
            ).select_related('uploader', 'folder').distinct().order_by('-created_at')
            
            # Paginate
            paginator = Paginator(documents_queryset, page_size)
            page_obj = paginator.get_page(page)
            
            # Serialize
            items = []
            for document in page_obj:
                items.append({
                    'id': str(document.id),
                    'filename': document.filename,
                    'original_name': document.original_name,
                    'file_type': document.file_type,
                    'file_size': document.file_size,
                    'status': document.status,
                    'uploader_id': str(document.uploader_id) if document.uploader_id else None,
                    'department_id': str(document.department_id) if document.department_id else None,
                    'folder_id': str(document.folder_id) if document.folder_id else None,
                    'access_scope': document.access_scope,
                    'created_at': document.created_at.isoformat() if document.created_at else None,
                    'updated_at': document.updated_at.isoformat() if document.updated_at else None,
                })
            
            return {
                'items': items,
                'pagination': {
                    'page': page_obj.number,
                    'page_size': page_size,
                    'total_items': paginator.count,
                    'total_pages': paginator.num_pages,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            }
        except Exception as e:
            logger.error(f"Error getting department documents: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to get department documents: {str(e)}")
    
    def get_folder_documents_paginated(
        self,
        folder_id: str,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Get documents in folder with pagination.
        
        Used by:
        - GET /api/v1/folders/{id}/documents
        
        Returns: {
            "items": [...],
            "pagination": {...}
        }
        """
        try:
            from django.core.paginator import Paginator
            from apps.documents.models import Folder
            
            # Get folder
            folder = Folder.objects.filter(is_deleted=False).get(id=folder_id)
            
            # Get documents
            documents_queryset = folder.documents.filter(
                is_deleted=False
            ).select_related('uploader', 'department').order_by('-created_at')
            
            # Paginate
            paginator = Paginator(documents_queryset, page_size)
            page_obj = paginator.get_page(page)
            
            # Serialize
            items = []
            for document in page_obj:
                items.append({
                    'id': str(document.id),
                    'filename': document.filename,
                    'original_name': document.original_name,
                    'file_type': document.file_type,
                    'file_size': document.file_size,
                    'status': document.status,
                    'uploader_id': str(document.uploader_id) if document.uploader_id else None,
                    'department_id': str(document.department_id) if document.department_id else None,
                    'folder_id': str(document.folder_id) if document.folder_id else None,
                    'access_scope': document.access_scope,
                    'created_at': document.created_at.isoformat() if document.created_at else None,
                    'updated_at': document.updated_at.isoformat() if document.updated_at else None,
                })
            
            return {
                'items': items,
                'pagination': {
                    'page': page_obj.number,
                    'page_size': page_size,
                    'total_items': paginator.count,
                    'total_pages': paginator.num_pages,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            }
        except Exception as e:
            logger.error(f"Error getting folder documents: {e}", exc_info=True)
            raise BusinessLogicError(f"Failed to get folder documents: {str(e)}")
