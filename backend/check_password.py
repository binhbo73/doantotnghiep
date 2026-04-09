#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/app')
django.setup()

from apps.users.models import Account

admin = Account.objects.get(username='admin')
print(f"Admin ID: {admin.id}")
print(f"Admin password hash: {admin.password[:50]}...")

# Try different passwords
test_passwords = ['admin123', 'Admin12345@', 'password', 'admin', '123456']
for pwd in test_passwords:
    result = admin.check_password(pwd)
    sys.stdout.write(f"  - '{pwd}': {result}\n")
    sys.stdout.flush()
