# -*- coding: utf-8 -*-
"""
Seed production-like organization data for ABC Corp internal documents.

Usage:
    python manage.py shell < scripts/seed_production_data.py

Docker example:
    docker compose exec -T backend python manage.py shell < scripts/seed_production_data.py

What this script does:
    - Uses the existing admin account.
    - Uses existing roles: admin, manager, user.
    - Creates 4 main departments plus operational sub-departments.
    - Creates 1 manager + 3 users for each main department.
    - Creates 1 manager + 2 users for each sub-department.
    - Resets document/folder data so documents can be uploaded manually later.
    - Deletes old non-seeded accounts and user profiles.
    - Seeds folders only, matching tai-lieu-noi-bo logic.

What this script does NOT do:
    - It does not seed the admin account.
    - It does not seed roles.
    - It does not seed documents.
    - It does not change existing role permissions.
    - It does not clear external vector stores such as Qdrant.
"""

import os
import django

from django.db import transaction


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()


from apps.documents.models import (  # noqa: E402
    Document,
    DocumentAsset,
    DocumentChunk,
    DocumentEmbedding,
    DocumentPermission,
    Folder,
    FolderPermission,
)
from apps.operations.models import (  # noqa: E402
    AsyncTask,
    Conversation,
    ConversationAttachedDocument,
    ConversationAttachedFolder,
    HumanFeedback,
    Message,
    UserDocumentCache,
)
from apps.users.models import Account, AccountRole, Department, Role, UserProfile  # noqa: E402


RESET_DATA = os.getenv("SEED_RESET_DATA", "1") == "1"

ADMIN_USERNAME = os.getenv("SEED_ADMIN_USERNAME", "admin_tong")

MANAGER_PASSWORD = os.getenv("SEED_MANAGER_PASSWORD", "Manager@123456")
USER_PASSWORD = os.getenv("SEED_USER_PASSWORD", "User@123456")


DEPARTMENTS = [
    {
        "code": "ban-giam-doc",
        "name": "Ban Giám đốc",
        "description": "Bộ phận điều hành và phê duyệt cấp công ty.",
        "manager_username": "manager_bgd",
        "parent_code": None,
    },
    {
        "code": "hanh-chinh-tong-hop",
        "name": "Phòng Hành chính - Tổng hợp",
        "description": "Quản trị hành chính, nhân sự, tài sản và văn thư lưu trữ.",
        "manager_username": "manager_hcth",
        "parent_code": None,
    },
    {
        "code": "hanh-chinh-nhan-su",
        "name": "Nhân sự",
        "description": "Tuyển dụng, đào tạo, bổ nhiệm, điều chuyển, đánh giá và phúc lợi nhân sự.",
        "manager_username": "manager_hcns",
        "parent_code": "hanh-chinh-tong-hop",
    },
    {
        "code": "hanh-chinh-van-thu-luu-tru",
        "name": "Văn thư - Lưu trữ",
        "description": "Văn thư, lưu trữ, kiểm soát hồ sơ và thể thức tài liệu.",
        "manager_username": "manager_hcvt",
        "parent_code": "hanh-chinh-tong-hop",
    },
    {
        "code": "hanh-chinh-tai-san-hau-can",
        "name": "Tài sản - Hậu cần",
        "description": "Quản lý tài sản, công cụ, thiết bị, nhà ăn, xe và hậu cần nội bộ.",
        "manager_username": "manager_hcts",
        "parent_code": "hanh-chinh-tong-hop",
    },
    {
        "code": "ky-thuat-kinh-te",
        "name": "Phòng Kỹ thuật - Kinh tế",
        "description": "Quản lý kỹ thuật, dự án, chất lượng, tiến độ và an toàn.",
        "manager_username": "manager_ktkt",
        "parent_code": None,
    },
    {
        "code": "ky-thuat-quan-ly-du-an",
        "name": "Quản lý dự án",
        "description": "Quy trình dự án, tiến độ, hồ sơ dự án và bàn giao.",
        "manager_username": "manager_ktda",
        "parent_code": "ky-thuat-kinh-te",
    },
    {
        "code": "ky-thuat-chat-luong-an-toan",
        "name": "Chất lượng - An toàn",
        "description": "Chất lượng, an toàn, nghiệm thu, kiểm soát lỗi và KPI kỹ thuật.",
        "manager_username": "manager_ktcl",
        "parent_code": "ky-thuat-kinh-te",
    },
    {
        "code": "ky-thuat-du-toan-kinh-te",
        "name": "Dự toán - Kinh tế",
        "description": "Dự toán, định mức, chi phí, hiệu quả kinh tế và hồ sơ kinh tế kỹ thuật.",
        "manager_username": "manager_ktdt",
        "parent_code": "ky-thuat-kinh-te",
    },
    {
        "code": "tai-chinh-ke-toan",
        "name": "Phòng Tài chính - Kế toán",
        "description": "Quản lý tài chính, kế toán, thanh toán, công nợ và lương.",
        "manager_username": "manager_tckt",
        "parent_code": None,
    },
    {
        "code": "tai-chinh-ke-toan-thanh-toan",
        "name": "Kế toán thanh toán",
        "description": "Thanh toán, tạm ứng, hoàn ứng, công tác phí và chi phí nội bộ.",
        "manager_username": "manager_tctt",
        "parent_code": "tai-chinh-ke-toan",
    },
    {
        "code": "tai-chinh-ke-toan-cong-no",
        "name": "Kế toán công nợ",
        "description": "Theo dõi, đối chiếu, thu hồi và báo cáo công nợ.",
        "manager_username": "manager_tccn",
        "parent_code": "tai-chinh-ke-toan",
    },
    {
        "code": "tai-chinh-luong-phuc-loi",
        "name": "Lương - Phúc lợi",
        "description": "Tính lương, nâng lương, tăng lương, thưởng, KPI và phúc lợi tài chính.",
        "manager_username": "manager_tclpl",
        "parent_code": "tai-chinh-ke-toan",
    },
]


