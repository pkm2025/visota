"""E-invoice issue + reporting services.

EInvoiceService.issue_from_sales_invoice(): generates XML per TT78 schema,
stores files, optionally calls provider API.
"""

import json
from datetime import datetime
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

from apps.notifications.services import NotificationService

from apps.einvoice.models import EInvoice, EInvoiceConfig, EInvoiceProvider, EInvoiceReportBatch


class EInvoiceIssueError(Exception):
    pass


def amount_in_words(amount: Decimal) -> str:
    """Convert amount to Vietnamese words. Simplified — replace with proper lib."""
    if not amount:
        return "Không đồng"
    # Truncated to integer for words
    n = int(amount)
    if n == 0:
        return "Không đồng"

    units = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
    tiers = [("", "đồng"), ("nghìn", ""), ("triệu", ""), ("tỷ", "")]

    def three_digits(num):
        """Read 3 digits in Vietnamese."""
        out = []
        tr, ch, dv = num // 100, (num // 10) % 10, num % 10
        if tr:
            out.append(units[tr] + " trăm")
            if ch == 0 and dv != 0:
                out.append("lẻ")
        if ch == 1 and tr:
            out.append("mười")
        elif ch:
            out.append(units[ch] + " mươi")
            if dv == 5 and ch:
                out.append("lăm")
        if dv and dv != 5:
            if ch == 0 and tr:
                out.append(units[dv])
            elif not out or units[dv] != "một":
                out.append(units[dv])
            elif units[dv] == "một" and ch != 0 and ch != 1:
                out.append("mốt")
        return " ".join(filter(None, out))

    parts = []
    tier_idx = 0
    while n > 0:
        chunk = n % 1000
        if chunk:
            tier_name = tiers[tier_idx][0] if tier_idx < len(tiers) else ""
            parts.append(three_digits(chunk) + ((" " + tier_name) if tier_name else ""))
        n //= 1000
        tier_idx += 1

    return " ".join(reversed(parts)).capitalize() + " đồng"


