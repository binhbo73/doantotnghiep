"""
Extended Seed Data Script - Add Sub-departments, Additional Roles & Employees
Usage: python manage.py shell < scripts/seed_extended_data.py
OR: docker-compose exec backend python manage.py shell < scripts/seed_extended_data.py

This script adds:
1. Additional Roles (Senior Developer, Junior Developer, HR Officer, Sales Officer, Accountant)
2. Sub-departments under existing departments
3. More employees with proper role assignments
"""

from apps.users.models import Account, Role, Permission, RolePermission, AccountRole, Department, UserProfile
from django.utils import timezone
import uuid

print("\n" + "=" * 80)
print("📊 EXTENDED DATABASE SEEDING - SUB-DEPARTMENTS & ADDITIONAL EMPLOYEES")
print("=" * 80)

# Get existing roles (only use: admin, manager, user)
from apps.users.models import Role as RoleModel
user_role = RoleModel.objects.filter(code='user', is_deleted=False).first()
manager_role = RoleModel.objects.filter(code='manager', is_deleted=False).first()

print("\n✓ Using existing roles: admin, manager, user")

# ============================================================================
# 1. CREATE SUB-DEPARTMENTS
# ============================================================================
print("\n🏢 [STEP 1/2] CREATING SUB-DEPARTMENTS...")

# Get existing parent departments
from apps.users.models import Department as DeptModel
parent_depts = {
    'Phòng IT': DeptModel.objects.filter(name='Phòng IT', is_deleted=False).first(),
    'Phòng HR': DeptModel.objects.filter(name='Phòng HR', is_deleted=False).first(),
    'Phòng Kinh doanh': DeptModel.objects.filter(name='Phòng Kinh doanh', is_deleted=False).first(),
}

sub_departments_data = [
    # IT Department Sub-departments
    {
        'name': 'Team Backend',
        'description': 'Backend development team',
        'parent': 'Phòng IT'
    },
    {
        'name': 'Team Frontend',
        'description': 'Frontend development team',
        'parent': 'Phòng IT'
    },
    {
        'name': 'Team DevOps',
        'description': 'DevOps and infrastructure team',
        'parent': 'Phòng IT'
    },
    {
        'name': 'Team Database',
        'description': 'Database administration and optimization',
        'parent': 'Phòng IT'
    },
    
    # HR Department Sub-departments
    {
        'name': 'Recruitment Team',
        'description': 'Recruitment and talent acquisition',
        'parent': 'Phòng HR'
    },
    {
        'name': 'Training & Development',
        'description': 'Employee training and development',
        'parent': 'Phòng HR'
    },
    {
        'name': 'Payroll & Benefits',
        'description': 'Payroll processing and benefits management',
        'parent': 'Phòng HR'
    },
    
    # Business Department Sub-departments
    {
        'name': 'Sales Team',
        'description': 'Sales and client acquisition',
        'parent': 'Phòng Kinh doanh'
    },
    {
        'name': 'Customer Success',
        'description': 'Customer support and success',
        'parent': 'Phòng Kinh doanh'
    },
]

created_sub_depts = {}
for dept_info in sub_departments_data:
    parent_name = dept_info.get('parent')
    parent = parent_depts.get(parent_name) if parent_name else None
    
    if not parent:
        print(f"  ⚠️  Skipped {dept_info['name']} - parent not found")
        continue
    
    dept, created = DeptModel.objects.get_or_create(
        name=dept_info['name'],
        defaults={
            'description': dept_info['description'],
            'parent': parent
        }
    )
    created_sub_depts[dept_info['name']] = dept
    status = "✅ Created" if created else "⚠️  Exists"
    print(f"  {status}: {dept.name} (Parent: {parent.name})")

# ============================================================================
# 2. CREATE ADDITIONAL EMPLOYEES
# ============================================================================
print("\n👤 [STEP 2/2] CREATING ADDITIONAL EMPLOYEES...")

