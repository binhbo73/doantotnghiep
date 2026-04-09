#!/usr/bin/env python
"""Test 2 critical APIs - UPDATE ROLE & FORGOT PASSWORD"""

import requests
import json
import os
import sys
import django

# Setup Django for DB queries
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/app')
django.setup()

from apps.users.models import Account, AccountRole, Role

# ============================================================================
# Get admin token (from curl test)
# ============================================================================
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc1NzIwNDA5LCJpYXQiOjE3NzU3MTk1MDksImp0aSI6ImM5MjYxZTlmMGI2MzQyMmM5M2FiMGM1NWZjMjRjZjUyIiwidXNlcl9pZCI6Ijg0YjgyZjUyLTM0NTAtNDVlNy1iNmY4LTAzYjMzMGI5MzY1NSJ9.ZAvHAiNtroHorgKchZiBVT1N3gR5N6QF-Bf0DH-_rbs"

BASE_URL = "http://localhost:8000"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}"
}

# ============================================================================
# TEST 1: UPDATE ROLE API
# ============================================================================
print("="*80)
print("TEST 1: PUT /api/v1/accounts/{id}/roles/{role_id} - UPDATE ROLE")
print("="*80)

# Get manager and their roles
manager = Account.objects.get(username='manager2')
manager_roles = manager.account_roles.filter(is_deleted=False)

if manager_roles.exists():
    old_role = manager_roles.first().role
    new_role = Role.objects.filter(is_deleted=False).exclude(id=old_role.id).first()
    
    if new_role:
        print(f"\n📋 Test Setup:")
        print(f"   Account: {manager.username} ({manager.id})")
        print(f"   Current Role: {old_role.code}")
        print(f"   New Role: {new_role.code}")
        
        url = f"{BASE_URL}/api/v1/accounts/{manager.id}/roles/{old_role.id}"
        payload = {
            "new_role_id": str(new_role.id),
            "notes": "Test update role"
        }
        
        print(f"\n🔄 REQUEST: PUT {url}")
        print(f"   Body: {json.dumps(payload)}")
        
        try:
            resp = requests.put(url, json=payload, headers=headers, timeout=10)
            print(f"\n📊 RESPONSE:")
            print(f"   Status: {resp.status_code}")
            
            if resp.status_code in [200, 201]:
                data = resp.json()
                print(f"   Message: {data.get('message', 'N/A')}")
                print(f"   Data: {json.dumps(data.get('data', {}), indent=6)}")
                print("\n✅ TEST PASSED: Update role successful (200/201)")
                
                # Verify in DB
                updated_roles = manager.account_roles.filter(is_deleted=False)
                print(f"\n   DB Verification: Manager now has {updated_roles.count()} roles:")
                for ar in updated_roles:
                    print(f"      - {ar.role.code}")
            else:
                print(f"   Error: {resp.text}")
                print("\n❌ TEST FAILED: Non-success status")
        except Exception as e:
            print(f"\n❌ ERROR: {e}")

# ============================================================================
# TEST 2: FORGOT PASSWORD API
# ============================================================================
print("\n" + "="*80)
print("TEST 2: POST /api/v1/auth/forgot-password/ - FORGOT PASSWORD")
print("="*80)

admin = Account.objects.get(username='admin')
print(f"\n📋 Test Setup:")
print(f"   User: {admin.username}")
print(f"   Email: {admin.email}")

url = f"{BASE_URL}/api/v1/auth/forgot-password/"
payload = {"email": admin.email}

print(f"\n🔄 REQUEST: POST {url}")
print(f"   Body: {json.dumps(payload)}")

try:
    # No auth needed for forgot-password
    resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
    print(f"\n📊 RESPONSE:")
    print(f"   Status: {resp.status_code}")
    
    data = resp.json()
    print(f"   Message: {data.get('message', 'N/A')}")
    
    if resp.status_code == 200:
        print("\n✅ TEST PASSED: Forgot-password returned 200")
        
        # Check if reset token was created
        from apps.users.password_reset import PasswordResetToken
        tokens = PasswordResetToken.objects.filter(account=admin, is_used=False).order_by('-created_at')
        if tokens.exists():
            token = tokens.first()
            print(f"\n   DB Verification: Reset token created")
            print(f"      - Token: {token.token[:50]}...")
            print(f"      - Created: {token.created_at}")
            print(f"      - Expires: {token.expires_at}")
            print(f"      - Is Used: {token.is_used}")
        else:
            print(f"\n   ⚠️  Reset token NOT found in DB")
    else:
        print(f"\n❌ TEST FAILED: Expected 200, got {resp.status_code}")
except Exception as e:
    print(f"\n❌ ERROR: {e}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*80)
print("FINAL VERDICT")
print("="*80)
print("""
✅ Both APIs tested
✅ Check above for any ❌ marks

STATUS:
  - Update Role API: Check response above
  - Forgot Password API: Check response above
  
If both show ✅:
  → Ready to handover to production
""")
