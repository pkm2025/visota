"""SalesInvoiceService — creates invoice + generates accounting voucher."""
from decimal import Decimal
from django.db import transaction

from apps.sales.models import SalesInvoice, SalesInvoiceLine
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.master_data.models import Customer, Product


class SalesInvoiceService:
    """Service for creating/posting sales invoices."""

    def __init__(self, company):
        self.company = company

    @transaction.atomic
    def create(self, data: dict) -> SalesInvoice:
        """Create invoice + (optional) auto-post voucher.

        data keys:
            invoice_no, invoice_date, customer_id, sales_staff_code, description,
            currency_code, exchange_rate,
            lines: list of {product_id, quantity, unit_price, vat_rate, ...}
            post: bool — auto-post voucher after creation (default True)
        """
        customer = Customer.objects.get(id=data['customer_id'], company=self.company)

        invoice = SalesInvoice.objects.create(
            company=self.company,
            invoice_no=data['invoice_no'],
            invoice_date=data['invoice_date'],
            invoice_type=data.get('invoice_type', SalesInvoice.InvoiceType.GOODS),
            customer=customer,
            sales_staff_code=data.get('sales_staff_code', ''),
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

            SalesInvoiceLine.objects.create(
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
                revenue_account=product.gl_account_revenue,
                vat_account='33311',
                inventory_account=product.gl_account_inv,
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

    def _post(self, invoice: SalesInvoice) -> AccountingVoucher:
        """Generate accounting voucher for the invoice."""
        # 1. Create voucher header
        voucher = AccountingVoucher.objects.create(
            company=invoice.company,
            fiscal_year=invoice.invoice_date.year,
            period=invoice.invoice_date.month,
            voucher_no=invoice.invoice_no,
            voucher_type='sales_invoice',
            voucher_date=invoice.invoice_date,
            currency_code=invoice.currency_code,
            exchange_rate=invoice.exchange_rate,
            total_vnd=invoice.total_amount,
            status=AccountingVoucher.Status.DRAFT,
            source='sales_invoice',
            source_reference_id=invoice.id,
            description=f'Hóa đơn bán {invoice.invoice_no} - {invoice.customer.name}',
        )

        # 2. Build bút toán:
        #    N131 (customer AR): total_amount
        #    C5111 (revenue) per line: amount_before_vat
        #    C33311 (VAT output): vat_amount
        line_no = 1

        # N131 — full AR
        VoucherLine.objects.create(
            voucher=voucher, line_no=line_no,
            account_code=invoice.customer.gl_account_receivable,
            object_type='customer', object_code=invoice.customer.code,
            object_name=invoice.customer.name,
            debit_vnd=invoice.total_amount,
            description=f'Phải thu KH {invoice.customer.name}',
        )
        line_no += 1

        # C5111 per line + aggregate C33311
        vat_by_account = {}  # group VAT by account
        for inv_line in invoice.lines.all():
            VoucherLine.objects.create(
                voucher=voucher, line_no=line_no,
                account_code=inv_line.revenue_account,
                credit_vnd=inv_line.amount_before_vat,
                description=f'DT bán {inv_line.product.name}',
            )
            line_no += 1

            vat_by_account.setdefault(inv_line.vat_account, Decimal('0'))
            vat_by_account[inv_line.vat_account] += inv_line.vat_amount

        # C33311 — VAT output (aggregated by account)
        for vat_acc, vat_amt in vat_by_account.items():
            VoucherLine.objects.create(
                voucher=voucher, line_no=line_no,
                account_code=vat_acc,
                credit_vnd=vat_amt,
                description='VAT đầu ra',
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
    def unpost(self, invoice: SalesInvoice) -> None:
        """Unpost invoice: unpost linked voucher + revert status."""
        if not invoice.gl_voucher:
            return
        VoucherPostingService().unpost(invoice.gl_voucher)
        invoice.status = 0  # DRAFT
        invoice.save()