new_employees = [
    # Team Backend - 3 employees
    {
        'username': 'backend_dev_1',
        'email': 'backend.dev1@example.com',
        'first_name': 'Ngô',
        'last_name': 'Minh Hùng',
        'password': 'dev123',
        'department': 'Team Backend',
        'status': 'active'
    },
    {
        'username': 'backend_dev_2',
        'email': 'backend.dev2@example.com',
        'first_name': 'Trần',
        'last_name': 'Văn Bảo',
        'password': 'dev123',
        'department': 'Team Backend',
        'status': 'active'
    },
    {
        'username': 'backend_dev_3',
        'email': 'backend.dev3@example.com',
        'first_name': 'Lê',
        'last_name': 'Quốc Huy',
        'password': 'dev123',
        'department': 'Team Backend',
        'status': 'active'
    },
    
    # Team Frontend - 3 employees
    {
        'username': 'frontend_dev_1',
        'email': 'frontend.dev1@example.com',
        'first_name': 'Phạm',
        'last_name': 'Thị Anh',
        'password': 'dev123',
        'department': 'Team Frontend',
        'status': 'active'
    },
    {
        'username': 'frontend_dev_2',
        'email': 'frontend.dev2@example.com',
        'first_name': 'Hoàng',
        'last_name': 'Duy Thanh',
        'password': 'dev123',
        'department': 'Team Frontend',
        'status': 'active'
    },
    {
        'username': 'frontend_dev_3',
        'email': 'frontend.dev3@example.com',
        'first_name': 'Vũ',
        'last_name': 'Minh Tuấn',
        'password': 'dev123',
        'department': 'Team Frontend',
        'status': 'active'
    },
    
    # Team DevOps - 2 employees
    {
        'username': 'devops_engineer_1',
        'email': 'devops.engineer1@example.com',
        'first_name': 'Đặng',
        'last_name': 'Công Vinh',
        'password': 'dev123',
        'department': 'Team DevOps',
        'status': 'active'
    },
    {
        'username': 'devops_engineer_2',
        'email': 'devops.engineer2@example.com',
        'first_name': 'Bùi',
        'last_name': 'Thanh Hải',
        'password': 'dev123',
        'department': 'Team DevOps',
        'status': 'active'
    },
    
    # Team Database - 2 employees
    {
        'username': 'dba_1',
        'email': 'dba.1@example.com',
        'first_name': 'Tô',
        'last_name': 'Ngọc Hùng',
        'password': 'dev123',
        'department': 'Team Database',
        'status': 'active'
    },
    {
        'username': 'dba_2',
        'email': 'dba.2@example.com',
        'first_name': 'Nguyễn',
        'last_name': 'Thái Phong',
        'password': 'dev123',
        'department': 'Team Database',
        'status': 'active'
    },
    
    # Recruitment Team - 2 employees
    {
        'username': 'recruiter_1',
        'email': 'recruiter.1@example.com',
        'first_name': 'Hoàng',
        'last_name': 'Thị Kim Dung',
        'password': 'hr123',
        'department': 'Recruitment Team',
        'status': 'active'
    },
    {
        'username': 'recruiter_2',
        'email': 'recruiter.2@example.com',
        'first_name': 'Trương',
        'last_name': 'Thúy Linh',
        'password': 'hr123',
        'department': 'Recruitment Team',
        'status': 'active'
    },
    
    # Training & Development - 2 employees
    {
        'username': 'trainer_1',
        'email': 'trainer.1@example.com',
        'first_name': 'Lý',
        'last_name': 'Minh Khoa',
        'password': 'hr123',
        'department': 'Training & Development',
        'status': 'active'
    },
    {
        'username': 'trainer_2',
        'email': 'trainer.2@example.com',
        'first_name': 'Cao',
        'last_name': 'Văn Tân',
        'password': 'hr123',
        'department': 'Training & Development',
        'status': 'active'
    },
    
    # Payroll & Benefits - 2 employees
    {
        'username': 'payroll_1',
        'email': 'payroll.1@example.com',
        'first_name': 'Tạ',
        'last_name': 'Văn Đức',
        'password': 'acc123',
        'department': 'Payroll & Benefits',
        'status': 'active'
    },
    {
        'username': 'payroll_2',
        'email': 'payroll.2@example.com',
        'first_name': 'Kiều',
        'last_name': 'Thị Hương',
        'password': 'acc123',
        'department': 'Payroll & Benefits',
        'status': 'active'
    },
    
    # Sales Team - 3 employees
    {
        'username': 'sales_1',
        'email': 'sales.1@example.com',
        'first_name': 'Mạc',
        'last_name': 'Mạnh Tiến',
        'password': 'sales123',
        'department': 'Sales Team',
        'status': 'active'
    },
    {
        'username': 'sales_2',
        'email': 'sales.2@example.com',
        'first_name': 'Vương',
        'last_name': 'Khánh Linh',
        'password': 'sales123',
        'department': 'Sales Team',
        'status': 'active'
    },
    {
        'username': 'sales_3',
        'email': 'sales.3@example.com',
        'first_name': 'Hồ',
        'last_name': 'Thị Hương',
        'password': 'sales123',
        'department': 'Sales Team',
        'status': 'active'
    },
    
    # Customer Success - 2 employees
    {
        'username': 'customer_success_1',
        'email': 'customer.success1@example.com',
        'first_name': 'Đinh',
        'last_name': 'Thị Hạnh',
        'password': 'support123',
        'department': 'Customer Success',
        'status': 'active'
    },
    {
        'username': 'customer_success_2',
        'email': 'customer.success2@example.com',
        'first_name': 'Lê',
        'last_name': 'Thanh Tuấn',
        'password': 'support123',
        'department': 'Customer Success',
        'status': 'active'
    },
]

