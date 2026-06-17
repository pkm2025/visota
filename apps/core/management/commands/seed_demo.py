"""Seed demo data: company + admin user + sample permissions."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.core.models import Company
from apps.identity.models import Permission, Role

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo data: company + admin user + sample permissions"

    def handle(self, *args, **options):
        # 1. Create demo company
        company, _ = Company.objects.update_or_create(
            code="PKM",
            defaults={
                "name": "CÔNG TY CỔ PHẦN CÔNG NGHỆ PKM",
                "tax_code": "0101218690",
                "address": "Tầng 06, Toà Nhà Icon4, Số 243A Đê La Thành, Hà Nội",
                "accounting_regime": "tt133",
            },
        )

        # Load TT133 chart of accounts
        from django.core.management import call_command

        call_command("load_tt133", company_code=company.code)
        self.stdout.write(f"Loaded TT133 chart for {company.code}")

        # 2. Create admin user
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@local.test",
                "full_name": "Administrator",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password("admin123")
            admin.save()
            self.stdout.write("Created admin user (password: admin123)")

        # 3. Create core permissions
        core_perms = [
            ("gl.voucher.view", "ledger", "View vouchers"),
            ("gl.voucher.create", "ledger", "Create voucher"),
            ("gl.voucher.edit", "ledger", "Edit voucher"),
            ("gl.voucher.delete", "ledger", "Delete voucher"),
            ("gl.voucher.post", "ledger", "Post voucher to ledger"),
            ("gl.voucher.lock", "ledger", "Lock voucher"),
            ("sales.invoice.view", "sales", "View sales invoices"),
            ("sales.invoice.create", "sales", "Create sales invoice"),
            ("purchase.invoice.view", "purchasing", "View purchase invoices"),
            ("purchase.invoice.create", "purchasing", "Create purchase invoice"),
            ("system.user.manage", "system", "Manage users"),
        ]
        for code, module, name in core_perms:
            Permission.objects.update_or_create(
                code=code,
                defaults={"module": module, "name": name},
            )

        # 4. Create accountant role for the demo company
        role, _ = Role.objects.update_or_create(
            company=company,
            code="accountant",
            defaults={"name": "Kế toán viên"},
        )
        gl_perms = Permission.objects.filter(module="ledger")
        role.permissions.set(gl_perms)

        # 5. Create sample master data
        from apps.master_data.models import Customer, Product, Vendor, Warehouse

        customer, _ = Customer.objects.update_or_create(
            company=company,
            code="KH001",
            defaults={
                "name": "Công ty ABC",
                "tax_code": "0101234567",
                "address": "Số 1 Đường A, Hà Nội",
                "phone": "0241234567",
                "payment_terms": "30 days",
            },
        )

        vendor, _ = Vendor.objects.update_or_create(
            company=company,
            code="NCC001",
            defaults={
                "name": "Nhà cung cấp XYZ",
                "tax_code": "0307654321",
                "address": "Số 2 Đường B, Hồ Chí Minh",
                "payment_terms": "15 days",
            },
        )

        product, _ = Product.objects.update_or_create(
            company=company,
            code="SP001",
            defaults={
                "name": "Sản phẩm demo",
                "product_type": "goods",
                "unit_id": "CAI",
                "gl_account_inv": "156",
                "gl_account_cogs": "632",
                "gl_account_revenue": "5111",
                "default_unit_price": 100000,
            },
        )

        warehouse, _ = Warehouse.objects.update_or_create(
            company=company,
            code="KHO_HN",
            defaults={
                "name": "Kho Hà Nội",
                "warehouse_type": "finished",
            },
        )

        self.stdout.write("Sample master data: 1 customer, 1 vendor, 1 product, 1 warehouse")

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete. Company: {company.code}, User: admin, "
                f"Permissions: {len(core_perms)}"
            )
        )
