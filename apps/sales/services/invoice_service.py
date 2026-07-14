"""SalesInvoiceService — creates invoice + generates accounting voucher.

Tax-method-aware for TT58/2026/TT-BTC:
- If company.accounting_regime == 'tt58': create DnsnVoucher + DnsnLedgerEntry.
- If company.vat_method == 'ty_le_phan_tram': revenue includes VAT (no TK 33311).
- If company.vat_method == 'khau_tru': existing deduction behavior (TK 33311).
- Non-TT58 companies: unchanged TT133/TT200 behavior.
"""

from decimal import Decimal

from django.db import transaction

from apps.core.models import Company
from apps.core.services.tndn_calculation_service import TndnCalculationService
from apps.ledger.models import AccountingVoucher, DnsnVoucher, VoucherLine
from apps.ledger.services import DnsnPostingService, VoucherPostingService
from apps.master_data.models import Customer, Product
from apps.sales.models import SalesInvoice, SalesInvoiceLine


class SalesInvoiceService:
    """Service for creating/posting sales invoices."""

    def __init__(self, company: Company):
        self.company = company

    @property
    def is_tt58(self) -> bool:
        """Check if the company uses TT58 accounting regime."""
        return self.company.accounting_regime == Company.AccountingRegime.TT58

    @property
    def is_vat_percentage(self) -> bool:
        """Check if the company uses percentage-based VAT (ty_le_phan_tram)."""
        return self.company.vat_method == Company.VatMethod.TY_LE_PHAN_TRAM

    @transaction.atomic
    def create(self, data: dict) -> SalesInvoice:
        """Create invoice + (optional) auto-post voucher.

        data keys:
            invoice_no, invoice_date, customer_id, sales_staff_code, description,
            currency_code, exchange_rate,
            lines: list of {product_id, quantity, unit_price, vat_rate, ...}
            post: bool — auto-post voucher after creation (default True)
        """
        customer = Customer.objects.get(id=data["customer_id"], company=self.company)

        invoice = SalesInvoice.objects.create(
            company=self.company,
            invoice_no=data["invoice_no"],
            invoice_date=data["invoice_date"],
            invoice_type=data.get("invoice_type", SalesInvoice.InvoiceType.GOODS),
            customer=customer,
            sales_staff_code=data.get("sales_staff_code", ""),
            currency_code=data.get("currency_code", "VND"),
            exchange_rate=data.get("exchange_rate", Decimal("1")),
            description=data.get("description", ""),
            status=0,  # draft until posted
        )

        # Build lines + compute totals
        subtotal = Decimal("0")
        vat_total = Decimal("0")
        for idx, line_data in enumerate(data["lines"], start=1):
            product = Product.objects.get(id=line_data["product_id"], company=self.company)
            quantity = Decimal(str(line_data["quantity"]))
            unit_price = Decimal(str(line_data["unit_price"]))
            vat_rate = Decimal(str(line_data.get("vat_rate", product.default_vat_rate)))

            amount_before_vat = quantity * unit_price
            vat_amount = (amount_before_vat * vat_rate).quantize(Decimal("0.0001"))
            amount = amount_before_vat + vat_amount

            SalesInvoiceLine.objects.create(
                invoice=invoice,
                line_no=idx,
                product=product,
                description=line_data.get("description", product.name),
                quantity=quantity,
                unit_id=product.unit_id,
                unit_price=unit_price,
                amount_before_vat=amount_before_vat,
                vat_rate=vat_rate,
                vat_amount=vat_amount,
                amount=amount,
                revenue_account=product.gl_account_revenue,
                vat_account="33311",
                inventory_account=product.gl_account_inv,
                cost_account=product.gl_account_cogs,
            )

            subtotal += amount_before_vat
            vat_total += vat_amount

        invoice.subtotal = subtotal
        invoice.vat_amount = vat_total
        invoice.total_amount = subtotal + vat_total
        invoice.save()

        if data.get("post", True):
            self._post(invoice)

        return invoice

    def _post(self, invoice: SalesInvoice) -> AccountingVoucher | DnsnVoucher:
        """Generate voucher for the invoice.

        Delegates to TT58 (DNSN) or standard TT133/TT200 posting.
        """
        if self.is_tt58:
            return self._post_tt58(invoice)
        return self._post_standard(invoice)

    # ------------------------------------------------------------------
    # TT133/TT200 standard posting (unchanged from original)
    # ------------------------------------------------------------------

    def _post_standard(self, invoice: SalesInvoice) -> AccountingVoucher:
        """Generate accounting voucher for the invoice (TT133/TT200)."""
        # 1. Create voucher header
        voucher = AccountingVoucher.objects.create(
            company=invoice.company,
            fiscal_year=invoice.invoice_date.year,
            period=invoice.invoice_date.month,
            voucher_no=invoice.invoice_no,
            voucher_type="sales_invoice",
            voucher_date=invoice.invoice_date,
            currency_code=invoice.currency_code,
            exchange_rate=invoice.exchange_rate,
            total_vnd=invoice.total_amount,
            status=AccountingVoucher.Status.DRAFT,
            source="sales_invoice",
            source_reference_id=invoice.id,
            description=f"Hóa đơn bán {invoice.invoice_no} - {invoice.customer.name}",
        )

        # 2. Build bút toán:
        #    N131 (customer AR): total_amount
        #    C5111 (revenue) per line: amount_before_vat
        #    C33311 (VAT output): vat_amount
        line_no = 1

        # N131 — full AR
        VoucherLine.objects.create(
            voucher=voucher,
            line_no=line_no,
            account_code=invoice.customer.gl_account_receivable,
            object_type="customer",
            object_code=invoice.customer.code,
            object_name=invoice.customer.name,
            debit_vnd=invoice.total_amount,
            description=f"Phải thu KH {invoice.customer.name}",
        )
        line_no += 1

        # C5111 per line + aggregate C33311
        vat_by_account = {}  # group VAT by account
        for inv_line in invoice.lines.all():
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=inv_line.revenue_account,
                credit_vnd=inv_line.amount_before_vat,
                description=f"DT bán {inv_line.product.name}",
            )
            line_no += 1

            vat_by_account.setdefault(inv_line.vat_account, Decimal("0"))
            vat_by_account[inv_line.vat_account] += inv_line.vat_amount

        # C33311 — VAT output (aggregated by account)
        for vat_acc, vat_amt in vat_by_account.items():
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=vat_acc,
                credit_vnd=vat_amt,
                description="VAT đầu ra",
            )
            line_no += 1

        # 3. Post voucher (validates N=C, updates balance)
        VoucherPostingService().post(voucher)

        # 4. Link + mark invoice as posted
        invoice.gl_voucher = voucher
        invoice.status = 2  # LEDGER
        invoice.save()

        return voucher

    # ------------------------------------------------------------------
    # TT58 DNSN posting
    # ------------------------------------------------------------------

    def _post_tt58(self, invoice: SalesInvoice) -> DnsnVoucher:
        """Generate DnsnVoucher + ledger entries for TT58 company.

        VAT handling depends on vat_method:
        - ty_le_phan_tram: revenue posted WITH VAT embedded, no separate VAT
          ledger entry. VAT is calculated as revenue × rate and posted to
          the revenue ledger (no TK 33311).
        - khau_tru: revenue posted WITHOUT VAT, VAT posted to S3b ledger
          (output VAT tracked separately).
        """
        group = self.company.tax_method_group

        # Create DnsnVoucher header
        voucher = DnsnVoucher.objects.create(
            company=invoice.company,
            fiscal_year=invoice.invoice_date.year,
            period=invoice.invoice_date.month,
            voucher_no=invoice.invoice_no,
            voucher_type=DnsnVoucher.VoucherType.HOA_DON_BAN_HANG,
            voucher_date=invoice.invoice_date,
            posting_date=invoice.invoice_date,
            description=f"Hóa đơn bán {invoice.invoice_no} - {invoice.customer.name}",
            partner_name=invoice.customer.name,
            invoice_no=invoice.invoice_no,
            invoice_date=invoice.invoice_date,
            status=DnsnVoucher.Status.DRAFT,
        )

        # Determine the revenue ledger_type based on tax_method_group
        revenue_ledger_type = self._get_revenue_ledger_type(group)

        # Build ledger entries based on vat_method
        entries = []
        if self.is_vat_percentage:
            # ty_le_phan_tram: revenue posted WITH VAT embedded.
            # The total_amount (including VAT) is recorded as revenue.
            # No separate VAT output entry (no TK 33311 equivalent).
            entries.append(
                {
                    "ledger_type": revenue_ledger_type,
                    "description": f"Doanh thu bán hàng (bao gồm VAT) - {invoice.customer.name}",
                    "partner_name": invoice.customer.name,
                    "revenue_amount": invoice.total_amount,
                    "vat_amount": invoice.vat_amount,  # informational, not posted separately
                }
            )
        else:
            # khau_tru: revenue posted WITHOUT VAT, VAT output posted to S3b.
            entries.append(
                {
                    "ledger_type": revenue_ledger_type,
                    "description": f"Doanh thu bán hàng - {invoice.customer.name}",
                    "partner_name": invoice.customer.name,
                    "revenue_amount": invoice.subtotal,
                }
            )
            # Output VAT to S3b ledger (Groups 3, 4)
            entries.append(
                {
                    "ledger_type": "s3b",
                    "description": f"Thuế GTGT đầu ra - {invoice.invoice_no}",
                    "partner_name": invoice.customer.name,
                    "vat_output": invoice.vat_amount,
                }
            )

        # Post via DnsnPostingService
        DnsnPostingService().post(voucher, entries=entries)

        # Link + mark invoice as posted
        invoice.dnsn_voucher = voucher
        invoice.status = 2  # LEDGER
        invoice.save()

        return voucher

    def _get_revenue_ledger_type(self, group: int) -> str:
        """Get the revenue ledger type for a tax method group.

        - Group 1: S1-DNSN (revenue only)
        - Group 2: S2a-DNSN (revenue)
        - Group 3: S3a-DNSN (revenue)
        - Group 4: S2b-DNSN (revenue/cost detail)
        """
        group_ledger_map = {
            1: "s1",
            2: "s2a",
            3: "s3a",
            4: "s2b",
        }
        return group_ledger_map.get(group, "s1")

    # ------------------------------------------------------------------
    # TNDN calculation helper
    # ------------------------------------------------------------------

    def calculate_tndn(
        self,
        revenue: Decimal | int | str,
        deductible_costs: Decimal | int | str = 0,
    ) -> dict:
        """Calculate TNDN tax using the company's tndn_method.

        - tndn_method='ty_le_phan_tram': tax = revenue × rate
        - tndn_method='tinh_thue': tax = (revenue - costs) × CIT rate
        """
        service = TndnCalculationService(self.company)
        return service.calculate(revenue, deductible_costs)

    @transaction.atomic
    def unpost(self, invoice: SalesInvoice) -> None:
        """Unpost invoice: unpost linked voucher + revert status."""
        # Handle TT58 DNSN voucher
        if invoice.dnsn_voucher_id:
            DnsnPostingService().unpost(invoice.dnsn_voucher)
            invoice.status = 0  # DRAFT
            invoice.save()
            return

        # Standard TT133/TT200 voucher
        if not invoice.gl_voucher:
            return
        VoucherPostingService().unpost(invoice.gl_voucher)
        invoice.status = 0  # DRAFT
        invoice.save()
