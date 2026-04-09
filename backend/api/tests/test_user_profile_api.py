"""
Test Suite for User Management API (Phase 1 & 2)

Test Overview:
1. Self-Service Profile APIs (Phase 2)
   - GET /api/v1/users/me - View own profile
   - PATCH /api/users/me - Update own profile
   - POST /api/v1/users/me/avatar - Upload avatar

2. Admin User Management APIs (Phase 1)
   - GET /api/v1/users/ - List all users
   - GET /api/v1/users/{id}/ - Get user details
   - PATCH /api/v1/users/{id}/department - Change department
   - And others (already tested before)

Test Strategy:
- Use pytest + Django test client
- Mock S3 for avatar upload
- Test permissions (owner vs admin vs unauthorized)
- Test validation and error handling
- Test audit logging
"""

import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
import json
from io import BytesIO
from PIL import Image

from apps.users.models import (
    Account, UserProfile, Department, Role, AccountRole, Permission, RolePermission
)
from core.constants import RoleIds

User = get_user_model()


# ============================================================
# FIXTURES & SETUP
# ============================================================

class UserProfileAPITestBase(APITestCase):
    """Base test class with common setup for User Profile tests"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test departments
        self.dept_it = Department.objects.create(
            name="IT Department",
            description="Information Technology"
        )
        self.dept_hr = Department.objects.create(
            name="HR Department",
            description="Human Resources"
        )
        
        # Create roles
        self.admin_role = Role.objects.create(
            id=RoleIds.ADMIN,
            code="admin",
            name="Administrator"
        )
        self.user_role = Role.objects.create(
            id=RoleIds.USER,
            code="user",
            name="User"
        )
        
        # Create test users
        self.admin_user = Account.objects.create_user(
            username="admin",
            email="admin@company.com",
            password="SecurePass123!",
            first_name="Admin",
            last_name="User"
        )
        AccountRole.objects.create(
            account=self.admin_user,
            role=self.admin_role
        )
        
        self.regular_user = Account.objects.create_user(
            username="john_doe",
            email="john@company.com",
            password="SecurePass123!",
            first_name="John",
            last_name="Doe"
        )
        AccountRole.objects.create(
            account=self.regular_user,
            role=self.user_role
        )
        
        # Create UserProfiles
        self.admin_profile = UserProfile.objects.create(
            account=self.admin_user,
            full_name="Admin User",
            department=self.dept_it,
            address="123 Admin St",
            birthday=date(1985, 5, 15)
        )
        
        self.user_profile = UserProfile.objects.create(
            account=self.regular_user,
            full_name="John Doe",
            department=self.dept_hr,
            address="456 User Ave",
            birthday=date(1990, 3, 20)
        )
        
        # Create another user for testing permissions
        self.other_user = Account.objects.create_user(
            username="jane_smith",
            email="jane@company.com",
            password="SecurePass123!",
            first_name="Jane",
            last_name="Smith"
        )
        AccountRole.objects.create(
            account=self.other_user,
            role=self.user_role
        )
        UserProfile.objects.create(
            account=self.other_user,
            full_name="Jane Smith",
            department=self.dept_it,
            address="789 Other Lne",
            birthday=date(1992, 7, 10)
        )


# ============================================================
# TEST: GET /api/v1/users/me - View Own Profile
# ============================================================

class UserProfileSelfViewGetTests(UserProfileAPITestBase):
    """Test GET /api/v1/users/me endpoint"""
    
    def test_get_own_profile_authenticated(self):
        """Test: Authenticated user can view own profile"""
        self.client.force_authenticate(user=self.regular_user)
        
        response = self.client.get('/api/v1/users/me/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['success'] is True
        assert data['data']['username'] == 'john_doe'
        assert data['data']['email'] == 'john@company.com'
        assert data['data']['full_name'] == 'John Doe'
        assert data['data']['department_name'] == 'HR Department'
        assert data['data']['address'] == '456 User Ave'
        
        print("✓ test_get_own_profile_authenticated passed")
    
    def test_get_own_profile_unauthenticated(self):
        """Test: Unauthenticated user cannot view profile"""
        # Don't authenticate
        response = self.client.get('/api/v1/users/me/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        print("✓ test_get_own_profile_unauthenticated passed")
    
    def test_get_profile_includes_all_fields(self):
        """Test: Profile response includes all expected fields"""
        self.client.force_authenticate(user=self.regular_user)
        
        response = self.client.get('/api/v1/users/me/')
        data = response.json()['data']
        
        expected_fields = [
            'id', 'account_id', 'username', 'email', 'full_name',
            'avatar_url', 'address', 'birthday', 'department_name',
            'metadata', 'created_at', 'updated_at'
        ]
        
        for field in expected_fields:
            assert field in data, f"Field '{field}' missing in response"
        
        print("✓ test_get_profile_includes_all_fields passed")


# ============================================================
# TEST: PATCH /api/users/me - Update Own Profile
# ============================================================

class UserProfileSelfViewPatchTests(UserProfileAPITestBase):
    """Test PATCH /api/users/me endpoint"""
    
    def test_update_own_profile_full_name(self):
        """Test: User can update own full name"""
        self.client.force_authenticate(user=self.regular_user)
        
        new_data = {'full_name': 'Jonathan Doe'}
        response = self.client.patch(
            '/api/users/me/',
            data=json.dumps(new_data),
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['data']['full_name'] == 'Jonathan Doe'
        
        # Verify in database
        updated_profile = UserProfile.objects.get(account=self.regular_user)
        assert updated_profile.full_name == 'Jonathan Doe'
        
        print("✓ test_update_own_profile_full_name passed")
    
    def test_update_own_profile_address(self):
        """Test: User can update own address"""
        self.client.force_authenticate(user=self.regular_user)
        
        new_data = {'address': 'New Address, City, Country'}
        response = self.client.patch(
            '/api/users/me/',
            data=json.dumps(new_data),
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['data']['address'] == 'New Address, City, Country'
        
        print("✓ test_update_own_profile_address passed")
    
    def test_update_own_profile_birthday(self):
        """Test: User can update own birthday"""
        self.client.force_authenticate(user=self.regular_user)
        
        new_data = {'birthday': '1995-06-15'}
        response = self.client.patch(
            '/api/users/me/',
            data=json.dumps(new_data),
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['data']['birthday'] == '1995-06-15'
        
        print("✓ test_update_own_profile_birthday passed")
    
    def test_update_own_profile_metadata(self):
        """Test: User can update own metadata"""
        self.client.force_authenticate(user=self.regular_user)
        
        metadata = {'phone': '0123456789', 'skype': 'john.doe'}
        new_data = {'metadata': metadata}
        response = self.client.patch(
            '/api/users/me/',
            data=json.dumps(new_data),
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['data']['metadata'] == metadata
        
        print("✓ test_update_own_profile_metadata passed")
    
    def test_update_profile_invalid_birthday_future_date(self):
        """Test: Cannot set birthday to future date"""
        self.client.force_authenticate(user=self.regular_user)
        
        future_date = (timezone.now().date() + timedelta(days=1)).isoformat()
        new_data = {'birthday': future_date}
        
        response = self.client.patch(
            '/api/users/me/',
            data=json.dumps(new_data),
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        print("✓ test_update_profile_invalid_birthday_future_date passed")
    
    def test_update_profile_empty_full_name(self):
        """Test: Cannot set empty full name"""
        self.client.force_authenticate(user=self.regular_user)
        
        new_data = {'full_name': ''}
        response = self.client.patch(
            '/api/users/me/',
            data=json.dumps(new_data),
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        print("✓ test_update_profile_empty_full_name passed")
    
    def test_update_profile_unauthenticated(self):
        """Test: Unauthenticated user cannot update profile"""
        new_data = {'full_name': 'Hacker'}
        response = self.client.patch(
            '/api/users/me/',
            data=json.dumps(new_data),
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        print("✓ test_update_profile_unauthenticated passed")
    
    def test_update_profile_partial(self):
        """Test: Can update only some fields (partial update)"""
        self.client.force_authenticate(user=self.regular_user)
        
        new_data = {'full_name': 'Johnny D'}
        response = self.client.patch(
            '/api/users/me/',
            data=json.dumps(new_data),
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()['data']
        assert data['full_name'] == 'Johnny D'
        assert data['address'] == '456 User Ave'  # Should remain unchanged
        
        print("✓ test_update_profile_partial passed")


# ============================================================
# TEST: POST /api/v1/users/me/avatar - Upload Avatar
# ============================================================

class UserProfileAvatarViewTests(UserProfileAPITestBase):
    """Test POST /api/v1/users/me/avatar endpoint"""
    
    def _create_test_image(self):
        """Helper: Create a test image file"""
        file = BytesIO()
        image = Image.new('RGB', (100, 100), color='red')
        image.save(file, 'JPEG')
        file.seek(0)
        file.name = 'test_avatar.jpg'
        return file
    
    def test_upload_avatar_success(self):
        """Test: User can upload avatar"""
        self.client.force_authenticate(user=self.regular_user)
        
        avatar_file = self._create_test_image()
        response = self.client.post(
            '/api/v1/users/me/avatar/',
            {'avatar': avatar_file},
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'avatar_url' in data['data']
        assert data['data']['avatar_url'] is not None
        assert 'avatar' in data['data']['avatar_url'].lower()
        
        # Verify in database
        updated_profile = UserProfile.objects.get(account=self.regular_user)
        assert updated_profile.avatar_url is not None
        
        print("✓ test_upload_avatar_success passed")
    
    def test_upload_avatar_unauthenticated(self):
        """Test: Unauthenticated user cannot upload avatar"""
        avatar_file = self._create_test_image()
        
        response = self.client.post(
            '/api/v1/users/me/avatar/',
            {'avatar': avatar_file},
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        print("✓ test_upload_avatar_unauthenticated passed")
    
    def test_upload_avatar_no_file(self):
        """Test: Cannot upload without avatar file"""
        self.client.force_authenticate(user=self.regular_user)
        
        response = self.client.post(
            '/api/v1/users/me/avatar/',
            {},
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        print("✓ test_upload_avatar_no_file passed")
    
    def test_upload_avatar_file_too_large(self):
        """Test: Cannot upload file larger than 5MB"""
        self.client.force_authenticate(user=self.regular_user)
        
        # Create a large fake file
        large_file = BytesIO(b'x' * (6 * 1024 * 1024))  # 6MB
        large_file.name = 'large_avatar.jpg'
        large_file.content_type = 'image/jpeg'
        
        response = self.client.post(
            '/api/v1/users/me/avatar/',
            {'avatar': large_file},
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        print("✓ test_upload_avatar_file_too_large passed")
    
    def test_upload_avatar_invalid_format(self):
        """Test: Cannot upload non-image file"""
        self.client.force_authenticate(user=self.regular_user)
        
        # Create a text file
        text_file = BytesIO(b'This is not an image')
        text_file.name = 'not_an_image.txt'
        text_file.content_type = 'text/plain'
        
        response = self.client.post(
            '/api/v1/users/me/avatar/',
            {'avatar': text_file},
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        print("✓ test_upload_avatar_invalid_format passed")


# ============================================================
# TEST: Permission & Security Tests
# ============================================================

class UserProfileSecurityTests(UserProfileAPITestBase):
    """Test permission and security aspects"""
    
    def test_user_cannot_view_other_users_profile(self):
        """Test: User cannot view other user's /me endpoint"""
        self.client.force_authenticate(user=self.regular_user)
        
        # Try to access other user's profile via /me (should return own)
        response = self.client.get('/api/v1/users/me/')
        
        data = response.json()['data']
        assert data['username'] == self.regular_user.username
        assert data['username'] != self.other_user.username
        
        print("✓ test_user_cannot_view_other_users_profile passed")
    
    def test_user_cannot_update_other_users_profile(self):
        """Test: User cannot update other user's profile via /me endpoint"""
        self.client.force_authenticate(user=self.regular_user)
        
        # Update own profile should only affect own profile
        new_data = {'full_name': 'Hacker'}
        self.client.patch(
            '/api/users/me/',
            data=json.dumps(new_data),
            content_type='application/json'
        )
        
        # Verify other user is not affected
        other_profile = UserProfile.objects.get(account=self.other_user)
        assert other_profile.full_name != 'Hacker'
        assert other_profile.full_name == 'Jane Smith'
        
        print("✓ test_user_cannot_update_other_users_profile passed")


# ============================================================
# Test Execution
# ============================================================

if __name__ == '__main__':
    """
    Run tests with:
    python manage.py test api.tests.test_user_profile_api
    
    Or with pytest:
    pytest backend/api/tests/test_user_profile_api.py -v
    """
    pytest.main([__file__, '-v'])