MAIN_DEPARTMENT_CODES = [
    "ban-giam-doc",
    "hanh-chinh-tong-hop",
    "ky-thuat-kinh-te",
    "tai-chinh-ke-toan",
]


SUB_DEPARTMENT_USER_PREFIXES = {
    "hanh-chinh-nhan-su": "hcns",
    "hanh-chinh-van-thu-luu-tru": "hcvt",
    "hanh-chinh-tai-san-hau-can": "hcts",
    "ky-thuat-quan-ly-du-an": "ktda",
    "ky-thuat-chat-luong-an-toan": "ktcl",
    "ky-thuat-du-toan-kinh-te": "ktdt",
    "tai-chinh-ke-toan-thanh-toan": "tctt",
    "tai-chinh-ke-toan-cong-no": "tccn",
    "tai-chinh-luong-phuc-loi": "tclpl",
}


USERS = [
    {
        "username": "manager_bgd",
        "email": "manager.bgd@abc-corp.local",
        "first_name": "Trưởng ban",
        "last_name": "Giám đốc",
        "full_name": "Trưởng ban Giám đốc",
        "department_code": "ban-giam-doc",
        "role": "manager",
        "password": MANAGER_PASSWORD,
    },
    {
        "username": "manager_hcth",
        "email": "manager.hcth@abc-corp.local",
        "first_name": "Trưởng phòng",
        "last_name": "Hành chính",
        "full_name": "Trưởng phòng Hành chính - Tổng hợp",
        "department_code": "hanh-chinh-tong-hop",
        "role": "manager",
        "password": MANAGER_PASSWORD,
    },
    {
        "username": "manager_ktkt",
        "email": "manager.ktkt@abc-corp.local",
        "first_name": "Trưởng phòng",
        "last_name": "Kỹ thuật",
        "full_name": "Trưởng phòng Kỹ thuật - Kinh tế",
        "department_code": "ky-thuat-kinh-te",
        "role": "manager",
        "password": MANAGER_PASSWORD,
    },
    {
        "username": "manager_tckt",
        "email": "manager.tckt@abc-corp.local",
        "first_name": "Trưởng phòng",
        "last_name": "Tài chính",
        "full_name": "Trưởng phòng Tài chính - Kế toán",
        "department_code": "tai-chinh-ke-toan",
        "role": "manager",
        "password": MANAGER_PASSWORD,
    },
]


for dept in [item for item in DEPARTMENTS if item["code"] in SUB_DEPARTMENT_USER_PREFIXES]:
    manager_username = dept["manager_username"]

    USERS.append(
        {
            "username": manager_username,
            "email": f"{manager_username.replace('_', '.')}@abc-corp.local",
            "first_name": "Trưởng bộ phận",
            "last_name": dept["name"],
            "full_name": f"Trưởng bộ phận {dept['name']}",
            "department_code": dept["code"],
            "role": "manager",
            "password": MANAGER_PASSWORD,
        }
    )


