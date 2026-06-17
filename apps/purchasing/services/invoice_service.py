"""PurchaseInvoiceService — creates invoice + generates accounting voucher."""
from decimal import Decimal
from django.db import transaction

from apps.purchasing.models import PurchaseInvoice, PurchaseInvoiceLine
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.master_data.models import Vendor, Product


class PurchaseInvoiceService:
    """Service for creating/posting purchase invoices."""

    def __init__(self, company):
        self.company = company

    @transaction.atomic
    def create(self, data: dict) -> PurchaseInvoice:
        """Create invoice + (optional) auto-post voucher.

        data keys:
            invoice_no, invoice_date, vendor_id, purchaser_code, description,
            currency_code, exchange_rate,
            lines: list of {product_id, quantity, unit_price, vat_rate, ...}
            post: bool — auto-post voucher after creation (default True)
        """
        vendor = Vendor.objects.get(id=data['vendor_id'], company=self.company)

        invoice = PurchaseInvoice.objects.create(
            company=self.company,
            invoice_no=data['invoice_no'],
            invoice_date=data['invoice_date'],
            invoice_type=data.get('invoice_type', PurchaseInvoice.InvoiceType.GOODS),
            vendor=vendor,
            purchaser_code=data.get('purchaser_code', ''),
            currency_code=data.get('currency_code', 'VND'),
            exchange_rate=data.get('exchange_rate', Decimal('1')),
            description=data.get('description', ''),
            status=0,  # draft until posted
        )

        # Build lines + compute totals
        subtotal = Decimal('0')
        vat_total = Decimal('0')
        for idx, line_data in enumerate(data['lines'], start=1):
            product = Product.objects.get(id=line_data['product_id'], company=self.company)
            quantity = Decimal(str(line_data['quantity']))
            unit_price = Decimal(str(line_data['unit_price']))
            vat_rate = Decimal(str(line_data.get('vat_rate', product.default_vat_rate)))

            amount_before_vat = quantity * unit_price
            vat_amount = (amount_before_vat * vat_rate).quantize(Decimal('0.0001'))
            amount = amount_before_vat + vat_amount

            PurchaseInvoiceLine.objects.create(
                invoice=invoice,
                line_no=idx,
                product=product,
                description=line_data.get('description', product.name),
                quantity=quantity,
                unit_id=product.unit_id,
                unit_price=unit_price,
                amount_before_vat=amount_before_vat,
                vat_rate=vat_rate,
                vat_amount=vat_amount,
                amount=amount,
                inventory_account=product.gl_account_inv,
                vat_account='1331',
                cost_account=product.gl_account_cogs,
            )

            subtotal += amount_before_vat
            vat_total += vat_amount

        invoice.subtotal = subtotal
        invoice.vat_amount = vat_total
        invoice.total_amount = subtotal + vat_total
        invoice.save()

        if data.get('post', True):
            self._post(invoice)

        return invoice

    def _post(self, invoice: PurchaseInvoice) -> AccountingVoucher:
        """Generate accounting voucher for the purchase invoice.

        Bút toán:
            N156 (inventory) per line: amount_before_vat
            N1331 (VAT input) aggregated: sum(vat_amount) by account
            C331 (vendor AP): total_amount
        """
        # 1. Create voucher header
        voucher = AccountingVoucher.objects.create(
            company=invoice.company,
            fiscal_year=invoice.invoice_date.year,
            period=invoice.invoice_date.month,
            voucher_no=invoice.invoice_no,
            voucher_type='purchase_invoice',
            voucher_date=invoice.invoice_date,
            currency_code=invoice.currency_code,
            exchange_rate=invoice.exchange_rate,
            total_vnd=invoice.total_amount,
            status=AccountingVoucher.Status.DRAFT,
            source='purchase_invoice',
            source_reference_id=invoice.id,
            description=f'Hóa đơn mua {invoice.invoice_no} - {invoice.vendor.name}',
        )

        # 2. Build bút toán
        line_no = 1

        # C331 — full AP (vendor credit)
        VoucherLine.objects.create(
            voucher=voucher, line_no=line_no,
            account_code=invoice.vendor.gl_account_payable,
            object_type='vendor', object_code=invoice.vendor.code,
            object_name=invoice.vendor.name,
            credit_vnd=invoice.total_amount,
            description=f'Phải trả NCC {invoice.vendor.name}',
        )
        line_no += 1

        # N156 per line (inventory debit) + aggregate N1331
        vat_by_account = {}
        for inv_line in invoice.lines.all():
            VoucherLine.objects.create(
                voucher=voucher, line_no=line_no,
                account_code=inv_line.inventory_account,
                debit_vnd=inv_line.amount_before_vat,
                description=f'Nhập kho {inv_line.product.name}',
            )
            line_no += 1

            vat_by_account.setdefault(inv_line.vat_account, Decimal('0'))
            vat_by_account[inv_line.vat_account] += inv_line.vat_amount

        # N1331 — VAT input (aggregated by account, debit)
        for vat_acc, vat_amt in vat_by_account.items():
            VoucherLine.objects.create(
                voucher=voucher, line_no=line_no,
                account_code=vat_acc,
                debit_vnd=vat_amt,
                description='VAT đầu vào',
            )
            line_no += 1

        # 3. Post voucher (validates N=C, updates balance)
        VoucherPostingService().post(voucher)

        # 4. Link + mark invoice as posted
        invoice.gl_voucher = voucher
        invoice.status = 2  # LEDGER
        invoice.save()

        return voucher

    @transaction.atomic
    def unpost(self, invoice: PurchaseInvoice) -> None:
        """Unpost invoice: unpost linked voucher + revert status."""
        if not invoice.gl_voucher:
            return
        VoucherPostingService().unpost(invoice.gl_voucher)
        invoice.status = 0  # DRAFT
        invoice.save()
