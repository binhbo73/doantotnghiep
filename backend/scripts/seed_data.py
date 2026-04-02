# Seed data script
# Usage: python manage.py shell < scripts/seed_data.py

from apps.users.models import Account

# Create test users
if not Account.objects.filter(username='test_user').exists():
    Account.objects.create_user(
        username='test_user',
        email='test@example.com',
        password='testpass123'
    )
    print("✅ Test user created")