for dept in [item for item in DEPARTMENTS if item["code"] in MAIN_DEPARTMENT_CODES]:
    username_prefix = {
        "ban-giam-doc": "bgd",
        "hanh-chinh-tong-hop": "hcth",
        "ky-thuat-kinh-te": "ktkt",
        "tai-chinh-ke-toan": "tckt",
    }[dept["code"]]

    display_prefix = {
        "ban-giam-doc": "Ban Giám đốc",
        "hanh-chinh-tong-hop": "Hành chính - Tổng hợp",
        "ky-thuat-kinh-te": "Kỹ thuật - Kinh tế",
        "tai-chinh-ke-toan": "Tài chính - Kế toán",
    }[dept["code"]]

    for index in range(1, 4):
        USERS.append(
            {
                "username": f"user_{username_prefix}_{index}",
                "email": f"user.{username_prefix}.{index}@abc-corp.local",
                "first_name": "Nhân viên",
                "last_name": f"{display_prefix} {index}",
                "full_name": f"Nhân viên {display_prefix} {index}",
                "department_code": dept["code"],
                "role": "user",
                "password": USER_PASSWORD,
            }
        )


for dept in [item for item in DEPARTMENTS if item["code"] in SUB_DEPARTMENT_USER_PREFIXES]:
    username_prefix = SUB_DEPARTMENT_USER_PREFIXES[dept["code"]]

    for index in range(1, 3):
        USERS.append(
            {
                "username": f"user_{username_prefix}_{index}",
                "email": f"user.{username_prefix}.{index}@abc-corp.local",
                "first_name": "Nhân viên",
                "last_name": f"{dept['name']} {index}",
                "full_name": f"Nhân viên {dept['name']} {index}",
                "department_code": dept["code"],
                "role": "user",
                "password": USER_PASSWORD,
            }
        )


