#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/app')
django.setup()

from apps.users.models import Account

username = os.environ.get("CHECK_PASSWORD_USERNAME", "admin").strip()
candidate = os.environ.get("CHECK_PASSWORD_CANDIDATE", "")
if not candidate or candidate.startswith("change-me-"):
    raise RuntimeError("Set CHECK_PASSWORD_CANDIDATE before running this diagnostic")

account = Account.objects.get(username=username)
result = account.check_password(candidate)
sys.stdout.write(f"Password matches account '{username}': {result}\n")
sys.stdout.flush()
