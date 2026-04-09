#!/usr/bin/env python
"""Test script for 2 critical APIs"""

import os
import sys
import django
import requests
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/app')
django.setup()

from apps.users.models import Account, AccountRole, Role
from apps.operations.models import AuditLog

# ============================================================================
# TEST 1: CHECK DATABASE STATE
# ============================================================================
print("="*80)
print("TEST 1: CHECK DATABASE STATE")
print("="*80)

# Get users
admin = Account.objects.get(username='admin')
manager = Account.objects.get(username='manager2')

print(f"\n✅ Admin: {admin.id} | {admin.username} | {admin.email}")
print(f"✅ Manager: {manager.id} | {manager.username} | {manager.email}")

# Get roles
roles = Role.objects.filter(is_deleted=False).order_by('code')
print(f"\n✅ Available Roles ({roles.count()}):")
for role in roles[:5]:
    print(f"   - {role.code:20} | {role.name:30} | {role.id}")

# Get manager's current roles
manager_roles = manager.account_roles.filter(is_deleted=False)
print(f"\n✅ Manager's Current Roles ({manager_roles.count()}):")
if manager_roles.exists():
    for ar in manager_roles:
        print(f"   - {ar.role.code} | {ar.role.name}")
        print(f"     Role ID: {ar.role.id}")
        print(f"     Granted by: {ar.granted_by.username if ar.granted_by else 'N/A'}")
        print(f"     Created: {ar.created_at}")
else:
    print("   (No roles assigned)")

# Get non-admin roles for update test
available_for_swap = Role.objects.filter(is_deleted=False).exclude(code='admin').first()
print(f"\n✅ Can swap to role: {available_for_swap.code if available_for_swap else 'N/A'}")

# ============================================================================
# TEST 2: API TEST SETUP
# ============================================================================
print("\n" + "="*80)
print("TEST 2: API ENDPOINTS HEALTH CHECK")
print("="*80)

BASE_URL = "http://localhost:8000"
headers = {"Content-Type": "application/json"}

# Get token
print("\n🔐 Getting Auth Token...")
try:
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/login/",
        json={
            "username": "admin",
            "password": "Admin12345@"
        },
        headers=headers,
        timeout=5
    )
    if resp.status_code == 200:
        token = resp.json()['access_token']
        auth_headers = {**headers, "Authorization": f"Bearer {token}"}
        print(f"✅ Token obtained: {token[:50]}...")
    else:
        print(f"❌ Login failed: {resp.status_code}")
        print(resp.json())
        sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# ============================================================================
# TEST 3: UPDATE ROLE API
# ============================================================================
print("\n" + "="*80)
print("TEST 3: PUT /api/v1/accounts/{id}/roles/{role_id} - UPDATE ROLE")
print("="*80)

if manager_roles.exists():
    old_role = manager_roles.first().role
    print(f"\n📋 Test Setup:")
    print(f"   - Account: {manager.username} ({manager.id})")
    print(f"   - Current Role: {old_role.code}")
    print(f"   - Current Role ID: {old_role.id}")
    
    # Find a different role to swap to
    new_role = Role.objects.filter(is_deleted=False).exclude(id=old_role.id).first()
    if new_role:
        print(f"   - New Role: {new_role.code}")
        print(f"   - New Role ID: {new_role.id}")
        
        # Make the request
        url = f"{BASE_URL}/api/v1/accounts/{manager.id}/roles/{old_role.id}"
        payload = {
            "new_role_id": str(new_role.id),
            "notes": "Test update role API"
        }
        print(f"\n🔄 Calling: PUT {url}")
        print(f"   Payload: {json.dumps(payload, indent=2)}")
        
        try:
            resp = requests.put(url, json=payload, headers=auth_headers, timeout=10)
            print(f"\n   Status: {resp.status_code}")
            print(f"   Response: {json.dumps(resp.json(), indent=2)}")
            
            if resp.status_code == 200 or resp.status_code == 201:
                print("\n✅ API PASSED: Role update successful")
                
                # Verify in DB
                updated_roles = manager.account_roles.filter(is_deleted=False)
                print(f"\n   ✅ DB Verification: Manager now has {updated_roles.count()} roles")
                for ar in updated_roles:
                    print(f"      - {ar.role.code}")
            else:
                print("\n❌ API FAILED: Non-success status code")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    else:
        print("❌ No different role available to swap")
else:
    print("⚠️  Manager has no roles - skipping update test")

# ============================================================================
# TEST 4: FORGOT PASSWORD API
# ============================================================================
print("\n" + "="*80)
print("TEST 4: POST /api/v1/auth/forgot-password/ - FORGOT PASSWORD")
print("="*80)

test_user = Account.objects.get(username='admin')
print(f"\n📋 Test Setup:")
print(f"   - User: {test_user.username}")
print(f"   - Email: {test_user.email}")

url = f"{BASE_URL}/api/v1/auth/forgot-password/"
payload = {"email": test_user.email}

print(f"\n🔄 Calling: POST {url}")
print(f"   Payload: {json.dumps(payload)}")

try:
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    print(f"\n   Status: {resp.status_code}")
    print(f"   Response: {json.dumps(resp.json(), indent=2)}")
    
    if resp.status_code == 200:
        print("\n✅ API PASSED: Forgot-password endpoint returned 200")
        
        # Check if reset token was created
        from apps.users.password_reset import PasswordResetToken
        tokens = PasswordResetToken.objects.filter(account=test_user, is_used=False).order_by('-created_at')
        if tokens.exists():
            token = tokens.first()
            print(f"\n   ✅ DB Verification: Reset token created")
            print(f"      - Token: {token.token[:50]}...")
            print(f"      - Created: {token.created_at}")
            print(f"      - Expires: {token.expires_at}")
        else:
            print(f"\n   ⚠️  Reset token not found - may not have been created")
    else:
        print("\n❌ API FAILED: Non-success status code")
except Exception as e:
    print(f"\n❌ Error: {e}")

# ============================================================================
# FINAL VERDICT
# ============================================================================
print("\n" + "="*80)
print("FINAL VERDICT")
print("="*80)
print("""
✅ Both APIs have been tested
✅ Check output above for any ❌ marks

If all tests show ✅:
   → APIs are ready for production use
   → You can proceed with deployment

If any tests show ❌:
   → Review the error messages
   → Contact backend team for fixes
""")