from apps.users.models import Account as AccModel
created_accounts = {}
for emp_info in new_employees:
    account, created = AccModel.objects.get_or_create(
        username=emp_info['username'],
        defaults={
            'email': emp_info['email'],
            'first_name': emp_info['first_name'],
            'last_name': emp_info['last_name'],
            'status': emp_info['status'],
            'is_staff': False,
            'is_superuser': False,
        }
    )
    
    if created:
        account.set_password(emp_info['password'])
        account.save()
    
    created_accounts[emp_info['username']] = account
    
    # Assign department via UserProfile
    dept = created_sub_depts.get(emp_info['department'])
    if dept:
        user_profile, _ = UserProfile.objects.get_or_create(
            account=account,
            defaults={
                'full_name': f"{emp_info['first_name']} {emp_info['last_name']}",
                'department': dept
            }
        )
        if not created and user_profile.department != dept:
            user_profile.department = dept
            user_profile.save()
    
    # Assign roles
    if user_role:
        AccountRole.objects.get_or_create(
            account=account,
            role=user_role,
            defaults={'granted_by': account}
        )
    
    status = "✅ Created" if created else "⚠️  Exists"
    dept_name = emp_info['department']
    print(f"  {status}: {emp_info['username']:25} (User) [Dept: {dept_name}]")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("✅ EXTENDED SEEDING COMPLETE!")
print("=" * 80)

summary = {
    'Departments': DeptModel.objects.filter(is_deleted=False).count(),
    'Sub-Departments (New)': len(created_sub_depts),
    'Accounts': AccModel.objects.filter(is_deleted=False).count(),
    'Employees (New)': len(new_employees),
}

print("\n📊 DATABASE SUMMARY:")
for key, count in summary.items():
    print(f"  • {key}: {count}")

print("\n🏢 SUB-DEPARTMENTS CREATED:")
for dept_name in sorted(created_sub_depts.keys()):
    dept = created_sub_depts[dept_name]
    emp_count = UserProfile.objects.filter(department=dept, account__is_deleted=False).count()
    print(f"  • {dept_name} ({emp_count} employees)")

print("\n👥 NEW EMPLOYEES BY DEPARTMENT:")
dept_employees = {}
for emp_info in new_employees:
    dept_name = emp_info['department']
    if dept_name not in dept_employees:
        dept_employees[dept_name] = []
    dept_employees[dept_name].append(emp_info)

for dept_name in sorted(dept_employees.keys()):
    employees = dept_employees[dept_name]
    print(f"\n  📍 {dept_name}:")
    for emp in employees:
        print(f"     • {emp['first_name']} {emp['last_name']} - Pass: {emp['password']}")

print("\n" + "=" * 80)
print("🚀 READY FOR TESTING!")
print("=" * 80 + "\n")