class EInvoiceService:
    """Issue / adjust / cancel e-invoices."""

    @staticmethod
    def get_config(company):
        config = EInvoiceConfig.objects.filter(
            company=company, is_active=True
        ).first()
        if not config:
            # Auto-create with defaults (manual mode)
            config = EInvoiceConfig.objects.create(company=company)
        return config

    @classmethod
    def issue_from_sales_invoice(cls, sales_invoice, issued_by=None):
        """Create a draft EInvoice from a SalesInvoice + populate parties/amounts."""
        config = cls.get_config(sales_invoice.company)

        # Snapshot seller (company)
        seller = sales_invoice.company
        # Snapshot buyer (customer)
        buyer = sales_invoice.customer
        buyer_name = buyer.name if buyer else ""
        buyer_tax = buyer.tax_code if buyer else ""
        buyer_addr = buyer.address if buyer else ""

        subtotal = sales_invoice.subtotal or Decimal("0")
        vat = sales_invoice.vat_amount or Decimal("0")
        total = sales_invoice.total_amount or Decimal("0")
        avg_vat_rate = (
            (vat / subtotal * Decimal("100")) if subtotal else Decimal("0")
        )

        ei = EInvoice.objects.create(
            company=sales_invoice.company,
            sales_invoice=sales_invoice,
            pattern=config.pattern,
            serial=config.serial,
            buyer_name=buyer_name,
            buyer_tax_code=buyer_tax,
            buyer_address=buyer_addr,
            seller_name=seller.name,
            seller_tax_code=seller.tax_code or "",
            seller_address=seller.address or "",
            subtotal=subtotal,
            vat_rate=avg_vat_rate / Decimal("100"),
            vat_amount=vat,
            total_amount=total,
            total_in_words=amount_in_words(total),
            payment_method="Tiền mặt/Chuyển khoản",
            status=EInvoice.Status.DRAFT,
            issued_by=issued_by,
        )

        # Generate XML payload (TT78 schema, simplified)
        xml = cls._build_xml(ei, sales_invoice)
        ei.xml_file.save(f"{ei.transaction_id}.xml", ContentFile(xml.encode("utf-8")))

        # Generate JSON (for API-driven providers)
        payload = cls._build_json(ei, sales_invoice)
        ei.json_file.save(
            f"{ei.transaction_id}.json", ContentFile(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
        )

        ei.save()
        return ei

    @classmethod
    def publish(cls, einvoice, invoice_no=None):
        """Mark as issued. For manual mode just assigns a number; for API mode calls provider."""
        config = cls.get_config(einvoice.company)
        if not invoice_no:
            invoice_no = cls._next_invoice_no(einvoice.company, config)

        einvoice.invoice_no = invoice_no
        einvoice.issue_date = timezone.now()
        einvoice.status = EInvoice.Status.ISSUED

        if config.provider == EInvoiceProvider.MANUAL:
            # Just save — operator uploads signed PDF manually
            einvoice.provider_response = {"mode": "manual"}
            einvoice.save()
        else:
            # Call provider API — stubbed. Real impl would call MISA/VNPT/etc.
            try:
                resp = cls._call_provider_api(config, einvoice)
                einvoice.provider_response = resp
            except Exception as e:
                einvoice.error_message = str(e)[:500]
                einvoice.provider_response = {"error": str(e)}
                einvoice.save()
                raise EInvoiceIssueError(str(e))

        einvoice.save()

        # Notify sales staff + accounting
        try:
            NotificationService.send_to_superusers(
                company=einvoice.company,
                type="success",
                title=f"Đã phát hành HĐĐT {einvoice.invoice_no}",
                message=(
                    f"Hóa đơn điện tử {einvoice.invoice_no} đã được phát hành cho "
                    f"{einvoice.buyer_name}, tổng {einvoice.total_amount:,.0f} VND."
                ),
                url=f"/modern/einvoices/{einvoice.id}/",
                related_object_type="einvoice.einvoice",
                related_object_id=einvoice.id,
            )
        except Exception:
            pass

        # Auto-generate human-readable PDF for download/email (best-effort)
        try:
            from apps.einvoice.services.einvoice_pdf_service import EInvoicePDFService
            EInvoicePDFService().get_or_generate(einvoice, force=True)
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                "PDF auto-gen failed for einvoice %s", einvoice.pk, exc_info=True
            )
        return einvoice

    @classmethod
    def cancel(cls, einvoice, reason, cancelled_by=None):
        """Cancel an issued invoice (Hóa đơn bị lỗi)."""
        einvoice.status = EInvoice.Status.CANCELLED
        einvoice.error_message = reason
        einvoice.note = f"Hủy: {reason}"
        einvoice.save()

    @classmethod
    def adjust(cls, original, reason, adjusted_by=None):
        """Create an adjusting invoice (Hóa đơn điều chỉnh)."""
        ei = EInvoice.objects.create(
            company=original.company,
            sales_invoice=original.sales_invoice,
            replaces_invoice=original,
            adjustment_type="adjust",
            pattern=original.pattern,
            serial=original.serial,
            buyer_name=original.buyer_name,
            buyer_tax_code=original.buyer_tax_code,
            buyer_address=original.buyer_address,
            seller_name=original.seller_name,
            seller_tax_code=original.seller_tax_code,
            seller_address=original.seller_address,
            subtotal=-original.subtotal,
            vat_rate=original.vat_rate,
            vat_amount=-original.vat_amount,
            total_amount=-original.total_amount,
            total_in_words="Điều chỉnh: " + amount_in_words(abs(original.total_amount)),
            note=f"Điều chỉnh {original.invoice_no}: {reason}",
            status=EInvoice.Status.DRAFT,
            issued_by=adjusted_by,
        )
        return ei

    @staticmethod
    def _next_invoice_no(company, config):
        """Generate sequential invoice number for the period."""
        today = timezone.now()
        count = EInvoice.objects.filter(
            company=company,
            issue_date__year=today.year,
            issue_date__month=today.month,
            status__in=[EInvoice.Status.ISSUED, EInvoice.Status.ADJUSTED],
        ).count()
        return f"{config.serial}{today.strftime('%y%m')}{count + 1:06d}"

    @staticmethod
    def _build_xml(einvoice, sales_invoice):
        """Build XML per TT78 schema (simplified)."""
        lines_xml = []
        for idx, line in enumerate(sales_invoice.lines.all(), 1):
            lines_xml.append(f"""
        <Item>
            <LineNumber>{idx}</LineNumber>
            <ItemName>{line.description}</ItemName>
            <Unit>{line.unit_id}</Unit>
            <Quantity>{line.quantity}</Quantity>
            <Price>{line.unit_price}</Price>
            <Amount>{line.amount_before_vat}</Amount>
            <VATRate>{float(line.vat_rate) * 100}</VATRate>
            <VATAmount>{line.vat_amount}</VATAmount>
        </Item>""")
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice>
    <TransactionID>{einvoice.transaction_id}</TransactionID>
    <Pattern>{einvoice.pattern}</Pattern>
    <Serial>{einvoice.serial}</Serial>
    <InvoiceDate>{timezone.now().isoformat()}</InvoiceDate>
    <Seller>
        <Name>{einvoice.seller_name}</Name>
        <TaxCode>{einvoice.seller_tax_code}</TaxCode>
        <Address>{einvoice.seller_address}</Address>
    </Seller>
    <Buyer>
        <Name>{einvoice.buyer_name}</Name>
        <TaxCode>{einvoice.buyer_tax_code}</TaxCode>
        <Address>{einvoice.buyer_address}</Address>
    </Buyer>
    <Items>
        {"".join(lines_xml)}
    </Items>
    <Summary>
        <Subtotal>{einvoice.subtotal}</Subtotal>
        <VATAmount>{einvoice.vat_amount}</VATAmount>
        <TotalAmount>{einvoice.total_amount}</TotalAmount>
        <TotalInWords>{einvoice.total_in_words}</TotalInWords>
    </Summary>