FOLDER_TREE = [
    {
        "name": "0-TAI-LIEU-CHUNG-CUA-TAT-CA-CAC-PHONG-BAN",
        "department_code": None,
        "access_scope": "company",
        "children": [
            {
                "name": "01-NHUNG-QUY-DINH-CHUNG",
                "children": [
                    {"name": "01-01-QUY-DINH-NOI-QUY"},
                    {"name": "01-03-BAO-MAT-THONG-TIN"},
                    {"name": "01-04-AN-TOAN-LAO-DONG"},
                    {"name": "01-05-KY-LUAT-LAO-DONG"},
                ],
            },
            {"name": "05-MAU-BIEU-CHUNG"},
            {"name": "06-KE-HOACH-TRIEN-KHAI"},
        ],
    },
    {
        "name": "1-BAN-GIAM-DOC",
        "department_code": "ban-giam-doc",
        "access_scope": "department",
        "children": [
            {"name": "01-QUY-CHE"},
            {"name": "02-QUYET-DINH"},
            {"name": "03-KPI-LUONG"},
            {
                "name": "TAI-LIEU-HO-TRO",
                "children": [
                    {"name": "01-VAI-TRO-TRACH-NHIEM-CAP-QUAN-LY"},
                ],
            },
        ],
    },
    {
        "name": "2-PHONG-HANH-CHINH-TONG-HOP",
        "department_code": "hanh-chinh-tong-hop",
        "access_scope": "department",
        "children": [
            {"name": "01-QUY-CHE"},
            {"name": "02-QUY-TRINH-PHOI-HOP-NOI-BO"},
            {"name": "TAI-LIEU-HO-TRO-CHUNG"},
        ],
    },
    {
        "name": "2.1-NHAN-SU",
        "department_code": "hanh-chinh-nhan-su",
        "access_scope": "department",
        "children": [
            {"name": "01-QUY-CHE-NHAN-SU"},
            {"name": "02-TUYEN-DUNG-BO-NHIEM-DIEU-CHUYEN"},
            {"name": "03-PHUC-LOI-KHEN-THUONG"},
            {"name": "04-DANH-GIA-CONG-VIEC-HO-SO-LUONG"},
            {"name": "TAI-LIEU-HO-TRO"},
        ],
    },
    {
        "name": "2.2-VAN-THU-LUU-TRU",
        "department_code": "hanh-chinh-van-thu-luu-tru",
        "access_scope": "department",
        "children": [
            {"name": "01-QUY-CHE-VAN-THU-LUU-TRU"},
            {"name": "02-CONG-VAN-DI-DEN"},
            {"name": "03-KIEM-SOAT-TAI-LIEU"},
            {"name": "TAI-LIEU-HO-TRO"},
        ],
    },
    {
        "name": "2.3-TAI-SAN-HAU-CAN",
        "department_code": "hanh-chinh-tai-san-hau-can",
        "access_scope": "department",
        "children": [
            {"name": "01-QUAN-LY-TAI-SAN-CONG-CU"},
            {"name": "02-QUAN-LY-NHA-AN"},
            {"name": "03-HAU-CAN-XE-THIET-BI"},
            {"name": "TAI-LIEU-HO-TRO"},
        ],
    },
    {
        "name": "3-PHONG-KY-THUAT-KINH-TE",
        "department_code": "ky-thuat-kinh-te",
        "access_scope": "department",
        "children": [
            {"name": "01-QUY-CHE"},
            {"name": "02-QUY-TRINH-PHOI-HOP-KY-THUAT"},
            {"name": "TAI-LIEU-HO-TRO-CHUNG"},
        ],
    },
    {
        "name": "3.1-QUAN-LY-DU-AN",
        "department_code": "ky-thuat-quan-ly-du-an",
        "access_scope": "department",
        "children": [
            {"name": "01-QUY-TRINH-DU-AN"},
            {"name": "02-HO-SO-DU-AN"},
            {"name": "03-TIEN-DO-BAN-GIAO"},
            {"name": "TAI-LIEU-HO-TRO"},
        ],
    },
    {
        "name": "3.2-CHAT-LUONG-AN-TOAN",
        "department_code": "ky-thuat-chat-luong-an-toan",
        "access_scope": "department",
        "children": [
            {"name": "01-CHAT-LUONG-KPI"},
            {"name": "02-AN-TOAN-LAO-DONG"},
            {"name": "03-NGHIEM-THU-KIEM-SOAT-LOI"},
            {"name": "TAI-LIEU-HO-TRO"},
        ],
    },
    {
        "name": "3.3-DU-TOAN-KINH-TE",
        "department_code": "ky-thuat-du-toan-kinh-te",
        "access_scope": "department",
        "children": [
            {"name": "01-DU-TOAN-KINH-TE"},
            {"name": "02-DINH-MUC-CHI-PHI"},
            {"name": "03-HO-SO-KINH-TE-KY-THUAT"},
            {"name": "TAI-LIEU-HO-TRO"},
        ],
    },
    {
        "name": "4-PHONG-TAI-CHINH-KE-TOAN",
        "department_code": "tai-chinh-ke-toan",
        "access_scope": "department",
        "children": [
            {"name": "01-QUY-CHE"},
            {"name": "02-QUY-TRINH-PHOI-HOP-TAI-CHINH"},
            {"name": "TAI-LIEU-HO-TRO-CHUNG"},
        ],
    },
    {
        "name": "4.1-KE-TOAN-THANH-TOAN",
        "department_code": "tai-chinh-ke-toan-thanh-toan",
        "access_scope": "department",
        "children": [
            {"name": "01-QUY-TRINH-THANH-TOAN"},
            {"name": "02-TAM-UNG-HOAN-UNG"},
            {"name": "03-THANH-TOAN-CONG-TAC-PHI"},
            {"name": "TAI-LIEU-HO-TRO"},
        ],
    },
    {
        "name": "4.2-KE-TOAN-CONG-NO",
        "department_code": "tai-chinh-ke-toan-cong-no",
        "access_scope": "department",
        "children": [
            {"name": "01-KE-TOAN-CONG-NO"},
            {"name": "02-DOI-CHIEU-CONG-NO"},
            {"name": "03-THU-HOI-BAO-CAO-CONG-NO"},
            {"name": "TAI-LIEU-HO-TRO"},
        ],
    },
    {
        "name": "4.3-LUONG-PHUC-LOI",
        "department_code": "tai-chinh-luong-phuc-loi",
        "access_scope": "department",
        "children": [
            {"name": "01-LUONG-KPI"},
            {"name": "02-LUONG-PHUC-LOI"},
            {"name": "03-THUONG-NANG-LUONG"},
            {"name": "TAI-LIEU-HO-TRO"},
        ],
    },
]


