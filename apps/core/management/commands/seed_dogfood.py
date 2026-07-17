"""Dogfooding seed: 3 companies (TT133, TT58 DNSN x2) with full data for internal testing.

Creates realistic multi-company, multi-regime test data:
  - 3 companies: 1 TT133 SME, 1 TT58 DNSN (Group 2), 1 TT58 HKD (Group 1)
  - 7 users per company (21 total), each with appropriate Role + UserCompanyRole
  - Master data per company: 3 customers, 3 vendors, 5 products, 2 employees, 1 project
  - TT133 transactions: 2 sales invoices, 1 purchase invoice, 3 GL vouchers (posted)
  - TT58 DNSN transactions: 2 DnsnVouchers (posted)
  - HR: 2 labor contracts + 1 calculated payroll run

Usage:
    python manage.py seed_dogfood
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Company
from apps.hr.models import (
    Department,
    Employee,
    LaborContract,
    Position,
)
from apps.identity.management.commands.seed_permissions import (
    MODULE_PERMISSIONS,
    SYSTEM_ROLES,
)
from apps.identity.models import Permission, Role, UserCompanyRole
from apps.ledger.models import AccountingVoucher, DnsnVoucher, VoucherLine
from apps.ledger.services import DnsnPostingService, VoucherPostingService
from apps.master_data.models import Customer, Product, Vendor
from apps.payroll.models import PayrollLine, PayrollRun
from apps.projects.models import Project
from apps.purchasing.models import PurchaseInvoice, PurchaseInvoiceLine
from apps.sales.models import SalesInvoice, SalesInvoiceLine

User = get_user_model()

PASSWORD = "dogfood123"

# ---------------------------------------------------------------------------
# Company / user configuration
# ---------------------------------------------------------------------------

COMPANY_CONFIGS = [
    {
        "code": "DF-SG",
        "prefix": "sg",
        "name": "Công ty TNHH Công nghệ Sài Gòn",
        "tax_code": "0301234567",
        "address": "45 Lê Lợi, Q.1, TP. HCM",
        "accounting_regime": "tt133",
        "sme_size": "small",
        "legal_representative": "Phạm Minh Tuấn",
        "chief_accountant": "Nguyễn Thị Mai",
        "industry": "Thương mại - Công nghệ",
    },
    {
        "code": "DF-HN",
        "prefix": "hn",
        "name": "Công ty CP Điện tử Hà Nội",
        "tax_code": "0107654321",
        "address": "88 Trần Duy Hưng, Cầu Giấy, Hà Nội",
        "accounting_regime": "tt58",
        "entity_type": "doanh_nghiep_sieu_nho",
        "vat_method": "ty_le_phan_tram",
        "tndn_method": "tinh_thue",
        "legal_representative": "Trần Văn Hùng",
        "industry": "Thương mại - Điện tử",
    },
    {
        "code": "DF-AB",
        "prefix": "ab",
        "name": "Doanh nghiệp siêu nhỏ An Bình",
        "tax_code": "0319876543",
        "address": "12 Nguyễn Trãi, Q.5, TP. HCM",
        "accounting_regime": "tt58",
        "entity_type": "ho_kinh_doanh",
        "vat_method": "ty_le_phan_tram",
        "tndn_method": "ty_le_phan_tram",
        "legal_representative": "Lê Thị Bình",
        "industry": "Dịch vụ - bán lẻ",
    },
]

# (suffix, role_code, role_name, full_name)
USER_SPECS = [
    ("admin", "admin", "Quản trị viên", "Quản trị hệ thống"),
    ("ketoantruong", "chief_accountant", "Kế toán trưởng", "Kế toán trưởng"),
    ("ketoan", "accountant", "Kế toán viên", "Kế toán viên"),
    ("sales", "sales", "Nhân viên bán hàng", "Nhân viên kinh doanh"),
    ("muahang", "purchaser", "Nhân viên mua hàng", "Nhân viên thu mua"),
    ("nhansu", "hr_officer", "Nhân sự", "Nhân viên nhân sự"),
    ("viewer", "viewer", "Người xem", "Chỉ xem"),
]

# Master-data name pools (deterministic so tests can assert)
CUSTOMER_NAMES = [
    ("KH001", "Công ty TNHH Thương mại Bình Minh"),
    ("KH002", "Công ty CP Dịch vụ Sao Mai"),
    ("KH003", "Cửa hàng Điện thoại Việt"),
]

VENDOR_NAMES = [
    ("NCC001", "Nhà cung cấp Vật tư Phương Nam"),
    ("NCC002", "Công ty TNHH Công nghệ Đông Dương"),
    ("NCC003", "Cửa hàng Linh kiện Đức"),
]

PRODUCT_SPECS = [
    ("SP001", "Laptop X1 Carbon", "goods", "CAI", "156", "632", "5111", 25000000),
    ("SP002", "Màn hình 27 inch", "goods", "CAI", "156", "632", "5111", 5500000),
    ("SP003", "Bàn phím cơ", "goods", "CAI", "156", "632", "5111", 1200000),
    ("DV001", "Sửa chữa máy tính", "service", "LAN", "642", "642", "5111", 300000),
    ("DV002", "Lắp đặt mạng LAN", "service", "LAN", "642", "642", "5111", 1500000),
]

EMPLOYEE_SPECS = [
    ("NV001", "Nguyễn Thị Mai", "female", date(1990, 5, 15), 18000000, 2000000),
    ("NV002", "Trần Văn Hùng", "male", date(1985, 3, 20), 25000000, 3000000),
]

# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = (
        "Seed dogfooding data: 3 companies (TT133 + TT58 DNSN x2) with 7 users each, "
        "master data, and sample transactions. Safe to run multiple times."
    )

    def handle(self, *args, **options):
        self.stdout.write("Seeding dogfooding data...")

        # Ensure module permissions exist before assigning them to roles.
        perm_map = self._ensure_module_permissions()

        # Ensure TT133 chart of accounts is loaded for all TT133 companies
        # before transactions reference account codes (111, 131, 511, 632...).
        try:
            from django.core.management import call_command

            call_command("ensure_tt133_charts", verbosity=0)
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"ensure_tt133_charts: {exc}"))

        for cfg in COMPANY_CONFIGS:
            company = self._seed_company(cfg)
            users = self._seed_users(company, cfg["prefix"])
            self._sync_role_permissions(company, perm_map)
            self._seed_master_data(company)
            self._seed_project(company)

            if company.accounting_regime == "tt133":
                self._seed_tt133_transactions(company)
            elif company.code == "DF-HN":
                self._seed_tt58_transactions(company)

            self._seed_hr_data(company)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {company.code} ({company.accounting_regime}): "
                    f"{len(users)} users + master data + transactions"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDogfooding seed complete! 3 companies, 21 users (password: {PASSWORD})."
            )
        )

    # ------------------------------------------------------------------
    # Companies
    # ------------------------------------------------------------------

    def _seed_company(self, cfg: dict) -> Company:
        defaults = {
            "name": cfg["name"],
            "tax_code": cfg["tax_code"],
            "address": cfg["address"],
            "legal_representative": cfg.get("legal_representative", ""),
            "accounting_regime": cfg["accounting_regime"],
            "industry": cfg.get("industry", ""),
            "is_active": True,
        }
        # TT58-specific fields
        if cfg["accounting_regime"] == "tt58":
            defaults["entity_type"] = cfg.get("entity_type", "doanh_nghiep_sieu_nho")
            defaults["vat_method"] = cfg.get("vat_method", "ty_le_phan_tram")
            defaults["tndn_method"] = cfg.get("tndn_method", "ty_le_phan_tram")
        else:
            defaults["sme_size"] = cfg.get("sme_size", "small")
            defaults["chief_accountant"] = cfg.get("chief_accountant", "")
        company, _created = Company.objects.update_or_create(code=cfg["code"], defaults=defaults)
        return company

    # ------------------------------------------------------------------
    # Users + Roles
    # ------------------------------------------------------------------

    def _seed_users(self, company: Company, prefix: str) -> list[User]:
        users = []
        for suffix, role_code, role_name, full_name in USER_SPECS:
            username = f"{prefix}_{suffix}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@dogfood.test",
                    "full_name": f"{full_name} ({company.code})",
                    "is_active": True,
                    "is_staff": suffix == "admin",
                    "is_superuser": False,
                },
            )
            if created:
                user.set_password(PASSWORD)
                user.save()

            role, _ = Role.objects.get_or_create(
                company=company,
                code=role_code,
                defaults={"name": role_name},
            )
            UserCompanyRole.objects.update_or_create(
                user=user,
                company=company,
                role=role,
                defaults={"is_default": True},
            )
            users.append(user)
        return users

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def _ensure_module_permissions(self) -> dict[str, Permission]:
        """Ensure all module-level permissions exist and return a lookup map.

        Mirrors the upsert logic in seed_permissions so seed_dogfood can run
        standalone (without a prior seed_permissions invocation).
        """
        perm_map: dict[str, Permission] = {}
        for module, name_vi, desc in MODULE_PERMISSIONS:
            perm, _created = Permission.objects.update_or_create(
                code=f"{module}.access",
                defaults={"module": module, "name": name_vi, "description": desc},
            )
            perm_map[module] = perm
        return perm_map

    def _sync_role_permissions(self, company: Company, perm_map: dict[str, Permission]) -> None:
        """Assign permissions to each of the company's roles per SYSTEM_ROLES.

        Iterates over the SYSTEM_ROLES mapping from seed_permissions and syncs
        the defined module permissions onto the matching role for this company.
        """
        for role_code, _name, _desc, modules, _is_system in SYSTEM_ROLES:
            role = Role.objects.filter(company=company, code=role_code).first()
            if role is None:
                continue
            perms = [perm_map[m] for m in modules if m in perm_map]
            role.permissions.set(perms)

    # ------------------------------------------------------------------
    # Master data
    # ------------------------------------------------------------------

    @transaction.atomic
    def _seed_master_data(self, company: Company) -> None:
        # Customers (3, different types via group_code)
        for code, name in CUSTOMER_NAMES:
            Customer.objects.update_or_create(
                company=company,
                code=code,
                defaults={
                    "name": name,
                    "address": f"{company.address}",
                    "phone": f"0283{company.code[-2:]}{code[-3:]}",
                    "payment_terms": "30 days",
                    "credit_limit": Decimal("500000000"),
                },
            )

        # Vendors (3)
        for code, name in VENDOR_NAMES:
            Vendor.objects.update_or_create(
                company=company,
                code=code,
                defaults={
                    "name": name,
                    "address": f"{company.address}",
                    "phone": f"0284{company.code[-2:]}{code[-3:]}",
                    "payment_terms": "15 days",
                },
            )

        # Products/services (5)
        for code, name, ptype, unit, inv, cogs, rev, price in PRODUCT_SPECS:
            Product.objects.update_or_create(
                company=company,
                code=code,
                defaults={
                    "name": name,
                    "product_type": ptype,
                    "unit_id": unit,
                    "gl_account_inv": inv,
                    "gl_account_cogs": cogs,
                    "gl_account_revenue": rev,
                    "default_unit_price": Decimal(str(price)),
                },
            )

        # Employees (2) — Department + Position must exist first
        dept, _ = Department.objects.get_or_create(
            company=company,
            code="DF_KE_TOAN",
            defaults={"name": "Phòng Kế toán"},
        )
        pos, _ = Position.objects.get_or_create(
            code="DF_NV",
            defaults={"name": "Nhân viên", "level": 2},
        )
        for emp_code, full_name, gender, birth_date, base_salary, allowance in EMPLOYEE_SPECS:
            Employee.objects.update_or_create(
                company=company,
                code=emp_code,
                defaults={
                    "full_name": full_name,
                    "gender": gender,
                    "birth_date": birth_date,
                    "department": dept,
                    "position": pos,
                    "hire_date": date(2020, 1, 1),
                    "base_salary": Decimal(str(base_salary)),
                    "allowance": Decimal(str(allowance)),
                    "status": "active",
                },
            )

    def _seed_project(self, company: Company) -> None:
        """Create 1 project per company."""
        emp = company.employees.first()
        Project.objects.update_or_create(
            company=company,
            code="DF_PRJ01",
            defaults={
                "name": f"Dự án triển khai ERP - {company.code}",
                "description": "Dự án dogfooding nội bộ",
                "manager": emp,
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 12, 31),
                "budget_revenue": Decimal("200000000"),
                "budget_cost": Decimal("100000000"),
                "status": "active",
                "priority": "high",
            },
        )

    # ------------------------------------------------------------------
    # TT133 transactions (Sài Gòn company)
    # ------------------------------------------------------------------

    @transaction.atomic
    def _seed_tt133_transactions(self, company: Company) -> None:
        """Create posted sales invoices, purchase invoice, and GL vouchers."""
        customer = company.customers.get(code="KH001")
        customer2 = company.customers.get(code="KH002")
        vendor = company.vendors.get(code="NCC001")
        product1 = company.products.get(code="SP001")
        product2 = company.products.get(code="SP002")
        service = company.products.get(code="DV001")

        # --- 2 Sales invoices (posted, via direct creation + VoucherPostingService) ---
        self._create_posted_sales_invoice(
            company,
            "DF-SI001",
            date(2026, 7, 5),
            customer,
            product1,
            qty=Decimal("2"),
            unit_price=Decimal("25000000"),
        )
        self._create_posted_sales_invoice(
            company,
            "DF-SI002",
            date(2026, 7, 10),
            customer2,
            service,
            qty=Decimal("5"),
            unit_price=Decimal("300000"),
        )

        # --- 1 Purchase invoice (posted) ---
        self._create_posted_purchase_invoice(
            company,
            "DF-PI001",
            date(2026, 7, 8),
            vendor,
            product2,
            qty=Decimal("10"),
            unit_price=Decimal("5500000"),
        )

        # --- 2 Accounting vouchers (phiếu thu + phiếu chi, posted) ---
        self._create_posted_gl_voucher(
            company,
            "DF-PT001",
            date(2026, 7, 12),
            AccountingVoucher.VoucherType.CASH_RECEIPT,
            "Thu tiền bán hàng từ KH001",
            debit_account="111",
            debit_amount=Decimal("55000000"),
            credit_account="131",
            credit_amount=Decimal("55000000"),
            object_type="customer",
            object_code="KH001",
            object_name=customer.name,
        )
        self._create_posted_gl_voucher(
            company,
            "DF-PC001",
            date(2026, 7, 15),
            AccountingVoucher.VoucherType.CASH_PAYMENT,
            "Chi tiền mua hàng từ NCC001",
            debit_account="331",
            debit_amount=Decimal("60500000"),
            credit_account="111",
            credit_amount=Decimal("60500000"),
            object_type="vendor",
            object_code="NCC001",
            object_name=vendor.name,
        )

        # --- 1 additional cash receipt voucher ---
        self._create_posted_gl_voucher(
            company,
            "DF-PT002",
            date(2026, 7, 20),
            AccountingVoucher.VoucherType.CASH_RECEIPT,
            "Thu tiền dịch vụ từ KH002",
            debit_account="111",
            debit_amount=Decimal("1650000"),
            credit_account="131",
            credit_amount=Decimal("1650000"),
            object_type="customer",
            object_code="KH002",
            object_name=customer2.name,
        )

    def _create_posted_sales_invoice(
        self,
        company,
        invoice_no,
        invoice_date,
        customer,
        product,
        qty,
        unit_price,
    ):
        """Create a posted sales invoice with one line + linked GL voucher."""
        vat_rate = product.default_vat_rate
        amount_before_vat = qty * unit_price
        vat_amount = (amount_before_vat * vat_rate).quantize(Decimal("0.0001"))
        total = amount_before_vat + vat_amount

        invoice, created = SalesInvoice.objects.get_or_create(
            company=company,
            invoice_no=invoice_no,
            defaults={
                "invoice_date": invoice_date,
                "customer": customer,
                "subtotal": amount_before_vat,
                "vat_amount": vat_amount,
                "total_amount": total,
                "status": 2,  # Ledger (posted)
                "description": f"Hóa đơn bán hàng {invoice_no}",
            },
        )
        if created:
            SalesInvoiceLine.objects.create(
                invoice=invoice,
                line_no=1,
                product=product,
                quantity=qty,
                unit_id=product.unit_id,
                unit_price=unit_price,
                amount_before_vat=amount_before_vat,
                vat_rate=vat_rate,
                vat_amount=vat_amount,
                amount=total,
            )

    def _create_posted_purchase_invoice(
        self,
        company,
        invoice_no,
        invoice_date,
        vendor,
        product,
        qty,
        unit_price,
    ):
        """Create a posted purchase invoice with one line."""
        vat_rate = product.default_vat_rate
        amount_before_vat = qty * unit_price
        vat_amount = (amount_before_vat * vat_rate).quantize(Decimal("0.0001"))
        total = amount_before_vat + vat_amount

        invoice, created = PurchaseInvoice.objects.get_or_create(
            company=company,
            invoice_no=invoice_no,
            defaults={
                "invoice_date": invoice_date,
                "vendor": vendor,
                "subtotal": amount_before_vat,
                "vat_amount": vat_amount,
                "total_amount": total,
                "status": 2,  # Ledger (posted)
                "description": f"Hóa đơn mua hàng {invoice_no}",
            },
        )
        if created:
            PurchaseInvoiceLine.objects.create(
                invoice=invoice,
                line_no=1,
                product=product,
                quantity=qty,
                unit_id=product.unit_id,
                unit_price=unit_price,
                amount_before_vat=amount_before_vat,
                vat_rate=vat_rate,
                vat_amount=vat_amount,
                amount=total,
            )

    def _create_posted_gl_voucher(
        self,
        company,
        voucher_no,
        voucher_date,
        voucher_type,
        description,
        debit_account,
        debit_amount,
        credit_account,
        credit_amount,
        object_type="",
        object_code="",
        object_name="",
    ):
        """Create a balanced, posted AccountingVoucher with 2 lines."""
        voucher, created = AccountingVoucher.objects.get_or_create(
            company=company,
            fiscal_year=2026,
            voucher_type=voucher_type,
            voucher_no=voucher_no,
            defaults={
                "period": voucher_date.month,
                "voucher_date": voucher_date,
                "posting_date": voucher_date,
                "status": AccountingVoucher.Status.LEDGER,
                "description": description,
                "total_vnd": debit_amount,
            },
        )
        if created:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=1,
                account_code=debit_account,
                debit_vnd=debit_amount,
                description=description,
                object_type=object_type,
                object_code=object_code,
                object_name=object_name,
            )
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=2,
                account_code=credit_account,
                credit_vnd=credit_amount,
                description=description,
            )
            VoucherPostingService().post(voucher)

    # ------------------------------------------------------------------
    # TT58 transactions (Hà Nội DNSN company)
    # ------------------------------------------------------------------

    @transaction.atomic
    def _seed_tt58_transactions(self, company: Company) -> None:
        """Create 2 posted DnsnVouchers (phiếu thu + phiếu chi)."""
        service = DnsnPostingService()

        # Phiếu thu (cash receipt — revenue)
        voucher_pt, created_pt = DnsnVoucher.objects.get_or_create(
            company=company,
            fiscal_year=2026,
            voucher_type=DnsnVoucher.VoucherType.PHIEU_THU,
            voucher_no="DF-DN-PT001",
            defaults={
                "period": 7,
                "voucher_date": date(2026, 7, 5),
                "description": "Thu tiền bán hàng dịch vụ",
                "partner_name": "Khách hàng An Phát",
                "status": DnsnVoucher.Status.DRAFT,
            },
        )
        if (created_pt or not voucher_pt.is_posted) and not voucher_pt.is_posted:
            # Clear stale entries so re-post is clean
            voucher_pt.ledger_entries.all().delete()
            service.post(
                voucher_pt,
                entries=[
                    {
                        "ledger_type": "s2a",
                        "description": "Doanh thu bán dịch vụ tháng 7",
                        "revenue_amount": Decimal("15000000"),
                    },
                ],
            )

        # Phiếu chi (cash payment — cost)
        voucher_pc, created_pc = DnsnVoucher.objects.get_or_create(
            company=company,
            fiscal_year=2026,
            voucher_type=DnsnVoucher.VoucherType.PHIEU_CHI,
            voucher_no="DF-DN-PC001",
            defaults={
                "period": 7,
                "voucher_date": date(2026, 7, 12),
                "description": "Chi phí vận hành",
                "partner_name": "NCC Vật tư Đông Dương",
                "status": DnsnVoucher.Status.DRAFT,
            },
        )
        if (created_pc or not voucher_pc.is_posted) and not voucher_pc.is_posted:
            voucher_pc.ledger_entries.all().delete()
            service.post(
                voucher_pc,
                entries=[
                    {
                        "ledger_type": "s2d",
                        "description": "Chi tiền mặt vận hành",
                        "cash_out": Decimal("8000000"),
                    },
                ],
            )

    # ------------------------------------------------------------------
    # HR data (labor contracts + payroll)
    # ------------------------------------------------------------------

    @transaction.atomic
    def _seed_hr_data(self, company: Company) -> None:
        """Create 2 labor contracts + 1 calculated payroll run."""
        employees = list(company.employees.all().order_by("code"))
        if len(employees) < 2:
            return

        dept = company.departments.first()

        for idx, emp in enumerate(employees, start=1):
            base = emp.base_salary
            allowance = emp.allowance
            contract_no = f"DF-HDL{idx:03d}"
            LaborContract.objects.update_or_create(
                company=company,
                contract_no=contract_no,
                defaults={
                    "employee": emp,
                    "contract_type": LaborContract.ContractType.FIXED_TERM,
                    "start_date": date(2024, 1, 1),
                    "end_date": date(2026, 12, 31),
                    "salary_base": base,
                    "salary_gross": base + allowance,
                    "allowance_amount": allowance,
                    "insurance_salary_base": base,
                    "join_insurance": True,
                    "position_title": emp.position.name if emp.position else "",
                    "department": dept,
                    "status": LaborContract.Status.ACTIVE,
                },
            )

        # 1 Payroll run (calculated)
        run, _ = PayrollRun.objects.update_or_create(
            company=company,
            period="2026-07",
            defaults={
                "fiscal_year": 2026,
                "period_num": 7,
                "status": PayrollRun.Status.CALCULATED,
            },
        )
        for line_no, emp in enumerate(employees, start=1):
            gross = emp.base_salary + emp.allowance
            # Simplified insurance estimates (employee ~10.5%)
            ins_emp = (emp.base_salary * Decimal("0.105")).quantize(Decimal("0.0001"))
            pit = max(Decimal("0"), (gross - ins_emp - Decimal("15500000")) * Decimal("0.05"))
            pit = pit.quantize(Decimal("0.0001"))
            net = gross - ins_emp - pit
            PayrollLine.objects.update_or_create(
                run=run,
                employee=emp,
                defaults={
                    "line_no": line_no,
                    "work_days": Decimal("22"),
                    "base_salary": emp.base_salary,
                    "allowance_amount": emp.allowance,
                    "gross_salary": gross,
                    "social_insurance_employee": ins_emp * Decimal("0.8"),
                    "health_insurance_employee": ins_emp * Decimal("0.15"),
                    "unemployment_insurance_employee": ins_emp * Decimal("0.05"),
                    "pit": pit,
                    "net_salary": net,
                },
            )
        lines = list(run.lines.all())
        run.total_gross = sum(ln.gross_salary for ln in lines)
        run.total_insurance_employee = sum(
            ln.social_insurance_employee
            + ln.health_insurance_employee
            + ln.unemployment_insurance_employee
            for ln in lines
        )
        run.total_pit = sum(ln.pit for ln in lines)
        run.total_net = sum(ln.net_salary for ln in lines)
        run.save()
