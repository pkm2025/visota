"""Seed TT58 demo data: DNSN companies for all 4 tax method groups + HKD company.

Creates demo companies with full TT58 data: posted vouchers, ledger entries,
and balances. Each DNSN company represents one of the 4 tax method groups
defined in TT58/2026/TT-BTC:

  Group 1: GTGT tỷ lệ % + TNDN tỷ lệ %     → S1-DNSN
  Group 2: GTGT tỷ lệ % + TNDN tính thuế   → S2a, S2b, S2c, S2d
  Group 3: GTGT khấu trừ  + TNDN tỷ lệ %   → S3a, S3b
  Group 4: GTGT khấu trừ  + TNDN tính thuế → S2b, S2c, S2d, S3b

Also creates a demo Hộ kinh doanh (HKD) entity with vouchers and reports.

Usage:
    python manage.py seed_tt58_demo
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Company
from apps.ledger.models import DnsnLedgerEntry, DnsnVoucher
from apps.ledger.services import DnsnPostingService

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FISCAL_YEAR = 2026
PERIOD = 7

# Voucher dates spread across the period for realistic data.
VOUCHER_DATES = [
    date(2026, 7, 3),
    date(2026, 7, 8),
    date(2026, 7, 15),
    date(2026, 7, 22),
    date(2026, 7, 29),
]


# ---------------------------------------------------------------------------
# Company definitions
# ---------------------------------------------------------------------------

DNSN_COMPANY_CONFIGS = [
    {
        "code": "DN58-G1",
        "name": "Cửa hàng Mini Shop DNSN Nhóm 1",
        "tax_code": "0315811111",
        "entity_type": "doanh_nghiep_sieu_nho",
        "vat_method": "ty_le_phan_tram",
        "tndn_method": "ty_le_phan_tram",
        "address": "123 Lê Lợi, Q.1, TP. HCM",
        "legal_representative": "Nguyễn Văn A",
    },
    {
        "code": "DN58-G2",
        "name": "Công ty TNHH Thương mại DNSN Nhóm 2",
        "tax_code": "0315822222",
        "entity_type": "doanh_nghiep_sieu_nho",
        "vat_method": "ty_le_phan_tram",
        "tndn_method": "tinh_thue",
        "address": "456 Hai Bà Trưng, Q.3, TP. HCM",
        "legal_representative": "Trần Thị B",
    },
    {
        "code": "DN58-G3",
        "name": "Dịch vụ DNSN Nhóm 3",
        "tax_code": "0315833333",
        "entity_type": "doanh_nghiep_sieu_nho",
        "vat_method": "khau_tru",
        "tndn_method": "ty_le_phan_tram",
        "address": "789 Nguyễn Huệ, Q.1, TP. HCM",
        "legal_representative": "Phạm Văn C",
    },
    {
        "code": "DN58-G4",
        "name": "Công ty TNHH Sản xuất DNSN Nhóm 4",
        "tax_code": "0315844444",
        "entity_type": "doanh_nghiep_sieu_nho",
        "vat_method": "khau_tru",
        "tndn_method": "tinh_thue",
        "address": "321 Điện Biên Phủ, Bình Thạnh, TP. HCM",
        "legal_representative": "Lê Thị D",
    },
]

HKD_COMPANY_CONFIG = {
    "code": "HKD-DEMO",
    "name": "Hộ kinh doanh Tạp hóa Minh Châu",
    "tax_code": "0315855555",
    "entity_type": "ho_kinh_doanh",
    "vat_method": "ty_le_phan_tram",
    "tndn_method": "ty_le_phan_tram",
    "address": "56 Xóm Đồi, P.7, Q. Phú Nhuận, TP. HCM",
    "legal_representative": "Minh Châu",
}


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = (
        "Seed TT58 demo data: DNSN companies for all 4 tax method groups "
        "+ demo Hộ kinh doanh with posted vouchers and ledger entries."
    )

    def handle(self, *args, **options):
        self.stdout.write("Seeding TT58 demo data...")

        total_companies = 0
        total_vouchers = 0

        for config in DNSN_COMPANY_CONFIGS:
            company, v_count = self._seed_dnsn_company(config)
            total_companies += 1
            total_vouchers += v_count
            self.stdout.write(
                f"  Created {company.code} (Group {company.tax_method_group}) "
                f"with {v_count} posted vouchers"
            )

        # Seed HKD company (uses Group 1 config — GTGT% + TNDN%)
        hkd_company, hkd_v_count = self._seed_hkd_company()
        total_companies += 1
        total_vouchers += hkd_v_count
        self.stdout.write(
            f"  Created {hkd_company.code} (HKD, Group {hkd_company.tax_method_group}) "
            f"with {hkd_v_count} posted vouchers"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTT58 seed complete: {total_companies} companies, "
                f"{total_vouchers} posted vouchers. "
                f"Use the company switcher to view TT58 data."
            )
        )

    # ------------------------------------------------------------------
    # Company creation
    # ------------------------------------------------------------------

    def _seed_dnsn_company(self, config: dict) -> tuple[Company, int]:
        """Create a DNSN demo company with posted vouchers for its tax group."""
        company, _created = Company.objects.update_or_create(
            code=config["code"],
            defaults={
                "name": config["name"],
                "tax_code": config["tax_code"],
                "address": config["address"],
                "legal_representative": config["legal_representative"],
                "accounting_regime": "tt58",
                "entity_type": config["entity_type"],
                "vat_method": config["vat_method"],
                "tndn_method": config["tndn_method"],
                "is_active": True,
            },
        )

        # Clear existing data for clean re-run
        self._clear_existing_data(company)

        group = company.tax_method_group
        voucher_count = self._create_vouchers_for_group(company, group)

        return company, voucher_count

    def _seed_hkd_company(self) -> tuple[Company, int]:
        """Create a demo HKD company with posted vouchers."""
        config = HKD_COMPANY_CONFIG
        company, _created = Company.objects.update_or_create(
            code=config["code"],
            defaults={
                "name": config["name"],
                "tax_code": config["tax_code"],
                "address": config["address"],
                "legal_representative": config["legal_representative"],
                "accounting_regime": "tt58",
                "entity_type": config["entity_type"],
                "vat_method": config["vat_method"],
                "tndn_method": config["tndn_method"],
                "is_active": True,
                # HKD entities do not require a chief accountant per TT58/2026
                "chief_accountant": "",
                "chief_accountant_license": "",
                "chief_accountant_phone": "",
            },
        )

        self._clear_existing_data(company)

        # HKD uses Group 1 ledgers (S1-DNSN) since it's GTGT% + TNDN%
        group = company.tax_method_group
        voucher_count = self._create_vouchers_for_group(company, group)

        return company, voucher_count

    # ------------------------------------------------------------------
    # Voucher creation per tax method group
    # ------------------------------------------------------------------

    @transaction.atomic
    def _create_vouchers_for_group(self, company: Company, group: int) -> int:
        """Create posted vouchers appropriate for the company's tax method group.

        Each group has different ledger types per TT58/2026/TT-BTC:
          Group 1: S1 (revenue only)
          Group 2: S2a (revenue), S2b (revenue+cost), S2c (inventory), S2d (cash)
          Group 3: S3a (revenue), S3b (VAT)
          Group 4: S2b (revenue+cost), S2c (inventory), S2d (cash), S3b (VAT)
        """
        if group == 1:
            return self._seed_group1(company)
        if group == 2:
            return self._seed_group2(company)
        if group == 3:
            return self._seed_group3(company)
        if group == 4:
            return self._seed_group4(company)
        return 0

    def _seed_group1(self, company: Company) -> int:
        """Group 1 (GTGT% + TNDN%): S1-DNSN (revenue only)."""
        service = DnsnPostingService()
        count = 0

        # Revenue vouchers posted to S1
        for i, vdate in enumerate(VOUCHER_DATES):
            amount = Decimal("5000000") + Decimal(str(i * 500000))
            voucher = DnsnVoucher.objects.create(
                company=company,
                fiscal_year=FISCAL_YEAR,
                period=PERIOD,
                voucher_no=f"S1-PT{i + 1:04d}",
                voucher_type="phieu_thu",
                voucher_date=vdate,
                description=f"Doanh thu bán hàng ngày {vdate.strftime('%d/%m')}",
                partner_name=f"Khách hàng {i + 1}",
                status="draft",
            )
            entries = [
                {
                    "ledger_type": "s1",
                    "description": f"Doanh thu bán hàng ngày {vdate.strftime('%d/%m')}",
                    "partner_name": f"Khách hàng {i + 1}",
                    "revenue_amount": amount,
                }
            ]
            service.post(voucher, entries=entries)
            count += 1

        return count

    def _seed_group2(self, company: Company) -> int:
        """Group 2 (GTGT% + TNDN tinh thue): S2a, S2b, S2c, S2d."""
        service = DnsnPostingService()
        count = 0

        # S2a: Revenue entries
        for i, vdate in enumerate(VOUCHER_DATES[:3]):
            amount = Decimal("8000000") + Decimal(str(i * 1000000))
            voucher = DnsnVoucher.objects.create(
                company=company,
                fiscal_year=FISCAL_YEAR,
                period=PERIOD,
                voucher_no=f"S2A-PT{i + 1:04d}",
                voucher_type="hoa_don_ban_hang",
                voucher_date=vdate,
                description=f"Hóa đơn bán hàng ngày {vdate.strftime('%d/%m')}",
                partner_name=f"Khách hàng {i + 1}",
                invoice_no=f"HD2A-{i + 1:04d}",
                invoice_date=vdate,
                invoice_form="02BANHANG",
                status="draft",
            )
            entries = [
                {
                    "ledger_type": "s2a",
                    "description": f"Doanh thu bán hàng ngày {vdate.strftime('%d/%m')}",
                    "revenue_amount": amount,
                }
            ]
            service.post(voucher, entries=entries)
            count += 1

        # S2b: Revenue + cost entries
        for i, vdate in enumerate(VOUCHER_DATES[:3]):
            revenue = Decimal("6000000")
            cost = Decimal("4000000")
            voucher = DnsnVoucher.objects.create(
                company=company,
                fiscal_year=FISCAL_YEAR,
                period=PERIOD,
                voucher_no=f"S2B-PC{i + 1:04d}",
                voucher_type="phieu_chi",
                voucher_date=vdate,
                description=f"Chi phí hoạt động ngày {vdate.strftime('%d/%m')}",
                partner_name=f"NCC {i + 1}",
                status="draft",
            )
            entries = [
                {
                    "ledger_type": "s2b",
                    "description": f"Doanh thu + chi phí ngày {vdate.strftime('%d/%m')}",
                    "revenue_amount": revenue,
                    "cost_amount": cost,
                }
            ]
            service.post(voucher, entries=entries)
            count += 1

        # S2c: Inventory entries
        for i, vdate in enumerate(VOUCHER_DATES[:2]):
            qty = Decimal("100") + Decimal(str(i * 20))
            price = Decimal("50000")
            total = qty * price
            voucher = DnsnVoucher.objects.create(
                company=company,
                fiscal_year=FISCAL_YEAR,
                period=PERIOD,
                voucher_no=f"S2C-PN{i + 1:04d}",
                voucher_type="phieu_nhap",
                voucher_date=vdate,
                description=f"Nhập kho hàng hóa ngày {vdate.strftime('%d/%m')}",
                partner_name=f"Nhà cung cấp {i + 1}",
                status="draft",
            )
            entries = [
                {
                    "ledger_type": "s2c",
                    "description": f"Nhập hàng hóa mã HH{i + 1:03d}",
                    "item_code": f"HH{i + 1:03d}",
                    "item_name": f"Hàng hóa {i + 1}",
                    "quantity": qty,
                    "unit_price": price,
                    "total_amount": total,
                }
            ]
            service.post(voucher, entries=entries)
            count += 1

        # S2d: Cash entries
        for i, vdate in enumerate(VOUCHER_DATES[:3]):
            cash_in = Decimal("3000000")
            cash_out = Decimal("1500000")
            voucher = DnsnVoucher.objects.create(
                company=company,
                fiscal_year=FISCAL_YEAR,
                period=PERIOD,
                voucher_no=f"S2D-PT{i + 1:04d}",
                voucher_type="phieu_thu",
                voucher_date=vdate,
                description=f"Thu/chi tiền mặt ngày {vdate.strftime('%d/%m')}",
                status="draft",
            )
            entries = [
                {
                    "ledger_type": "s2d",
                    "description": f"Thu tiền mặt ngày {vdate.strftime('%d/%m')}",
                    "cash_in": cash_in,
                    "cash_out": cash_out,
                }
            ]
            service.post(voucher, entries=entries)
            count += 1

        return count

    def _seed_group3(self, company: Company) -> int:
        """Group 3 (GTGT khau tru + TNDN%): S3a (revenue), S3b (VAT)."""
        service = DnsnPostingService()
        count = 0

        # S3a: Revenue entries + S3b: VAT output
        for i, vdate in enumerate(VOUCHER_DATES):
            revenue = Decimal("10000000") + Decimal(str(i * 1000000))
            vat_output = revenue * Decimal("0.08")  # VAT 8% (ND 174/2025)

            voucher = DnsnVoucher.objects.create(
                company=company,
                fiscal_year=FISCAL_YEAR,
                period=PERIOD,
                voucher_no=f"S3A-PT{i + 1:04d}",
                voucher_type="hoa_don_ban_hang",
                voucher_date=vdate,
                description=f"Bán hàng có hóa đơn GTGT ngày {vdate.strftime('%d/%m')}",
                partner_name=f"Khách hàng {i + 1}",
                invoice_no=f"HD3A-{i + 1:04d}",
                invoice_date=vdate,
                invoice_form="01GTKT",
                invoice_serial="C26T",
                status="draft",
            )
            entries = [
                {
                    "ledger_type": "s3a",
                    "description": f"Doanh thu bán hàng GTGT ngày {vdate.strftime('%d/%m')}",
                    "revenue_amount": revenue,
                },
                {
                    "ledger_type": "s3b",
                    "description": f"Thuế GTGT đầu ra ngày {vdate.strftime('%d/%m')}",
                    "vat_output": vat_output,
                },
            ]
            service.post(voucher, entries=entries)
            count += 1

        return count

    def _seed_group4(self, company: Company) -> int:
        """Group 4 (GTGT khau tru + TNDN tinh thue): S2b, S2c, S2d, S3b."""
        service = DnsnPostingService()
        count = 0

        # S2b: Revenue + cost entries
        for i, vdate in enumerate(VOUCHER_DATES[:3]):
            revenue = Decimal("12000000")
            cost = Decimal("8000000")
            voucher = DnsnVoucher.objects.create(
                company=company,
                fiscal_year=FISCAL_YEAR,
                period=PERIOD,
                voucher_no=f"S2B4-PC{i + 1:04d}",
                voucher_type="phieu_chi",
                voucher_date=vdate,
                description=f"Chi phí kinh doanh ngày {vdate.strftime('%d/%m')}",
                partner_name=f"NCC {i + 1}",
                status="draft",
            )
            entries = [
                {
                    "ledger_type": "s2b",
                    "description": f"Doanh thu + chi phí ngày {vdate.strftime('%d/%m')}",
                    "revenue_amount": revenue,
                    "cost_amount": cost,
                }
            ]
            service.post(voucher, entries=entries)
            count += 1

        # S2c: Inventory entries
        for i, vdate in enumerate(VOUCHER_DATES[:2]):
            qty = Decimal("200")
            price = Decimal("75000")
            total = qty * price
            voucher = DnsnVoucher.objects.create(
                company=company,
                fiscal_year=FISCAL_YEAR,
                period=PERIOD,
                voucher_no=f"S2C4-PN{i + 1:04d}",
                voucher_type="phieu_nhap",
                voucher_date=vdate,
                description=f"Nhập kho nguyên vật liệu ngày {vdate.strftime('%d/%m')}",
                partner_name=f"Nhà cung cấp {i + 1}",
                status="draft",
            )
            entries = [
                {
                    "ledger_type": "s2c",
                    "description": f"Nhập NVL mã NVL{i + 1:03d}",
                    "item_code": f"NVL{i + 1:03d}",
                    "item_name": f"Nguyên vật liệu {i + 1}",
                    "quantity": qty,
                    "unit_price": price,
                    "total_amount": total,
                }
            ]
            service.post(voucher, entries=entries)
            count += 1

        # S2d: Cash entries
        for i, vdate in enumerate(VOUCHER_DATES[:3]):
            cash_in = Decimal("5000000")
            cash_out = Decimal("2500000")
            voucher = DnsnVoucher.objects.create(
                company=company,
                fiscal_year=FISCAL_YEAR,
                period=PERIOD,
                voucher_no=f"S2D4-PT{i + 1:04d}",
                voucher_type="phieu_thu",
                voucher_date=vdate,
                description=f"Thu/chi tiền ngày {vdate.strftime('%d/%m')}",
                status="draft",
            )
            entries = [
                {
                    "ledger_type": "s2d",
                    "description": f"Dòng tiền ngày {vdate.strftime('%d/%m')}",
                    "cash_in": cash_in,
                    "cash_out": cash_out,
                }
            ]
            service.post(voucher, entries=entries)
            count += 1

        # S3b: VAT entries (output + input)
        for i, vdate in enumerate(VOUCHER_DATES[:3]):
            vat_output = Decimal("960000")  # Output VAT
            vat_input = Decimal("640000")  # Input VAT
            voucher = DnsnVoucher.objects.create(
                company=company,
                fiscal_year=FISCAL_YEAR,
                period=PERIOD,
                voucher_no=f"S3B4-PT{i + 1:04d}",
                voucher_type="hoa_don_ban_hang",
                voucher_date=vdate,
                description=f"Thuế GTGT đầu ra + đầu vào ngày {vdate.strftime('%d/%m')}",
                partner_name=f"Khách hàng {i + 1}",
                invoice_no=f"HD3B-{i + 1:04d}",
                invoice_date=vdate,
                invoice_form="01GTKT",
                invoice_serial="C26T",
                status="draft",
            )
            entries = [
                {
                    "ledger_type": "s3b",
                    "description": f"GTGT đầu ra ngày {vdate.strftime('%d/%m')}",
                    "vat_output": vat_output,
                    "vat_input": vat_input,
                }
            ]
            service.post(voucher, entries=entries)
            count += 1

        return count

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _clear_existing_data(self, company: Company) -> None:
        """Clear existing DNSN vouchers and entries for a clean re-run."""
        DnsnLedgerEntry.objects.filter(company=company).delete()
        DnsnVoucher.objects.filter(company=company).delete()
        from apps.ledger.models import DnsnLedgerBalance

        DnsnLedgerBalance.objects.filter(company=company).delete()