</Invoice>"""

    @staticmethod
    def _build_json(einvoice, sales_invoice):
        return {
            "transactionId": str(einvoice.transaction_id),
            "pattern": einvoice.pattern,
            "serial": einvoice.serial,
            "seller": {
                "name": einvoice.seller_name,
                "taxCode": einvoice.seller_tax_code,
                "address": einvoice.seller_address,
            },
            "buyer": {
                "name": einvoice.buyer_name,
                "taxCode": einvoice.buyer_tax_code,
                "address": einvoice.buyer_address,
            },
            "items": [
                {
                    "lineNumber": idx,
                    "itemName": line.description,
                    "unit": line.unit_id,
                    "quantity": float(line.quantity),
                    "price": float(line.unit_price),
                    "amount": float(line.amount_before_vat),
                    "vatRate": float(line.vat_rate),
                    "vatAmount": float(line.vat_amount),
                }
                for idx, line in enumerate(sales_invoice.lines.all(), 1)
            ],
            "summary": {
                "subtotal": float(einvoice.subtotal),
                "vatAmount": float(einvoice.vat_amount),
                "totalAmount": float(einvoice.total_amount),
                "totalInWords": einvoice.total_in_words,
            },
        }

    @staticmethod
    def _call_provider_api(config, einvoice):
        """Stub — real implementation calls provider REST API."""
        # Example stub: just echo back
        return {
            "provider": config.provider,
            "statusCode": "success",
            "invoiceNo": einvoice.invoice_no,
            "transactionId": str(einvoice.transaction_id),
            "timestamp": timezone.now().isoformat(),
        }


class EInvoiceReportService:
    """Generate BC01/BC26 reports for tax authority submission."""

    @staticmethod
    def generate_bc01(company, month, year, submitted_by=None):
        """BC01 — usage situation report for given month."""
        from calendar import monthrange
        from datetime import datetime

        # Use range filter (avoids CONVERT_TZ needed for __year/__month on tz-aware fields)
        first_day = datetime(year, month, 1)
        last_day_num = monthrange(year, month)[1]
        # Range covers entire month inclusive
        last_day = datetime(year, month, last_day_num, 23, 59, 59)
        qs = EInvoice.objects.filter(
            company=company,
            issue_date__gte=first_day,
            issue_date__lte=last_day,
            status__in=[EInvoice.Status.ISSUED, EInvoice.Status.ADJUSTED],
        )
        batch = EInvoiceReportBatch.objects.create(
            company=company,
            report_type=EInvoiceReportBatch.ReportType.BC01,
            period_month=month,
            period_year=year,
            invoice_count=qs.count(),
            total_amount=sum((e.total_amount for e in qs), Decimal("0")),
            submitted_by=submitted_by,
            submitted_at=timezone.now(),
            status="submitted",
        )
        # Generate XML
        lines = "\n".join(
            f"""
        <Invoice>
            <InvoiceNo>{e.invoice_no}</InvoiceNo>
            <Pattern>{e.pattern}</Pattern>
            <Serial>{e.serial}</Serial>
            <IssueDate>{e.issue_date.isoformat()}</IssueDate>
            <BuyerName>{e.buyer_name}</BuyerName>
            <BuyerTaxCode>{e.buyer_tax_code}</BuyerTaxCode>
            <TotalAmount>{e.total_amount}</TotalAmount>
            <VATAmount>{e.vat_amount}</VATAmount>
            <Status>{e.status}</Status>
        </Invoice>"""
            for e in qs
        )
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BC01>
    <ReportPeriod>{month:02d}/{year}</ReportPeriod>
    <Company>
        <Name>{company.name}</Name>
        <TaxCode>{company.tax_code}</TaxCode>
    </Company>
    <Invoices>{lines}
    </Invoices>
    <Total><Count>{qs.count()}</Count><Amount>{batch.total_amount}</Amount></Total>
</BC01>"""
        batch.xml_file.save(
            f"BC01_{year}{month:02d}.xml", ContentFile(xml.encode("utf-8"))
        )
        batch.save()
        return batch
