"""Seed module-level permissions and system roles.

Each business module gets a single <module>.access permission (module-level
granularity, per product decision 2026-06-20). Old CRUD permissions are
removed to keep the catalog clean.

PKM module additionally has fine-grained permissions (pkm.notes.manage,
pkm.documents.manage, pkm.qa.use) for feature-level access control.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Company
from apps.identity.models import Permission, Role

MODULE_PERMISSIONS = [
    ("master_data", "Danh mục hệ thống", "Hạng mục, sản phẩm, khách hàng, nhà cung cấp"),
    ("ledger", "Kế toán tổng hợp", "Phiếu kế toán, sổ cái, bút toán, khóa sổ"),
    ("sales", "Bán hàng", "Hóa đơn bán, khách hàng, công nợ phải thu"),
    ("purchasing", "Mua hàng", "Hóa đơn mua, nhà cung cấp, công nợ phải trả"),
    ("inventory", "Kho", "Nhập/xuất/tồn, phiếu kho, kiểm kê"),
    ("assets", "Tài sản cố định", "TSCĐ, khấu hao, thanh lý, điều chuyển"),
    ("hr", "Nhân sự", "Nhân viên, HĐLĐ, BHXH, phép năm"),
    ("payroll", "Tính lương", "Bảng lương, PIT, BHXH, quỹ lương"),
    ("reporting", "Báo cáo tài chính", "B01, B02, BCĐTK, VAT, TNCN, D62"),
    ("documents", "Tài liệu đính kèm", "Quản lý tệp đính kèm chứng từ/hợp đồng"),
    ("contracts", "Hợp đồng & biên bản", "Hợp đồng mua/bán/dịch vụ, biên bản, mẫu HĐ"),
    ("input_docs", "Chứng từ đầu vào", "Upload/OCR hóa đơn đầu vào"),
    ("recurring", "Bút toán định kỳ", "Khấu hao, phân bổ, định kỳ"),
    ("projects", "Quản lý dự án", "Dự án, giai đoạn, nguồn lực, tiến độ"),
    ("crm", "CRM", "Lead, opportunity, ticket, campaign"),
    ("treasury", "Quỹ tiền mặt", "Phiếu thu, phiếu chi, quỹ"),
    ("banking", "Ngân hàng & Đối soát", "Sao kê, đối soát giao dịch ngân hàng"),
    ("guarantees", "Bảo lãnh ngân hàng", "Bid bond, performance, advance payment"),
    ("loans", "Vay vốn ngân hàng", "Vay ngắn/dài hạn, lãi vay, tất toán"),
    ("bidding", "Đấu thầu", "Cơ hội đấu thầu, HSDT, kết quả theo Luật 23/2023"),
    ("budget", "Ngân sách & Dòng tiền", "Ngân sách năm, variance, cash flow forecast"),
    ("fx", "Tỷ giá & Định giá ngoại tệ", "Exchange rate, period-end revaluation"),
    ("einvoice", "Hóa đơn điện tử", "HĐĐT ND 254/2026 + TT 91/2026, XML/JSON, BC01/BC26"),
    ("approvals", "Phê duyệt", "Chuỗi duyệt phiếu/hóa đơn theo quy tắc"),
    ("notifications", "Thông báo", "Hộp thư thông báo hệ thống"),
    ("pkm", "Quản lý tri thức cá nhân", "PKM - Notes, RAG documents, Q&A AI"),
]

# Fine-grained permissions for the PKM module (beyond the standard .access).
# These enable feature-level checks within the PKM module.
PKM_FINE_GRAINED_PERMISSIONS = [
    ("pkm.notes.manage", "pkm", "Quản lý ghi chú", "Tạo/sửa/xóa ghi chú cá nhân"),
    ("pkm.documents.manage", "pkm", "Quản lý tài liệu", "Upload/xử lý/xóa tài liệu RAG"),
    ("pkm.qa.use", "pkm", "Sử dụng Q&A AI", "Hỏi đáp AI với RAG"),
]

# Permission codes that are intentionally NOT .access and must survive cleanup
FINE_GRAINED_CODES = {code for code, _, _, _ in PKM_FINE_GRAINED_PERMISSIONS}


SYSTEM_ROLES = [
    (
        "admin",
        "Quản trị hệ thống",
        "Toàn quyền truy cập mọi module",
        [m for m, _, _ in MODULE_PERMISSIONS],
        True,
    ),
    (
        "accountant",
        "Kế toán viên",
        "Kế toán tổng hợp + mua/bán + báo cáo + HĐ + nhân sự + HĐĐT + ngân hàng + FX",
        [
            "ledger",
            "sales",
            "purchasing",
            "reporting",
            "contracts",
            "documents",
            "hr",
            "payroll",
            "recurring",
            "master_data",
            "input_docs",
            "treasury",
            "einvoice",
            "approvals",
            "notifications",
            "banking",
            "guarantees",
            "loans",
            "fx",
        ],
        True,
    ),
    (
        "sales",
        "Nhân viên kinh doanh",
        "Bán hàng + CRM + khách hàng + hợp đồng + HĐĐT + đấu thầu",
        [
            "sales",
            "crm",
            "contracts",
            "documents",
            "projects",
            "master_data",
            "einvoice",
            "notifications",
            "bidding",
        ],
        True,
    ),
    (
        "chief_accountant",
        "Kế toán trưởng",
        "Toàn quyền kế toán + duyệt khóa sổ + HĐĐT + quản trị",
        [m for m, _, _ in MODULE_PERMISSIONS],
        True,
    ),
    (
        "purchaser",
        "Nhân viên mua hàng",
        "Mua hàng + nhà cung cấp + kho + thông báo",
        ["purchasing", "inventory", "documents", "master_data", "input_docs", "notifications"],
        True,
    ),
    (
        "hr_officer",
        "Nhân sự",
        "Quản lý nhân sự + HĐLĐ + BHXH + thông báo",
        ["hr", "payroll", "documents", "master_data", "reporting", "notifications"],
        True,
    ),
    (
        "project_manager",
        "Quản lý dự án",
        "Quản lý dự án + CRM + hợp đồng + báo cáo + thông báo",
        ["projects", "crm", "contracts", "documents", "sales", "reporting", "notifications"],
        True,
    ),
    (
        "viewer",
        "Chỉ xem",
        "Toàn quyền xem báo cáo, không ghi/sửa",
        ["reporting", "ledger", "notifications"],
        True,
    ),
]


class Command(BaseCommand):
    help = "Seed module-level permissions and system roles"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing non-system permissions before seeding",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        reset = options.get("reset", False)

        if reset:
            deleted_count, _ = Permission.objects.all().delete()
            self.stdout.write(f"  Reset: deleted {deleted_count} permission records")

        # 1. Upsert module permissions
        self.stdout.write("Seeding module permissions...")
        perm_map = {}
        for module, name_vi, desc in MODULE_PERMISSIONS:
            perm, created = Permission.objects.update_or_create(
                code=f"{module}.access",
                defaults={
                    "module": module,
                    "name": name_vi,
                    "description": desc,
                },
            )
            perm_map[module] = perm
            marker = "+" if created else "="
            self.stdout.write(f"  {marker} {perm.code}  ({name_vi})")

        # 1b. Upsert PKM fine-grained permissions
        self.stdout.write("Seeding PKM fine-grained permissions...")
        for code, module, name_vi, desc in PKM_FINE_GRAINED_PERMISSIONS:
            perm, created = Permission.objects.update_or_create(
                code=code,
                defaults={
                    "module": module,
                    "name": name_vi,
                    "description": desc,
                },
            )
            marker = "+" if created else "="
            self.stdout.write(f"  {marker} {perm.code}  ({name_vi})")

        # Clean up obsolete CRUD permissions from earlier seed
        # (preserve PKM fine-grained codes that don't end with .access)
        obsolete = Permission.objects.exclude(code__endswith=".access").exclude(
            code__in=FINE_GRAINED_CODES
        )
        obsolete_count = obsolete.count()
        if obsolete_count:
            obsolete.delete()
            self.stdout.write(f"  Removed {obsolete_count} obsolete CRUD permission(s)")

        # 2. Upsert system roles + assign permissions
        self.stdout.write("")
        self.stdout.write("Seeding system roles...")
        company = Company.objects.first()

        # Build a lookup for fine-grained permission objects by code
        fine_grained_perms = {
            p.code: p for p in Permission.objects.filter(code__in=FINE_GRAINED_CODES)
        }

        # Modules that include pkm get the fine-grained PKM permissions too
        pkm_fine_codes = [code for code, _, _, _ in PKM_FINE_GRAINED_PERMISSIONS]

        for code, name_vi, desc, modules, is_system in SYSTEM_ROLES:
            role, created = Role.objects.update_or_create(
                code=code,
                company=company,
                defaults={
                    "name": name_vi,
                    "description": desc,
                    "is_system": is_system,
                },
            )
            perms = [perm_map[m] for m in modules]
            if "pkm" in modules:
                perms.extend(
                    fine_grained_perms[c] for c in pkm_fine_codes if c in fine_grained_perms
                )
            role.permissions.set(perms)
            marker = "+" if created else "="
            self.stdout.write(
                f"  {marker} {role.code:<18} ({role.name}) — {len(modules)} module(s)"
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {len(MODULE_PERMISSIONS)} permissions, {len(SYSTEM_ROLES)} roles"
            )
        )
