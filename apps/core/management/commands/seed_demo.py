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

        # 6. Sample fixed asset (TSCĐ): TS001 Xe Toyota Vios
        from apps.assets.models import (
            AssetCategory,
            AssetUsingDepartment,
            FixedAsset,
        )

        category, _ = AssetCategory.objects.update_or_create(
            company=company,
            code="PTVT",
            defaults={
                "name": "Phương tiện vận tải",
                "level": "group",
                "is_for_tool": False,
                "default_gl_account": "2112",
                "default_depreciation_account": "2141",
                "default_expense_account": "642",
                "default_depreciation_rate": "0.20",
                "default_useful_life_months": 60,
            },
        )

        department, _ = AssetUsingDepartment.objects.update_or_create(
            company=company,
            code="BP_HC",
            defaults={
                "name": "Bộ phận Hành chính",
                "default_expense_account": "642",
            },
        )

        from decimal import Decimal

        fixed_asset, fa_created = FixedAsset.objects.update_or_create(
            company=company,
            asset_code="TS001",
            defaults={
                "asset_name": "Xe Toyota Vios",
                "category": category,
                "using_department": department,
                "gl_account": "2112",
                "depreciation_account": "2141",
                "expense_account": "642",
                "original_cost": Decimal("800000000"),
                "currency_code": "VND",
                "depreciation_method": FixedAsset.DepreciationMethod.STRAIGHT_LINE,
                "depreciation_rate": Decimal("0.20"),
                "useful_life_months": 60,
                "start_date": "2024-01-01",
                "is_tool": False,
                "status": FixedAsset.Status.ACTIVE,
            },
        )

        self.stdout.write(
            "Sample master data: 1 customer, 1 vendor, 1 product, 1 warehouse"
            + (", 1 fixed asset" if fa_created else "")
        )

        # 7. Sample HR data: department, position, 2 employees
        from apps.hr.models import Department, Employee, Position

        dept_hr, _ = Department.objects.update_or_create(
            company=company,
            code="KE_TOAN",
            defaults={"name": "Kế toán"},
        )
        pos_nv, _ = Position.objects.update_or_create(
            code="KE_TOAN_VIEN",
            defaults={"name": "Kế toán viên", "level": 2},
        )
        Employee.objects.update_or_create(
            company=company,
            code="NV001",
            defaults={
                "full_name": "Nguyễn Thị Mai",
                "birth_date": "1990-05-15",
                "gender": "female",
                "id_card_no": "001123456789",
                "personal_tax_code": "037123456789",
                "social_insurance_no": "1234567890",
                "department": dept_hr,
                "position": pos_nv,
                "hire_date": "2020-01-01",
                "base_salary": 15000000,
                "allowance": 2000000,
                "bank_account_no": "1234567890",
                "bank_id": "VCB",
                "status": "active",
            },
        )
        Employee.objects.update_or_create(
            company=company,
            code="NV002",
            defaults={
                "full_name": "Trần Văn Hùng",
                "birth_date": "1985-03-20",
                "gender": "male",
                "department": dept_hr,
                "position": pos_nv,
                "hire_date": "2019-06-01",
                "base_salary": 20000000,
                "allowance": 3000000,
                "status": "active",
            },
        )
        self.stdout.write("Sample employees: NV001 (15M), NV002 (20M)")

        # 7b. Sample HR detail data: contract, dependent, leave balance for NV001
        from datetime import date as _date
        from decimal import Decimal as _Decimal

        from apps.hr.models import (
            Dependent,
            LaborContract,
            LeaveBalance,
        )

        nv001 = Employee.objects.get(company=company, code="NV001")
        LaborContract.objects.update_or_create(
            company=company,
            contract_no="HDL001",
            defaults={
                "employee": nv001,
                "contract_type": LaborContract.ContractType.FIXED_TERM,
                "start_date": _date(2024, 1, 1),
                "end_date": _date(2026, 12, 31),
                "salary_base": _Decimal("15000000"),
                "salary_gross": _Decimal("17000000"),
                "allowance_amount": _Decimal("2000000"),
                "insurance_salary_base": _Decimal("15000000"),
                "join_insurance": True,
                "position_title": "Kế toán viên",
                "department": dept_hr,
                "status": LaborContract.Status.ACTIVE,
            },
        )
        Dependent.objects.update_or_create(
            employee=nv001,
            full_name="Nguyễn Minh Khôi",
            defaults={
                "relationship": Dependent.Relationship.CHILD,
                "birth_date": _date(2015, 3, 10),
                "deduction_amount": _Decimal("6200000"),
                "valid_from": _date(2024, 1, 1),
                "registration_status": Dependent.RegistrationStatus.REGISTERED,
            },
        )
        LeaveBalance.objects.update_or_create(
            employee=nv001,
            fiscal_year=2026,
            defaults={
                "standard_days": _Decimal("12"),
                "carried_forward": _Decimal("0"),
                "used_days": _Decimal("0"),
            },
        )
        self.stdout.write(
            "Sample HR detail: NV001 contract (15M), 1 dependent (6.2M), "
            "2026 leave balance (12 days)"
        )

        # 8. Default recurring templates (bút toán định kỳ)
        from apps.recurring.services import RecurringService

        templates = RecurringService().setup_defaults(company)
        self.stdout.write(f"Created {len(templates)} recurring templates")

        # 9. Seed contract templates
        from django.core.management import call_command as _call

        _call("seed_contract_templates", verbosity=0)
        _call("seed_legal_references", verbosity=0)
        _call("seed_tax_types", verbosity=0)
        self.stdout.write("Seeded contract templates + legal references + tax types")

        # 10. Default TaxRateConfig (Luật TNDN 2025 + ND 174/2025 VAT 8%)
        from datetime import date as _date
        from decimal import Decimal as _Decimal

        from apps.core.models import TaxRateConfig

        TaxRateConfig.objects.update_or_create(
            is_active=True,
            defaults={
                "cit_rate_standard": _Decimal("0.20"),
                "cit_rate_small": _Decimal("0.17"),
                "cit_rate_micro": _Decimal("0.15"),
                # CIT exemption threshold (ND 141/2026 — revenue <= 1 tỷ/year = 0% CIT)
                "cit_exemption_threshold": _Decimal("1000000000"),
                "vat_rate_standard": _Decimal("0.10"),
                "vat_rate_reduced": _Decimal("0.08"),
                "vat_rate_reduced_active": True,  # ND 174/2025 active until 31/12/2026
                # VAT thresholds (Luật GTGT 09/2026)
                "vat_exemption_threshold": _Decimal("1000000000"),  # < 1 tỷ/year = VAT exempt
                "vat_refund_threshold": _Decimal("300000000"),  # input VAT >= 300 triệu = refund
                # Active PIT — NQ 110/2025/UBTVQH15 (hiệu lực từ 01/07/2026)
                # GTGC 15.5M/tháng, NPT 6.2M, 5 bậc lũy tiến 5%/10%/20%/30%/35%
                "pit_personal_deduction": _Decimal("15500000"),
                "pit_dependent_deduction": _Decimal("6200000"),
                "pit_brackets": [
                    [5000000, "0.05"],
                    [10000000, "0.10"],
                    [18000000, "0.20"],
                    [32000000, "0.30"],
                    [999999999, "0.35"],
                ],
                # 2026 fields (mirrors active values — NQ 110/2025 effective 01/07/2026)
                "pit_personal_deduction_2026": _Decimal("15500000"),
                "pit_dependent_deduction_2026": _Decimal("6200000"),
                "pit_brackets_2026": [
                    [5000000, "0.05"],
                    [10000000, "0.10"],
                    [18000000, "0.20"],
                    [32000000, "0.30"],
                    [999999999, "0.35"],
                ],
                # PIT non-taxable allowances (ND 253/2026 + TT 87/2026)
                "pit_meal_allowance": _Decimal("1200000"),  # Trợ cấp ăn trưa — 1.2M/mo
                "pit_pension_allowance": _Decimal("3000000"),  # BHXH tự nguyện/BHNT — 3M/mo
                "pit_medical_deduction": _Decimal("23000000"),  # 23M/yr
                "pit_education_deduction": _Decimal("24000000"),  # 24M/yr
                "pit_dependent_income_threshold": _Decimal("3000000"),  # 3M/mo
                "pit_withholding_threshold": _Decimal("5000000"),  # 5M/payment
                # TTĐB rates (Luật TTĐB 66/2025/QH15)
                "ttdb_alcohol_high": _Decimal("0.65"),
                "ttdb_alcohol_low": _Decimal("0.35"),
                "ttdb_beer": _Decimal("0.65"),
                "ttdb_tobacco_rate": _Decimal("0.75"),
                "ttdb_tobacco_absolute": _Decimal("5000"),
                "ttdb_car_under_9": _Decimal("0.15"),
                "ttdb_car_hybrid_discount": _Decimal("0.70"),
                # Lệ phí môn bài (ND 22/2020)
                "fee_monbai_over_10b": _Decimal("3000000"),
                "fee_monbai_under_10b": _Decimal("2000000"),
                # Lệ phí trước bạ (ND 10/2022)
                "fee_truoc_ba_real_estate": _Decimal("0.005"),
                "fee_truoc_ba_other": _Decimal("0.01"),
                # Thuế nhà thầu (TT 20/2026)
                "fct_cit_rate": _Decimal("0.05"),
                "fct_vat_rate": _Decimal("0.05"),
                "bhxh_cap": _Decimal("50600000"),
                "bhxh_base_salary": _Decimal("2530000"),
                "effective_date": _date(2026, 7, 1),
            },
        )
        self.stdout.write("Seeded TaxRateConfig (CIT/VAT/PIT/TTĐB/môn bài/trước bạ/FCT)")

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete. Company: {company.code}, User: admin, "
                f"Permissions: {len(core_perms)}"
            )
        )
