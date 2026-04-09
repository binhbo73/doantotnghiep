"""
User Service - Nghiệp vụ quản lý Account và Profile.
Xử lý các thao tác về Tài khoản người dùng.
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from django.apps import apps
from django.db import transaction
from django.utils import timezone
from core.exceptions import (
    BusinessLogicError,
    ValidationError,
    InvalidCredentialsError,
    AccountBlockedError,
    AccountInactiveError,
)
from services.base_service import BaseService
from repositories.user_repository import UserRepository
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


class UserService(BaseService):
    """
    User Management Service - Logic cho Tài khoản
    """
    
    repository_class = UserRepository
    
    def __init__(self):
        super().__init__()  # BaseService will initialize repository from repository_class
        self.Account = apps.get_model('users', 'Account')
        self.UserProfile = apps.get_model('users', 'UserProfile')
        
        # Initialize UserProfile repository for Phase 2 operations
        from repositories.user_profile_repository import UserProfileRepository
        self.profile_repository = UserProfileRepository()

    @transaction.atomic
    def register_account(self, account_data: Dict) -> Any:
        """Đăng ký tài khoản mới"""
        try:
            # Extract department before creating account (department is not on Account anymore)
            department = account_data.pop('department', None)
            password = account_data.pop('password')
            
            # Create account WITHOUT department (it's now on UserProfile)
            account = self.Account(**account_data)
            account.set_password(password)
            account.save()
            
            # Create UserProfile (1-1 relationship) with department
            try:
                profile_data = {
                    'account': account,
                    'full_name': account.get_full_name() or account.username,
                }
                if department:
                    profile_data['department'] = department
                
                self.UserProfile.objects.create(**profile_data)
                logger.info(f"UserProfile created for: {account.username}")
            except Exception as e:
                logger.error(f"Error creating UserProfile: {str(e)}")
                raise BusinessLogicError(f"Không thể tạo Profile: {str(e)}")
            
            logger.info(f"User registered: {account.username}")
            return account
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            raise BusinessLogicError(f"Đăng ký thất bại: {str(e)}")

    def change_password(self, user_id: int, old_password: str, new_password: str):
        """Đổi mật khẩu bảo mật (kiểm tra mật khẩu cũ)"""
        try:
            user = self.get_by_id(user_id)
        except Exception as e:
            logger.error(f"Failed to fetch user {user_id}: {str(e)}")
            raise ValidationError(f"Không thể lấy thông tin tài khoản: {str(e)}")
        
        if not user.check_password(old_password):
            raise ValidationError("Mật khẩu hiện tại không chính xác.")
        
        user.set_password(new_password)
        user.save(update_fields=['password', 'updated_at'])
        logger.info(f"User {user_id} changed password successfully")

    def update_account(self, user_id: int, account_data: Dict) -> Any:
        """Cập nhật thông tin account của user"""
        # ⚠️ Unpack dict to kwargs vì BaseService.update(pk, **data)
        return self.update(user_id, **account_data)

    def deactivate_account(self, user_id: int):
        """Soft-delete tài khoản (set is_deleted=True)"""
        from django.utils import timezone
        user = self.get_by_id(user_id)
        user.is_deleted = True
        user.deleted_at = timezone.now()
        user.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
        logger.warning(f"Account {user_id} soft-deleted")
    
    def change_account_status(self, user_id: int, new_status: str, reason: str = '') -> Any:
        """
        Change user account status (active/blocked/inactive).
        NOT the same as soft-delete!
        
        Args:
            user_id: Account ID
            new_status: New status (active, blocked, inactive)
            reason: Reason for status change
        
        Returns:
            Updated Account object
        
        Raises:
            ValidationError: If status invalid
        """
        try:
            from core.constants import AccountStatus
            
            # Validate status
            valid_statuses = [AccountStatus.ACTIVE, AccountStatus.BLOCKED, AccountStatus.INACTIVE]
            if new_status not in valid_statuses:
                raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")
            
            # Get user
            user = self.get_by_id(user_id)
            
            # Update ONLY status field (not is_deleted)
            old_status = user.status
            user.status = new_status
            user.save(update_fields=['status', 'updated_at'])
            
            logger.info(f"Account {user_id} status changed: {old_status} → {new_status}. Reason: {reason}")
            return user
        
        except Exception as e:
            logger.error(f"Error changing account status: {str(e)}")
            raise

    def get_user_permissions(self, user_id: int) -> List[str]:
        """Lấy danh sách tất cả mã permission của user (từ Role)"""
        user = self.get_by_id(user_id)
        return user.get_permissions() if hasattr(user, 'get_permissions') else []
    
    @transaction.atomic
    def authenticate(self, email_or_username: str, password: str, request=None) -> Dict[str, Any]:
        """
        Authenticate user (Login) - Comprehensive authentication with all checks.
        
        LOGIC CHAIN:
        1. Validate input
        2. Find user by email or username
        3. Check account exists
        4. Check account status (not blocked, not inactive)
        5. Verify password
        6. Generate JWT tokens
        7. Update last_login timestamp
        8. Log audit trail
        9. Get permissions and roles
        10. Return comprehensive result
        
        Args:
            email_or_username: User email or username
            password: User password (plaintext)
            request: HTTP request object (for audit logging)
            
        Returns:
            Dict with keys:
            - user: AccountSerializer data
            - access_token: JWT access token
            - refresh_token: JWT refresh token
            - permissions: List of permission codes
            - roles: List of role objects
            - department_id: User's department ID
            
        Raises:
            ValidationError: If validation fails
            InvalidCredentialsError: If credentials are invalid
            AccountBlockedError: If account is blocked
            AccountInactiveError: If account is inactive
            BusinessLogicError: For unexpected errors
        """
        try:
            # STEP 1: Validate input
            if not email_or_username or not password:
                raise ValidationError("Email/username và mật khẩu bắt buộc")
            
            email_or_username = email_or_username.strip()
            
            # STEP 2-3: Find user by email or username
            user = self.repository.get_by_email_or_username(email_or_username)
            
            if not user:
                identifier = email_or_username
                logger.warning(f"Login attempt with non-existent user: {identifier}")
                raise InvalidCredentialsError("Email/username hoặc mật khẩu không chính xác")
            
            # STEP 4: Check account status - BLOCKED
            if user.status == 'blocked':
                logger.warning(f"Login attempt with blocked account: {user.id}")
                raise AccountBlockedError("Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên.")
            
            # STEP 4: Check account status - INACTIVE
            if user.status == 'inactive' or not user.is_active:
                logger.warning(f"Login attempt with inactive account: {user.id}")
                raise AccountInactiveError("Tài khoản không hoạt động. Vui lòng liên hệ quản trị viên.")
            
            # STEP 5: Verify password
            if not user.check_password(password):
                logger.warning(f"Failed login attempt for user: {user.id}")
                raise InvalidCredentialsError("Email/username hoặc mật khẩu không chính xác")
            
            # STEP 6: Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # STEP 7: Update last_login timestamp
            try:
                from django.utils import timezone
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                logger.info(f"Updated last_login for user: {user.username}")
            except Exception as e:
                logger.warning(f"Failed to update last_login: {str(e)}")
            
            # STEP 8: Log audit trail
            try:
                from apps.operations.models import AuditLog
                ip_address = None
                user_agent = None
                
                if request:
                    # Get IP address from request
                    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                    ip_address = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
                    user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
                
                AuditLog.objects.create(
                    user_id=user.id,
                    action='LOGIN',
                    description=f"User {user.username} logged in successfully",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={'method': 'password', 'email_or_username': email_or_username}
                )
                logger.info(f"Audit log created for login: {user.id}")
            except Exception as e:
                logger.warning(f"Failed to create audit log for login: {str(e)}")
            
            # STEP 9: Get permissions and roles
            try:
                permission_codes = user.get_permissions() if hasattr(user, 'get_permissions') else []
                
                roles = [
                    {
                        "id": str(ar.role.id),
                        "code": ar.role.code,
                        "name": ar.role.name
                    }
                    for ar in user.account_roles.filter(is_deleted=False).select_related('role')
                ]
                
                logger.info(f"Fetched permissions ({len(permission_codes)}) and roles ({len(roles)}) for user {user.id}")
            except Exception as e:
                logger.warning(f"Failed to fetch permissions/roles: {str(e)}")
                permission_codes = []
                roles = []
            
            # Get department from UserProfile
            department_id = None
            try:
                user_profile = user.user_profile if hasattr(user, 'user_profile') else None
                if user_profile and user_profile.department_id:
                    department_id = str(user_profile.department_id)
            except Exception as e:
                logger.warning(f"Failed to fetch user profile: {str(e)}")
            
            # STEP 10: Return comprehensive result
            from api.serializers.user_serializers import AccountSerializer
            
            result = {
                'user': AccountSerializer(user).data,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'permissions': permission_codes,
                'roles': roles,
                'department_id': department_id,
            }
            
            logger.info(f"User {user.id} authenticated successfully")
            return result
        
        except (InvalidCredentialsError, ValidationError, AccountBlockedError, AccountInactiveError):
            # Expected exceptions - just re-raise
            raise
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {str(e)}", exc_info=True)
            raise BusinessLogicError(f"Lỗi xác thực không mong muốn: {str(e)}")
    
    
    # ============================================================
    # USER PROFILE OPERATIONS (Phase 2 - Self-Service)
    # ============================================================
    
    def get_user_profile(self, user_id) -> Dict[str, Any]:
        """
        Get UserProfile by UserProfile ID.
        
        Business Logic:
        1. Fetch profile from repository using profile ID (not account ID)
        2. Validate profile exists
        3. Return profile data
        
        Args:
            user_id: UUID of UserProfile (not Account)
        
        Returns:
            UserProfile object
        
        Raises:
            ValidationError: If profile not found
        """
        try:
            profile = self.profile_repository.get_profile_by_id(user_id)
            
            if not profile:
                raise ValidationError(f"Profile not found for user_id {user_id}")
            
            logger.info(f"Profile fetched with user_id: {user_id}")
            return profile
        
        except Exception as e:
            logger.error(f"Error fetching profile: {str(e)}")
            raise
    
    def get_user_profile_by_account_id(self, account_id) -> Dict[str, Any]:
        """
        Get UserProfile by Account ID.
        
        Used for self-service APIs where we have Account ID (from request.user.id)
        but need UserProfile for returning profile data.
        
        Business Logic:
        1. Fetch profile from repository using account_id
        2. Validate profile exists
        3. Return profile data
        
        Args:
            account_id: UUID of Account
        
        Returns:
            UserProfile object
        
        Raises:
            ValidationError: If profile not found
        """
        try:
            profile = self.profile_repository.get_profile_by_account_id(account_id)
            
            if not profile:
                raise ValidationError(f"Profile not found for account {account_id}")
            
            logger.info(f"Profile fetched for account: {account_id}")
            return profile
        
        except Exception as e:
            logger.error(f"Error fetching profile: {str(e)}")
            raise
    
    @transaction.atomic
    def update_user_profile(self, user_id, profile_data: Dict[str, Any]) -> Any:
        """
        Update UserProfile information (personal data only).
        
        Business Logic:
        1. Validate profile exists by user_id (UserProfile ID)
        2. Get current profile from repository
        3. Update allowed fields (full_name, address, birthday, metadata)
        4. Save via repository
        5. Return updated profile
        
        Args:
            user_id: UUID of UserProfile (not Account)
            profile_data: Dict with fields to update
        
        Returns:
            Updated UserProfile object
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Validate profile exists by user_id
            profile = self.profile_repository.get_profile_by_id(user_id)
            if not profile:
                raise ValidationError(f"Profile not found for user_id {user_id}")
            
            # Update only allowed fields
            allowed_fields = ['full_name', 'address', 'birthday', 'metadata']
            for field, value in profile_data.items():
                if field in allowed_fields and value is not None:
                    setattr(profile, field, value)
            
            profile.save(update_fields=list(profile_data.keys()) + ['updated_at'])
            
            logger.info(f"Profile updated for user_id: {user_id}. Fields: {list(profile_data.keys())}")
            return profile
        
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            raise
    
    @transaction.atomic
    def update_user_profile_by_account_id(self, account_id, profile_data: Dict[str, Any]) -> Any:
        """
        Update UserProfile information by Account ID.
        
        Used for self-service APIs where we have Account ID (from request.user.id).
        Fetches the associated UserProfile and updates it.
        
        Business Logic:
        1. Validate profile exists by account_id
        2. Update allowed fields (full_name, address, birthday, metadata)
        3. Save profile
        4. Return updated profile
        
        Args:
            account_id: UUID of Account
            profile_data: Dict with fields to update
        
        Returns:
            Updated UserProfile object
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Validate profile exists by account_id
            profile = self.profile_repository.get_profile_by_account_id(account_id)
            if not profile:
                raise ValidationError(f"Profile not found for account {account_id}")
            
            # Update only allowed fields
            allowed_fields = ['full_name', 'address', 'birthday', 'metadata']
            for field, value in profile_data.items():
                if field in allowed_fields and value is not None:
                    setattr(profile, field, value)
            
            profile.save(update_fields=list(profile_data.keys()) + ['updated_at'])
            
            logger.info(f"Profile updated for account: {account_id}. Fields: {list(profile_data.keys())}")
            return profile
        
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            raise
    
    @transaction.atomic
    def upload_avatar(self, user_id, avatar_file) -> str:
        """
        Upload avatar file and update UserProfile.
        
        Business Logic:
        1. Validate profile exists by user_id (UserProfile ID)
        2. Generate avatar URL
        3. Update avatar URL in profile
        4. Return avatar URL
        
        Args:
            user_id: UUID of UserProfile (not Account)
            avatar_file: Uploaded file object
        
        Returns:
            Avatar URL string
        
        Raises:
            ValidationError: If validation fails
            BusinessLogicError: If upload fails
        """
        try:
            # Get profile by user_id
            profile = self.profile_repository.get_profile_by_id(user_id)
            if not profile:
                raise ValidationError(f"Profile not found for user_id {user_id}")
            
            # TODO: Upload file to S3/Storage
            import uuid
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"avatar_{user_id}_{timestamp}.jpg"
            avatar_url = f"/media/avatars/{filename}"
            
            # Update profile avatar_url
            profile.avatar_url = avatar_url
            profile.save(update_fields=['avatar_url', 'updated_at'])
            
            logger.info(f"Avatar uploaded for user_id: {user_id} - {avatar_url}")
            return avatar_url
        
        except Exception as e:
            logger.error(f"Error uploading avatar: {str(e)}")
            raise
    
    @transaction.atomic
    def upload_avatar_by_account_id(self, account_id, avatar_file) -> str:
        """
        Upload avatar file by Account ID.
        
        Used for self-service APIs where we have Account ID (from request.user.id).
        Fetches the associated UserProfile and updates avatar.
        
        Business Logic:
        1. Get profile by account_id
        2. Validate profile exists
        3. Generate avatar URL
        4. Update avatar URL in profile
        5. Return avatar URL
        
        Args:
            account_id: UUID of Account
            avatar_file: Uploaded file object
        
        Returns:
            Avatar URL string
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Get profile by account_id
            profile = self.profile_repository.get_profile_by_account_id(account_id)
            if not profile:
                raise ValidationError(f"Profile not found for account {account_id}")
            
            # TODO: Upload file to S3/Storage
            import uuid
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"avatar_{account_id}_{timestamp}.jpg"
            avatar_url = f"/media/avatars/{filename}"
            
            # Update profile avatar_url
            profile.avatar_url = avatar_url
            profile.save(update_fields=['avatar_url', 'updated_at'])
            
            logger.info(f"Avatar uploaded for account: {account_id} - {avatar_url}")
            return avatar_url
        
        except Exception as e:
            logger.error(f"Error uploading avatar: {str(e)}")
            raise
    
    @transaction.atomic
    def change_user_department(self, account_id, department_id) -> Any:
        """
        Change user's department.
        
        Business Logic:
        1. Validate account exists
        2. Validate department exists
        3. Update department via repository
        4. Return updated profile
        
        Args:
            account_id: UUID of account
            department_id: UUID of new department
        
        Returns:
            Updated UserProfile object
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Validate account exists
            account = self.Account.objects.filter(id=account_id, is_deleted=False).first()
            if not account:
                raise ValidationError(f"Account {account_id} not found")
            
            # Update department via repository
            updated_profile = self.profile_repository.update_department(account_id, department_id)
            
            logger.info(f"Department changed for account: {account_id} → {department_id}")
            return updated_profile
        
        except Exception as e:
            logger.error(f"Error changing department: {str(e)}")
            raise
    
    @transaction.atomic
    def replace_user_role(self, account_id, old_role_id, new_role_id, notes='', granted_by=None) -> Any:
        """
        Replace account's role with a new one.
        
        Business Logic:
        1. Validate account exists
        2. Get old active role assignment
        3. Soft-delete old role
        4. Create new role assignment
        5. Return new role assignment
        
        Args:
            account_id: UUID of Account
            old_role_id: UUID of role to deactivate
            new_role_id: UUID of role to assign
            notes: Optional notes
            granted_by: User performing the action
        
        Returns:
            New AccountRole object
        
        Raises:
            ValidationError: If validation fails
            BusinessLogicError: If business logic fails
        """
        try:
            from apps.users.models import AccountRole, Role
            
            # Validate account exists
            user = self.get_by_id(account_id)
            if not user:
                raise ValidationError(f"Account {account_id} not found")
            
            # Validate old role exists
            old_ar = AccountRole.objects.get(
                account_id=account_id,
                role_id=old_role_id,
                is_deleted=False
            )
            
            # Soft-delete old assignment
            old_ar.is_deleted = True
            old_ar.deleted_at = timezone.now()
            old_ar.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
            logger.info(f"Old role {old_role_id} soft-deleted for account {account_id}")
            
            # Create new role assignment
            new_ar = AccountRole.objects.create(
                account_id=account_id,
                role_id=new_role_id,
                granted_by=granted_by or user,
                notes=notes
            )
            
            logger.info(f"New role {new_role_id} assigned to account {account_id}")
            return new_ar
        
        except AccountRole.DoesNotExist:
            raise ValidationError(f"Account doesn't have old role assigned")
        except Exception as e:
            logger.error(f"Error replacing user role: {str(e)}")
            raise
    
    @transaction.atomic
    def assign_role_to_user(self, account_id, role_id, notes='', granted_by=None) -> Any:
        """
        Assign a new role to account.
        
        Business Logic:
        1. Validate account exists
        2. Validate role not already assigned
        3. Create AccountRole
        4. Return assignment
        
        Args:
            account_id: UUID of Account
            role_id: UUID of Role to assign
            notes: Optional notes
            granted_by: User performing the action
        
        Returns:
            AccountRole object
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            from apps.users.models import AccountRole, Role
            
            # Validate account exists
            user = self.get_by_id(account_id)
            if not user:
                raise ValidationError(f"Account {account_id} not found")
            
            # Check if role already assigned
            existing = AccountRole.objects.filter(
                account_id=account_id,
                role_id=role_id,
                is_deleted=False
            ).exists()
            
            if existing:
                raise ValidationError(f"Account already has this role assigned")
            
            # Create assignment
            ar = AccountRole.objects.create(
                account_id=account_id,
                role_id=role_id,
                granted_by=granted_by or user,
                notes=notes
            )
            
            logger.info(f"Role {role_id} assigned to account {account_id}")
            return ar
        
        except AccountRole.DoesNotExist:
            raise ValidationError(f"Account doesn't have role assigned")
        except Exception as e:
            logger.error(f"Error assigning role: {str(e)}")
            raise
    
    @transaction.atomic
    def remove_role_from_user(self, account_id, role_id) -> None:
        """
        Remove a role from account.
        
        Business Logic:
        1. Validate account exists
        2. Validate role assignment exists
        3. Check if trying to remove last role (prevent)
        4. Soft-delete the assignment
        
        Args:
            account_id: UUID of Account
            role_id: UUID of Role to remove
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            from apps.users.models import AccountRole
            
            # Validate account exists
            user = self.get_by_id(account_id)
            if not user:
                raise ValidationError(f"Account {account_id} not found")
            
            # Get active assignments
            active_assignments = AccountRole.objects.filter(
                account_id=account_id,
                is_deleted=False
            )
            
            # Check if role assigned
            ar = active_assignments.filter(role_id=role_id).first()
            if not ar:
                raise ValidationError(f"Account doesn't have this role assigned")
            
            # Prevent removing last role
            if active_assignments.count() == 1:
                raise ValidationError(f"Cannot remove account's last role")
            
            # Soft-delete the assignment
            ar.is_deleted = True
            ar.save()
            
            logger.info(f"Role {role_id} removed from account {account_id}")
        
        except Exception as e:
            logger.error(f"Error removing role: {str(e)}")
            raise
    
    @transaction.atomic
    def update_role_assignment(self, account_id, role_id, notes='') -> Any:
        """
        Update role assignment info (notes).
        
        Business Logic:
        1. Validate account exists
        2. Validate role assignment exists
        3. Update assignment notes
        4. Return updated assignment
        
        Args:
            account_id: UUID of Account
            role_id: UUID of Role
            notes: Updated notes
        
        Returns:
            Updated AccountRole object
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            from apps.users.models import AccountRole
            
            # Validate account exists
            user = self.get_by_id(account_id)
            if not user:
                raise ValidationError(f"Account {account_id} not found")
            
            # Get assignment
            ar = AccountRole.objects.filter(
                account_id=account_id,
                role_id=role_id,
                is_deleted=False
            ).first()
            
            if not ar:
                raise ValidationError(f"User doesn't have this role assigned")
            
            # Update notes
            ar.notes = notes
            ar.save(update_fields=['notes', 'updated_at'])
            
            logger.info(f"Role {role_id} assignment notes updated for account {user_id}")
            return ar
        
        except Exception as e:
            logger.error(f"Error updating role assignment: {str(e)}")
            raise
    
    # ============================================================
    # ADMIN USER MANAGEMENT OPERATIONS (Phase 3 - Admin)
    # ============================================================
    
    def get_by_email(self, email) -> Any:
        """
        Get user by email address.
        
        Args:
            email: Email address
        
        Returns:
            User object or None
        """
        try:
            return self.Account.objects.filter(
                email=email,
                is_deleted=False
            ).first()
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None
    
    def reset_user_password(self, user_id, new_password) -> None:
        """
        Reset user password (from reset token).
        
        Business Logic:
        1. Validate user exists
        2. Set new password
        3. Save to database
        
        Args:
            user_id: UUID of user
            new_password: New password (must be validated by caller)
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            user = self.get_by_id(user_id)
            if not user:
                raise ValidationError(f"Account {user_id} not found")
            
            user.set_password(new_password)
            user.save(update_fields=['password', 'updated_at'])
            
            logger.info(f"Password reset for account {user_id}")
        
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            raise
    
    def admin_reset_user_password(self, account_id, new_password) -> Any:
        """
        Admin reset account password (no token needed).
        
        Business Logic:
        1. Validate account exists
        2. Prevent self-reset
        3. Set new password
        4. Save to database
        5. Return account
        
        Args:
            account_id: UUID of account to reset
            new_password: New password (must be validated by caller)
        
        Returns:
            Updated user object
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            user = self.get_by_id(account_id)
            if not user:
                raise ValidationError(f"Account {account_id} not found")
            
            user.set_password(new_password)
            user.save(update_fields=['password', 'updated_at'])
            
            logger.info(f"Admin reset password for account {account_id}")
            return user
        
        except Exception as e:
            logger.error(f"Error on admin reset password: {str(e)}")
            raise
    
    @transaction.atomic
    def resolve_or_create_default_department(self, department_id: str = None) -> Any:
        """
        Resolve department by ID or get/create default company department.
        
        Business Logic:
        1. If department_id provided → find and return it
        2. If not provided → find default root department (parent_id=null)
        3. If no default exists → create default "Company" department
        
        Args:
            department_id: Optional department UUID string
        
        Returns:
            Department object
        
        Raises:
            ValidationError: If department not found
        """
        try:
            from django.apps import apps
            import uuid as uuid_module
            
            Department = apps.get_model('users', 'Department')
            
            # Strategy 1: If department_id provided → find it
            if department_id:
                try:
                    dept = Department.objects.get(id=department_id, is_deleted=False)
                    logger.info(f"Department resolved: {dept.name}")
                    return dept
                except Department.DoesNotExist:
                    raise ValidationError(f"Department '{department_id}' not found")
            
            # Strategy 2: If not provided → get or create default
            dept = Department.objects.filter(
                parent_id__isnull=True,
                is_deleted=False
            ).first()
            
            if dept:
                logger.info(f"Auto-assigned default department: {dept.name}")
                return dept
            
            # Create default if none exists
            dept = Department.objects.create(
                id=uuid_module.uuid4(),
                name="Company",
                parent=None,
                is_deleted=False
            )
            logger.info(f"Created default department: {dept.id}")
            return dept
        
        except Exception as e:
            logger.error(f"Error resolving department: {str(e)}")
            raise
    
    def get_user_roles_detailed(self, user_id: str) -> List[Dict]:
        """
        Get user's roles with detailed permission information.
        
        Business Logic:
        1. Validate user exists
        2. Get all active role assignments
        3. For each assignment, get role details + permissions
        4. Build detailed response with role metadata
        
        Args:
            user_id: UUID of Account
        
        Returns:
            List of role dicts with details [
                {
                    'role_id': '...',
                    'role_code': '...',
                    'role_name': '...',
                    'permissions': [...],
                    'assigned_at': '...',
                    'notes': '...'
                },
                ...
            ]
        
        Raises:
            ValidationError: If user not found
        """
        try:
            from apps.users.models import AccountRole
            
            # Validate user exists
            user = self.get_by_id(user_id)
            if not user:
                raise ValidationError(f"Account {user_id} not found")
            
            # Get active role assignments
            account_roles = AccountRole.objects.filter(
                account_id=user_id,
                is_deleted=False
            ).select_related('role').prefetch_related(
                'role__role_permissions__permission'
            )
            
            roles_data = []
            for ar in account_roles:
                role = ar.role
                permissions = [
                    perm.permission.code
                    for perm in role.role_permissions.filter(is_deleted=False)
                ]
                
                roles_data.append({
                    'role_id': str(role.id),
                    'role_code': role.code,
                    'role_name': role.name,
                    'permissions': permissions,
                    'assigned_at': ar.created_at.isoformat() if ar.created_at else None,
                    'notes': ar.notes or ''
                })
            
            logger.info(f"Retrieved {len(roles_data)} roles for account {user_id}")
            return roles_data
        
        except Exception as e:
            logger.error(f"Error getting user roles detailed: {str(e)}")
            raise
    
    def register_account_admin(self, account_data: Dict, department=None, role_id=None) -> Any:
        """
        Admin create account with specified role and department.
        
        Business Logic:
        1. Validate account data
        2. Create Account
        3. Create UserProfile with department
        4. Assign role (default USER if not specified)
        5. Return user
        
        Args:
            account_data: Dict with username, email, first_name, last_name, password
            department: Department object (optional)
            role_id: Role UUID (optional, uses default USER if not provided)
        
        Returns:
            Created user object
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            from django.contrib.auth import get_user_model
            from apps.users.models import UserProfile, AccountRole, Role
            from core.constants import RoleIds, AccountStatus
            
            User = get_user_model()
            
            # Extract fields
            username = account_data.get('username')
            email = account_data.get('email')
            password = account_data.get('password')
            first_name = account_data.get('first_name', '')
            last_name = account_data.get('last_name', '')
            
            # Validation
            if not username or not email or not password:
                raise ValidationError("Username, email, and password are required")
            
            if User.objects.filter(username=username, is_deleted=False).exists():
                raise ValidationError(f"Username '{username}' already exists")
            
            if User.objects.filter(email=email, is_deleted=False).exists():
                raise ValidationError(f"Email '{email}' already exists")
            
            # Create user with proper status constant
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                status=AccountStatus.ACTIVE
            )
            
            # Create UserProfile with department
            try:
                profile_data = {
                    'account': user,
                    'full_name': user.get_full_name() or user.username,
                }
                if department:
                    profile_data['department'] = department
                
                UserProfile.objects.create(**profile_data)
                logger.info(f"UserProfile created for: {user.username}")
            except Exception as e:
                logger.error(f"Error creating UserProfile: {str(e)}")
                # Don't fail - user still created but without profile
            
            # Assign role
            try:
                if not role_id:
                    # Default to USER role
                    role_id = RoleIds.USER
                
                role = Role.objects.get(id=role_id, is_deleted=False)
                AccountRole.objects.create(
                    account=user,
                    role=role,
                    notes="Created by admin"
                )
                logger.info(f"Role {role.code} assigned to {user.username}")
            except Exception as e:
                logger.warning(f"Failed to assign role: {str(e)}")
                # Don't fail - user still created but without role
            
            logger.info(f"Admin account created: {user.username}")
            return user
        
        except Exception as e:
            logger.error(f"Error creating admin account: {str(e)}")
            raise
    
    def list_users(self, search: str = None, department_id: str = None, status: str = None) -> List:
        """
        List all user profiles with search and filters (Admin only).
        
        Business Logic:
        1. Validate filters
        2. Fetch profiles from repository with filters
        3. Return list of profiles
        
        Args:
            search: Search query (username, email, full_name)
            department_id: Filter by department UUID
            status: Filter by account status (active, blocked, inactive)
        
        Returns:
            List of UserProfile objects
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Validate status filter if provided
            if status and status not in ['active', 'blocked', 'inactive']:
                raise ValidationError(f"Invalid status: {status}. Must be active, blocked, or inactive")
            
            # Fetch profiles via repository
            profiles = self.profile_repository.search_profiles(
                search=search,
                department_id=department_id,
                status=status
            )
            
            logger.info(f"Listed users. Filters: search={search}, dept={department_id}, status={status}")
            return profiles
        
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            raise
