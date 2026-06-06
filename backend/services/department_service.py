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

from django.db import transaction, models
from django.utils import timezone
from django.db.models import Q

from repositories.department_repository import DepartmentRepository
from repositories.role_repository import RoleRepository
from repositories.user_repository import UserRepository
from services.audit_service import AuditService
from services.base_service import BaseService
from apps.users.models import Department
from core.constants import PermissionCodes
from core.permissions.drf_permissions import user_has_any_permission, user_has_permission
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
        self.role_repo = RoleRepository()
        self.audit_service = AuditService()
        # Profile repository to update user's department when assigned as manager
        from repositories.user_profile_repository import UserProfileRepository
        self.profile_repository = UserProfileRepository()

    def _ensure_department_manager_role(self, account_id, granted_by=None) -> None:
        """
        Ensure the selected department manager has the manager role.

        Admin is company-wide and must not be attached to a department. When a
        regular user becomes a department manager, replace the basic user role
        with manager while preserving any custom roles.
        """
        manager_role = self.role_repo.get_by_code('manager')
        if not manager_role:
            raise ValidationError("Manager role was not found in the database")

        active_roles = self.user_repo.get_all_account_roles(account_id)
        has_manager_role = False
        user_role_ids = []

        for assignment in active_roles:
            role_code = getattr(assignment.role, 'code', None)
            if role_code == 'admin':
                raise ValidationError("Admin role is company-wide and must not be assigned as a department manager")
            if role_code == 'manager':
                has_manager_role = True
            if role_code == 'user':
                user_role_ids.append(assignment.role_id)

        for role_id in user_role_ids:
            self.user_repo.delete_account_role(account_id, role_id)

        if not has_manager_role:
            granted_by_account = None
            if granted_by:
                try:
                    granted_by_account = self.user_repo.get_by_id(granted_by)
                except Exception:
                    granted_by_account = None

            self.user_repo.create_account_role(
                account_id=account_id,
                role_id=manager_role.id,
                granted_by=granted_by_account,
                notes='Auto assigned when set as department manager',
            )

        logger.info(f"Ensured manager role for department manager account: {account_id}")

    def _sync_removed_manager_profile_department(self, account_id, removed_department_id) -> None:
        """
        Clear or move the old manager's profile department after manager update.

        A profile can only store one department. If the removed manager's profile
        points to the department they no longer manage, move it to another
        department they still manage, otherwise clear it.
        """
        profile = self.profile_repository.get_profile_by_account_id(account_id)
        if not profile or str(profile.department_id) != str(removed_department_id):
            return

        remaining_department = Department.objects.filter(
            Q(manager_id=account_id) | Q(managers__id=account_id),
            is_deleted=False,
        ).exclude(id=removed_department_id).distinct().order_by('name').first()

        next_department_id = remaining_department.id if remaining_department else None
        self.profile_repository.update_department(account_id, next_department_id)
        logger.info(
            f"Synced removed manager profile department: {account_id} -> {next_department_id}"
        )
    
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

    def get_accessible_department_ids(self, user) -> set:
        """Return department IDs the given user can view."""
        if not user:
            return set()

        if user_has_permission(user, PermissionCodes.DEPARTMENT_MANAGE):
            return set(
                str(dept_id)
                for dept_id in self.department_repo.get_base_queryset()
                .filter(is_deleted=False)
                .values_list('id', flat=True)
            )

        base_qs = self.department_repo.get_base_queryset().filter(is_deleted=False)

        if not user_has_any_permission(
            user,
            [
                PermissionCodes.DEPARTMENT_READ,
                PermissionCodes.DEPARTMENT_UPDATE,
                PermissionCodes.DEPARTMENT_MANAGE,
            ],
        ):
            return set()

        managed_ids = set(
            str(dept_id)
            for dept_id in base_qs.filter(
                Q(manager_id=user.id) | Q(managers__id=user.id)
            ).values_list('id', flat=True).distinct()
        )

        children_map: dict[str, list[str]] = {}
        for dept_id, parent_id in base_qs.values_list('id', 'parent_id'):
            if parent_id:
                children_map.setdefault(str(parent_id), []).append(str(dept_id))

        visible_ids = set()
        stack = list(managed_ids)
        while stack:
            current_id = stack.pop()
            if current_id in visible_ids:
                continue
            visible_ids.add(current_id)
            stack.extend(children_map.get(current_id, []))

        try:
            department_id = user.user_profile.department_id if hasattr(user, 'user_profile') else None
            if department_id:
                stack.append(str(department_id))
                while stack:
                    current_id = stack.pop()
                    if current_id in visible_ids:
                        continue
                    visible_ids.add(current_id)
                    stack.extend(children_map.get(current_id, []))
        except Exception:
            pass

        return visible_ids

    def can_access_department(self, user, dept_id: str) -> bool:
        return str(dept_id) in self.get_accessible_department_ids(user)

    def can_edit_department(self, user, dept_id: str) -> bool:
        if not user_has_any_permission(
            user,
            [PermissionCodes.DEPARTMENT_UPDATE, PermissionCodes.DEPARTMENT_MANAGE],
        ):
            return False
        return self.can_access_department(user, dept_id)

    def get_accessible_departments_queryset(self, user, include_deleted: bool = False):
        """Return departments visible to the given user."""
        dept_ids = self.get_accessible_department_ids(user)
        qs = self.department_repo.get_base_queryset()
        if not include_deleted:
            qs = qs.filter(is_deleted=False)
        if not dept_ids:
            return qs.none()
        return qs.filter(id__in=dept_ids)
    
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
            self.audit_log_action(
                action='CREATE',
                user_id=requested_by_user_id,
                resource_id=str(dept.id),
                resource_type='Department',
                query_text=f"Created department: {name}",
                details={'name': name, 'parent_id': parent_id, 'manager_id': manager_id}
            )
            # Keep the legacy manager FK and the new M2M relation in sync.
            if manager is not None:
                dept.managers.add(manager)
                logger.info(f"Added manager to department.managers: {manager.id} -> {dept.id}")
                self.profile_repository.update_department(manager.id, dept.id)
                logger.info(f"Assigned manager's profile department updated: {manager.id} -> {dept.id}")
                self._ensure_department_manager_role(manager.id, granted_by=requested_by_user_id)
            
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
            previous_manager_id = str(dept.manager_id) if dept.manager_id else None
            
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
            self.audit_log_action(
                action='UPDATE',
                user_id=requested_by_user_id,
                resource_id=str(dept_id),
                resource_type='Department',
                query_text=f"Updated department: {dept.name}",
                details={'updates': updates}
            )

            # If manager changed to a specific user, update their profile.department
            if 'manager_id' in updates:
                new_manager_id = updates.get('manager_id')
                if previous_manager_id:
                    dept.managers.remove(previous_manager_id)
                    self._sync_removed_manager_profile_department(previous_manager_id, dept.id)

                if new_manager_id:
                    new_manager = self.user_repo.get_by_id(new_manager_id)
                    dept.managers.add(new_manager)
                    self.profile_repository.update_department(new_manager_id, dept.id)
                    logger.info(f"Updated manager's profile department: {new_manager_id} -> {dept.id}")
                    self._ensure_department_manager_role(new_manager_id, granted_by=requested_by_user_id)
            
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
        2. Check for direct users in this department
        3. Check for active child departments
        4. Check for active folders and documents
        5. Soft delete only when the department is empty
        6. Log audit
        
        Note:
        - This is a safe delete: no users, child departments, folders, or
          documents are moved, detached, archived, or deleted automatically.
        """
        try:
            # ========== STEP 1: GET DEPARTMENT ==========
            dept = self.department_repo.get_by_id(dept_id)
            if not dept:
                raise NotFoundError(f"Department {dept_id} not found")
            
            # ========== STEP 2: CHECK ALL DEPENDENCIES ==========
            from apps.documents.models import Document

            users_in_dept = dept.get_all_members(include_subdepts=False).count()
            sub_depts = dept.sub_departments.filter(is_deleted=False).count()
            folders_in_dept = dept.folders.filter(is_deleted=False).count()
            documents_in_dept = Document.objects.filter(
                Q(department=dept) | Q(folder__department=dept),
                is_deleted=False,
            ).distinct().count()

            blockers = {
                'users': users_in_dept,
                'child_departments': sub_depts,
                'folders': folders_in_dept,
                'documents': documents_in_dept,
            }
            active_blockers = {
                key: count for key, count in blockers.items() if count > 0
            }

            if active_blockers:
                blocker_labels = {
                    'users': 'direct user(s)',
                    'child_departments': 'child department(s)',
                    'folders': 'folder(s)',
                    'documents': 'document(s)',
                }
                blocker_summary = ', '.join(
                    f"{count} {blocker_labels[key]}"
                    for key, count in active_blockers.items()
                )
                raise ConflictError(
                    (
                        f"Cannot delete department '{dept.name}' because it still contains "
                        f"{blocker_summary}. Reassign or remove these resources first."
                    ),
                    detail={
                        'department_id': str(dept.id),
                        'department_name': dept.name,
                        'blockers': blockers,
                    },
                )

            # ========== STEP 3: SOFT DELETE ==========
            dept.is_deleted = True
            dept.deleted_at = timezone.now()
            dept.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
            
            logger.info(f"Department soft-deleted: {dept_id} (name={dept.name})")
            
            # ========== STEP 4: AUDIT LOG ==========
            self.audit_log_action(
                action='DELETE',
                user_id=requested_by_user_id,
                resource_id=str(dept_id),
                resource_type='Department',
                query_text=f"Deleted department: {dept.name}",
                details={'safe_delete_checks': blockers}
            )
        
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
        user_id: Optional[str] = None,
        is_admin: bool = False,
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
            from apps.users.models import Department
            
            # Get folder
            folder = Folder.objects.filter(is_deleted=False).get(id=folder_id)
            
            # Get documents
            if is_admin:
                documents_queryset = folder.documents.filter(
                    is_deleted=False
                ).select_related('uploader', 'department').order_by('-created_at')
            else:
                from repositories.document_repository import DocumentRepository
                doc_repo = DocumentRepository()
                accessible_docs = doc_repo.get_accessible_documents(user_id)
                documents_queryset = folder.documents.filter(
                    is_deleted=False,
                    id__in=accessible_docs.values_list('id', flat=True)
                ).select_related('uploader', 'department').order_by('-created_at')

            # Paginate
            paginator = Paginator(documents_queryset, page_size)
            page_obj = paginator.get_page(page)
            
            # Serialize
            items = []
            for document in page_obj:
                # Determine user permission level
                # Frontend object-permission helpers only understand delete/write/read/none.
                # Map admin to the highest supported object permission so the UI can render access correctly.
                if is_admin:
                    my_permission = 'delete'
                elif str(document.uploader_id) == str(user_id):
                    my_permission = 'write'
                else:
                    my_permission = 'read'
                
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
                    'my_permission': my_permission,
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
