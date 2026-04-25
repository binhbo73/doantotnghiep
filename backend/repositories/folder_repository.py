"""
FolderRepository - Specific queries for Folder model.
Extend BaseRepository với folder-specific business logic.

Responsibilities:
- Hierarchical tree queries (get_folder_tree, get_all_descendants)
- Folder accessibility checks (respects access_scope)
- Circular reference prevention
- Soft delete handling
"""

from typing import List, Optional, Dict, Tuple
from django.db.models import Q, Prefetch
from apps.documents.models import Folder
from .base_repository import BaseRepository
import logging


logger = logging.getLogger(__name__)


class FolderRepository(BaseRepository):
    """
    Repository cho Folder model.
    Optimize queries: select_related parent + department
    """
    
    model_class = Folder
    default_select_related = ['parent', 'department', 'created_by']
    default_prefetch_related = []
    
    # ============================================================
    # HIERARCHICAL TREE QUERIES
    # ============================================================
    
    def get_folder_tree(self, parent_id: Optional[str] = None) -> List[Folder]:
        """
        Get all folders in tree structure (root level or specific parent).
        
        Args:
            parent_id: If None, returns root folders (parent=NULL)
                      If UUID, returns folders where parent_id=parent_id
        
        Returns:
            List of Folder objects in tree (but not nested - building nesting in service)
        
        Example:
            folders = repo.get_folder_tree()  # All root folders
            subfolders = repo.get_folder_tree(parent_id="uuid-123")  # Children of folder-123
        """
        try:
            if parent_id is None:
                # Root level folders (no parent)
                return list(
                    self.get_base_queryset()
                    .filter(parent__isnull=True)
                    .order_by('name')
                )
            else:
                # Sub-level folders
                return list(
                    self.get_base_queryset()
                    .filter(parent_id=parent_id)
                    .order_by('name')
                )
        except Exception as e:
            logger.error(f"Error getting folder tree: {str(e)}")
            raise
    
    def get_all_descendants(self, folder_id: str) -> List[Folder]:
        """
        Get all descendants of a folder (recursive - all sub-folders recursively).
        
        Args:
            folder_id: Parent folder ID
        
        Returns:
            List of all descendant folders
        
        Example:
            # If folder structure is:
            # - Folder A
            #   - Folder B
            #     - Folder C
            # - Folder D
            
            descendants = repo.get_all_descendants("A")
            # Returns: [Folder B, Folder C]
        """
        try:
            descendants = []
            to_process = [folder_id]  # BFS queue
            
            while to_process:
                current_id = to_process.pop(0)
                
                # Get direct children
                children = list(
                    self.get_base_queryset()
                    .filter(parent_id=current_id)
                    .values_list('id', flat=True)
                )
                
                # Convert to Folder objects
                folder_children = list(
                    self.get_base_queryset()
                    .filter(parent_id=current_id)
                )
                
                descendants.extend(folder_children)
                to_process.extend(children)
            
            return descendants
            
        except Exception as e:
            logger.error(f"Error getting descendants of folder {folder_id}: {str(e)}")
            raise
    
    def get_subfolders(self, folder_id: str) -> List[Folder]:
        """
        Get direct children (1 level deep) of a folder.
        
        Args:
            folder_id: Parent folder ID
        
        Returns:
            List of direct children
        
        Example:
            direct_children = repo.get_subfolders("uuid-123")
        """
        try:
            return list(
                self.get_base_queryset()
                .filter(parent_id=folder_id)
                .order_by('name')
            )
        except Exception as e:
            logger.error(f"Error getting subfolders of {folder_id}: {str(e)}")
            raise
    
    # ============================================================
    # ACCESSIBILITY & PERMISSION CHECKS
    # ============================================================
    
    def check_circular_reference(self, folder_id: str, new_parent_id: Optional[str]) -> bool:
        """
        Check if moving folder_id to new_parent_id would create circular reference.
        
        Args:
            folder_id: Folder being moved
            new_parent_id: Target parent ID (None means make root)
        
        Returns:
            True if circular reference would be created, False otherwise
        
        Example:
            # Prevent: Moving "Folder A" into its own subfolder "Folder B"
            is_circular = repo.check_circular_reference("A", "B")
            # Returns: True (A is ancestor of B, so would create circle)
        """
        if new_parent_id is None:
            # Moving to root is always safe
            return False
        
        if str(folder_id) == str(new_parent_id):
            # Folder cannot be parent of itself
            return True
        
        try:
            # Get all ancestors of new_parent_id
            # If folder_id is among them, would create circle
            ancestors = []
            current_id = new_parent_id
            
            while current_id:
                ancestors.append(current_id)
                
                parent = self.get_base_queryset().filter(id=current_id).first()
                if not parent:
                    break
                
                current_id = parent.parent_id
                
                # Safety check to prevent infinite loop (max 100 levels)
                if len(ancestors) > 100:
                    logger.warning(f"Folder hierarchy exceeds 100 levels - possible data corruption")
                    break
            
            # If folder_id is in ancestors, it's circular
            return str(folder_id) in [str(a) for a in ancestors]
            
        except Exception as e:
            logger.error(f"Error checking circular reference: {str(e)}")
            raise
    
    def get_accessible_folders(
        self, 
        user_id: str, 
        user_department_id: Optional[str] = None,
        is_admin: bool = False
    ) -> List[Folder]:
        """
        Get folders that user can access based on access_scope and roles.
        
        LOGIC:
        - Admin (is_admin=True) → Access all folders
        - 'company' → all users can access
        - 'department' → only users in same department
        - 'personal' → only creator
        """
        try:
            query = self.get_base_queryset()
            
            # If Admin, return all folders
            if is_admin:
                return list(query.order_by('name'))
            
            # Combine filters using Q objects for regular users
            accessible = query.filter(
                Q(access_scope='company') |
                Q(access_scope='department', department_id=user_department_id) |
                Q(access_scope='personal', created_by_id=user_id)
            ).distinct()
            
            return list(accessible.order_by('name'))
            
        except Exception as e:
            logger.error(f"Error getting accessible folders for user {user_id}: {str(e)}")
            raise
    
    # ============================================================
    # DELETION & CASCADE
    # ============================================================
    
    def get_all_folder_ids_for_cascade_delete(self, folder_id: str) -> List[str]:
        """
        Get all folder IDs that should be deleted when deleting folder_id.
        Includes all descendants.
        
        Args:
            folder_id: Folder to delete
        
        Returns:
            List of folder IDs to delete (including the original)
        
        Example:
            ids_to_delete = repo.get_all_folder_ids_for_cascade_delete("uuid-123")
        """
        try:
            descendants = self.get_all_descendants(folder_id)
            descendant_ids = [str(d.id) for d in descendants]
            
            return [str(folder_id)] + descendant_ids
            
        except Exception as e:
            logger.error(f"Error getting cascade delete IDs for folder {folder_id}: {str(e)}")
            raise
    
    # ============================================================
    # SEARCH & FILTER
    # ============================================================
    
    def search_folders(self, search_term: str, department_id: Optional[str] = None) -> List[Folder]:
        """
        Search folders by name or description.
        
        Args:
            search_term: Search keyword
            department_id: Optional filter by department
        
        Returns:
            List of matching folders
        
        Example:
            results = repo.search_folders("project", department_id="uuid-dept")
        """
        try:
            query = self.get_base_queryset()
            
            # Search by name or description
            query = query.filter(
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term)
            )
            
            # Filter by department if provided
            if department_id:
                query = query.filter(department_id=department_id)
            
            return list(query.order_by('name'))
            
        except Exception as e:
            logger.error(f"Error searching folders: {str(e)}")
            raise
