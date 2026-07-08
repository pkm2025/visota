"""Data migration: register PKM permissions and grant to admin/chief_accountant.

Creates the four PKM permission codes (pkm.access, pkm.notes.manage,
pkm.documents.manage, pkm.qa.use) and grants pkm.access plus fine-grained
PKM permissions to roles that have all-module access (admin,
chief_accountant). This ensures existing databases get the PKM permissions
without requiring a fresh seed_permissions run.
"""

from django.db import migrations

PKM_PERMISSIONS = [
    {
        "code": "pkm.access",
        "module": "pkm",
        "name": "Quản lý tri thức cá nhân",
        "description": "PKM - Notes, RAG documents, Q&A AI",
    },
    {
        "code": "pkm.notes.manage",
        "module": "pkm",
        "name": "Quản lý ghi chú",
        "description": "Tạo/sửa/xóa ghi chú cá nhân",
    },
    {
        "code": "pkm.documents.manage",
        "module": "pkm",
        "name": "Quản lý tài liệu",
        "description": "Upload/xử lý/xóa tài liệu RAG",
    },
    {
        "code": "pkm.qa.use",
        "module": "pkm",
        "name": "Sử dụng Q&A AI",
        "description": "Hỏi đáp AI với RAG",
    },
]

# Roles that should receive all PKM permissions (full-module-access roles)
PKM_FULL_ROLES = ["admin", "chief_accountant"]


def forwards(apps, schema_editor):
    Permission = apps.get_model("identity", "Permission")
    Role = apps.get_model("identity", "Role")

    # 1. Create or update PKM permissions
    perm_map = {}
    for perm_data in PKM_PERMISSIONS:
        perm, _ = Permission.objects.update_or_create(
            code=perm_data["code"],
            defaults={
                "module": perm_data["module"],
                "name": perm_data["name"],
                "description": perm_data["description"],
            },
        )
        perm_map[perm_data["code"]] = perm

    # 2. Grant all PKM permissions to full-access roles
    all_pkm_perms = list(perm_map.values())
    for role_code in PKM_FULL_ROLES:
        for role in Role.objects.filter(code=role_code):
            existing = set(role.permissions.values_list("code", flat=True))
            to_add = [p for p in all_pkm_perms if p.code not in existing]
            if to_add:
                role.permissions.add(*to_add)


def backwards(apps, schema_editor):
    Permission = apps.get_model("identity", "Permission")
    # Remove PKM permissions (M2M relationships auto-cleaned on delete)
    Permission.objects.filter(module="pkm").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0003_permission_role_usercompanyrole"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