def get_or_restore(model, lookup, defaults=None):
    defaults = defaults or {}
    obj = model.objects.all_records().filter(**lookup).first()
    created = False

    if obj is None:
        data = {**lookup, **defaults}
        obj = model.objects.create(**data)
        created = True
    else:
        changed_fields = []
        if getattr(obj, "is_deleted", False):
            obj.is_deleted = False
            obj.deleted_at = None
            changed_fields.extend(["is_deleted", "deleted_at"])

        for field, value in defaults.items():
            if getattr(obj, field) != value:
                setattr(obj, field, value)
                changed_fields.append(field)

        if changed_fields:
            obj.save(update_fields=list(dict.fromkeys(changed_fields + ["updated_at"])))

    return obj, created


def reset_documents_and_folders():
    HumanFeedback.objects.all_records().hard_delete()
    Message.objects.all_records().hard_delete()
    ConversationAttachedDocument.objects.all_records().hard_delete()
    ConversationAttachedFolder.objects.all_records().hard_delete()
    Conversation.objects.all_records().hard_delete()
    AsyncTask.objects.all_records().hard_delete()
    DocumentEmbedding.objects.all_records().hard_delete()
    DocumentAsset.objects.all_records().hard_delete()
    DocumentPermission.objects.all_records().hard_delete()
    UserDocumentCache.objects.all_records().hard_delete()
    FolderPermission.objects.all_records().hard_delete()
    DocumentChunk.objects.all_records().hard_delete()
    Document.objects.all_records().hard_delete()
    Folder.objects.all_records().hard_delete()


def reset_accounts_and_departments(target_usernames):
    AccountRole.objects.all_records().exclude(account__username__in=target_usernames).hard_delete()
    UserProfile.objects.all_records().exclude(account__username__in=target_usernames).hard_delete()
    Account.objects.exclude(username__in=target_usernames).delete()
    Department.objects.all_records().hard_delete()


def load_existing_roles():
    roles = {}
    for code in ("admin", "manager", "user"):
        role = Role.objects.filter(code=code, is_deleted=False).first()
        if role is None:
            raise RuntimeError(
                f"Required role '{code}' does not exist. "
                "Create roles/permissions before running this seed."
            )
        roles[code] = role
        print(f"  ready role: {code}")
    return roles


def load_existing_admin():
    admin = Account.objects.filter(
        username=ADMIN_USERNAME,
        is_deleted=False,
        status="active",
    ).first()

    if admin is None:
        admin = Account.objects.filter(
            is_superuser=True,
            is_deleted=False,
            status="active",
        ).order_by("username").first()

    if admin is None:
        raise RuntimeError(
            "No active admin account found. "
            "Set SEED_ADMIN_USERNAME to an existing admin username."
        )

    admin_role = Role.objects.filter(code="admin", is_deleted=False).first()
    if admin_role and not AccountRole.objects.filter(
        account=admin,
        role=admin_role,
        is_deleted=False,
    ).exists():
        raise RuntimeError(
            f"Account '{admin.username}' exists but does not have the admin role."
        )

    print(f"  using existing admin: {admin.username} ({admin.email})")
    return admin


def seed_departments():
    departments = {}
    for item in DEPARTMENTS:
        dept, created = get_or_restore(
            Department,
            {"name": item["name"]},
            {
                "description": item["description"],
                "parent": None,
                "manager": None,
            },
        )
        departments[item["code"]] = dept
        print(f"  {'created' if created else 'ready'} department: {item['name']}")

    for item in DEPARTMENTS:
        parent_code = item.get("parent_code")
        parent = departments.get(parent_code) if parent_code else None
        dept = departments[item["code"]]
        if dept.parent_id != (parent.id if parent else None):
            dept.parent = parent
            dept.save(update_fields=["parent", "updated_at"])

    return departments


def ensure_account(user_data, departments, roles):
    role = roles[user_data["role"]]
    department = departments.get(user_data["department_code"])

    account = Account.objects.filter(username=user_data["username"]).first()
    created = False

    if account is None:
        account = Account(
            username=user_data["username"],
            email=user_data["email"],
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            status="active",
            is_active=True,
            is_staff=user_data.get("is_staff", False),
            is_superuser=user_data.get("is_superuser", False),
            is_deleted=False,
            deleted_at=None,
        )
        account.set_password(user_data["password"])
        account.save()
        created = True
    else:
        account.email = user_data["email"]
        account.first_name = user_data["first_name"]
        account.last_name = user_data["last_name"]
        account.status = "active"
        account.is_active = True
        account.is_staff = user_data.get("is_staff", False)
        account.is_superuser = user_data.get("is_superuser", False)
        account.is_deleted = False
        account.deleted_at = None
        account.set_password(user_data["password"])
        account.save()

    profile, _ = get_or_restore(
        UserProfile,
        {"account": account},
        {
            "full_name": user_data["full_name"],
            "department": department,
            "metadata": {
                "seeded_by": "seed_production_data",
                "role": user_data["role"],
            },
        },
    )
    if profile.department_id != (department.id if department else None):
        profile.department = department
        profile.save(update_fields=["department", "updated_at"])

    AccountRole.objects.all_records().filter(account=account).exclude(role=role).hard_delete()
    account_role, _ = get_or_restore(
        AccountRole,
        {"account": account, "role": role},
        {
            "granted_by": None,
            "notes": "Seeded by seed_production_data.py",
        },
    )

    return account, account_role, created


def assign_department_managers(departments, accounts_by_username):
    for item in DEPARTMENTS:
        manager_username = item.get("manager_username")
        if not manager_username:
            continue
        manager = accounts_by_username[manager_username]
        dept = departments[item["code"]]
        dept.manager = manager
        dept.save(update_fields=["manager", "updated_at"])
        dept.managers.set([manager])


def seed_folder_node(node, parent, inherited_department, inherited_scope, departments, admin_account):
    department_code = node.get("department_code", inherited_department)
    access_scope = node.get("access_scope", inherited_scope)
    department = departments.get(department_code) if department_code else None

    folder = Folder.objects.create(
        name=node["name"],
        parent=parent,
        department=department,
        access_scope=access_scope,
        description=node.get("description") or "",
        metadata={
            "seeded_by": "seed_production_data",
            "department_code": department_code,
        },
        created_by=admin_account,
    )

    for child in node.get("children", []):
        seed_folder_node(
            child,
            folder,
            department_code,
            access_scope,
            departments,
            admin_account,
        )

    return folder


def seed_folders(departments, admin_account):
    for root_node in FOLDER_TREE:
        seed_folder_node(
            root_node,
            parent=None,
            inherited_department=root_node.get("department_code"),
            inherited_scope=root_node.get("access_scope", "company"),
            departments=departments,
            admin_account=admin_account,
        )


def print_summary(admin_account):
    print("\nSeed summary")
    print("-" * 80)
    print(f"Departments: {Department.objects.filter(is_deleted=False).count()}")
    print(f"Accounts:    {Account.objects.filter(is_deleted=False).count()}")
    print(f"Profiles:    {UserProfile.objects.filter(is_deleted=False).count()}")
    print(f"Folders:     {Folder.objects.filter(is_deleted=False).count()}")
    print(f"Documents:   {Document.objects.filter(is_deleted=False).count()} (expected 0)")
    print("")
    print("Credentials")
    print("-" * 80)
    print(f"admin:           existing account '{admin_account.username}' (password unchanged)")
    print(f"manager default: <manager_username> / {MANAGER_PASSWORD}")
    print(f"user default:    <user_username> / {USER_PASSWORD}")
    print("")
    print("Manager usernames")
    print("-" * 80)
    for dept in DEPARTMENTS:
        manager_username = dept.get("manager_username")
        if manager_username:
            print(f"{dept['name']}: {manager_username}")


@transaction.atomic
def run():
    print("\n" + "=" * 80)
    print("ABC CORP PRODUCTION SEED")
    print("=" * 80)
    print(f"Reset data: {RESET_DATA}")

    print("\nLoading existing roles and admin...")
    roles = load_existing_roles()
    admin_account = load_existing_admin()
    target_usernames = {item["username"] for item in USERS}
    target_usernames.add(admin_account.username)

    if RESET_DATA:
        print("\nResetting old documents, folders, accounts and departments...")
        reset_documents_and_folders()
        reset_accounts_and_departments(target_usernames)

    print("\nSeeding departments...")
    departments = seed_departments()

    print("\nSeeding accounts...")
    accounts_by_username = {}
    for item in USERS:
        account, _, created = ensure_account(item, departments, roles)
        accounts_by_username[item["username"]] = account
        dept_label = item["department_code"] or "none"
        print(
            f"  {'created' if created else 'ready'} account: "
            f"{item['username']} | role={item['role']} | department={dept_label}"
        )

    assign_department_managers(departments, accounts_by_username)

    print("\nSeeding folders...")
    Folder.objects.all_records().hard_delete()
    seed_folders(departments, admin_account)

    print_summary(admin_account)
    print("\nDone. Upload documents manually into the seeded folders.")
    print("=" * 80 + "\n")


run()
