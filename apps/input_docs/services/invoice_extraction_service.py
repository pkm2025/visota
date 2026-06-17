"""InvoiceExtractionService — parse Vietnamese invoices + auto-create PI."""

import re
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
from xml.etree.ElementTree import ParseError

from django.db import transaction
from django.utils import timezone

from apps.input_docs.models import InputInvoice
from apps.master_data.models import Vendor
from apps.purchasing.services import PurchaseInvoiceService


# Vietnamese number normalization: "1.234.567" → 1234567
def _to_decimal(raw: str) -> Decimal:
    if raw is None:
        return Decimal("0")
    cleaned = raw.strip().replace(" ", "").replace("\xa0", "")
    # Remove currency symbols / suffixes
    cleaned = re.sub(r"[^0-9,.\-]", "", cleaned)
    if not cleaned:
        return Decimal("0")
    # If contains both '.' and ',' assume '.' is thousand sep (vi-VN)
    if "." in cleaned and "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned and "." not in cleaned:
        # Could be decimal comma (vi-VN) — convert to dot
        cleaned = cleaned.replace(",", ".")
    elif "." in cleaned:
        # If multiple dots → thousand separators
        if cleaned.count(".") > 1:
            cleaned = cleaned.replace(".", "")
        else:
            # Single dot — ambiguous, leave as decimal
            pass
    try:
        return Decimal(cleaned)
    except Exception:
        return Decimal("0")


class InvoiceExtractionService:
    """Extract structured data from uploaded invoice files (text/XML).

    Vietnamese invoice formats covered:
        - Plain-text dumps (from PDF OCR): MST, invoice_no, date, amounts
        - TCT e-invoice XML (HoaDon/TTChung/TToan)
    """

    def __init__(self, company):
        self.company = company

    # ---------- TEXT ----------
    def extract_from_text(self, text: str) -> dict:
        """Parse plain Vietnamese invoice text via regex."""
        if not text:
            return {}

        # MST (10-digit tax code) — appear after "Mã số thuế" or "MST"
        tax = ""
        m = re.search(r"M[ãa]\s*s[ốo]\s*thu[ếe][:\s]*([0-9]{10})", text, re.IGNORECASE)
        if not m:
            m = re.search(r"\bMST[:\s]*([0-9]{10})\b", text, re.IGNORECASE)
        if m:
            tax = m.group(1)

        # Invoice number — "Số:" / "SHDon" or "Số hóa đơn"
        invoice_no = ""
        m = re.search(r"S[ốo]\s*(?:hóa\s*đơn)?[:\s#]*([0-9A-Z]{4,})", text, re.IGNORECASE)
        if m:
            invoice_no = m.group(1)

        # Date — formats dd/mm/yyyy or yyyy-mm-dd
        date_val = None
        m = re.search(
            r"Ng[àa]y[:\s]*([0-9]{1,2})[/-]([0-9]{1,2})[/-]([0-9]{4})",
            text,
            re.IGNORECASE,
        )
        if m:
            d, mo, y = (int(x) for x in m.groups())
            try:
                date_val = datetime(y, mo, d).date()
            except ValueError:
                date_val = None
        if not date_val:
            m = re.search(r"([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})", text)
            if m:
                y, mo, d = (int(x) for x in m.groups())
                try:
                    date_val = datetime(y, mo, d).date()
                except ValueError:
                    date_val = None

        # Seller name — "Đơn vị bán" / "Nhà cung cấp" / "Người bán"
        seller_name = ""
        m = re.search(
            r"(?:Đơn vị bán|Nhà cung cấp|Người bán|Seller)[:\s]*([^\n\r]+)",
            text,
            re.IGNORECASE,
        )
        if m:
            seller_name = m.group(1).strip().rstrip(",").strip()

        # Seller address
        seller_address = ""
        m = re.search(r"Địa chỉ[:\s]*([^\n\r]+)", text, re.IGNORECASE)
        if m:
            seller_address = m.group(1).strip()

        # Amounts — look for keywords.  Order matters: total > vat > subtotal.
        total_amount = Decimal("0")
        m = re.search(
            r"(?:TỔNG\s*CỘNG|Tổng\s*cộng thanh toán|THANH TIỀN|Thanh toán)[:\s]*"
            r"([0-9][0-9.,]*)",
            text,
            re.IGNORECASE,
        )
        if m:
            total_amount = _to_decimal(m.group(1))

        vat_amount = Decimal("0")
        m = re.search(
            r"(?:Tiền thuế GTGT|Ti[ềe]n thu[ếe]|GTGT)[:\s]*([0-9][0-9.,]*)",
            text,
            re.IGNORECASE,
        )
        if m:
            vat_amount = _to_decimal(m.group(1))

        amount_before_vat = Decimal("0")
        m = re.search(
            r"(?:Thành tiền|Cộng tiền hàng|Tổng tiền hàng)[:\s]*([0-9][0-9.,]*)",
            text,
            re.IGNORECASE,
        )
        if m:
            amount_before_vat = _to_decimal(m.group(1))

        # VAT rate — "10%" or "(10%)"
        vat_rate = Decimal("0")
        m = re.search(r"\(([0-9]{1,2})\s*%\)", text)
        if not m:
            m = re.search(r"GTGT[^0-9]*([0-9]{1,2})\s*%", text, re.IGNORECASE)
        if m:
            vat_rate = (Decimal(m.group(1)) / Decimal("100")).quantize(Decimal("0.0001"))

        # Fallbacks / cross-checks
        if total_amount == 0 and amount_before_vat > 0:
            total_amount = amount_before_vat + vat_amount
        if amount_before_vat == 0 and total_amount > 0 and vat_amount > 0:
            amount_before_vat = total_amount - vat_amount
        if vat_rate == 0 and amount_before_vat > 0 and vat_amount > 0:
            vat_rate = (vat_amount / amount_before_vat).quantize(Decimal("0.0001"))

        return {
            "invoice_no": invoice_no,
            "invoice_date": date_val,
            "seller_tax_code": tax,
            "seller_name": seller_name,
            "seller_address": seller_address,
            "amount_before_vat": amount_before_vat,
            "vat_rate": vat_rate,
            "vat_amount": vat_amount,
            "total_amount": total_amount,
            "currency_code": "VND",
        }

    # ---------- XML ----------
    def extract_from_xml(self, xml_string: str) -> dict:
        """Parse TCT e-invoice XML.

        Expected schema (typical VN e-invoice):
            <HoaDon>
              <TTChung>
                <KHDon>,<SHDon>,<NLap>,<MST>
              </TTChung>
              <NDHDon><NDBan><Ten>...</Ten></NDBan></NDHDon>
              <TToan>
                <TgTThue>200000</TgTThue>  (subtotal before VAT)
                <TgTGTGT>20000</TgTGTGT>   (VAT amount)
                <TgTTTBSo>220000</TgTTTBSo> (total)
                <TSuat>10</TSuat>          (VAT rate %)
              </TToan>
            </HoaDon>
        """
        if not xml_string:
            return {}
        try:
            root = ET.fromstring(xml_string)
        except ParseError:
            return {}

        def find_text(parent, tag):
            el = parent.find(f".//{tag}")
            return el.text.strip() if el is not None and el.text else ""

        ttc = root.find(".//TTChung")
        if ttc is None:
            ttc = root
        invoice_no = find_text(ttc, "SHDon")
        date_raw = find_text(ttc, "NLap")
        tax = find_text(ttc, "MST")

        # Some XMLs put MST under NDBan / Seller
        if not tax:
            tax = find_text(root, "MST")

        date_val = None
        if date_raw:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
                try:
                    date_val = datetime.strptime(date_raw[:19], fmt).date()
                    break
                except ValueError:
                    continue

        seller_name = find_text(root, "Ten") or find_text(root, "NDBan/Ten")
        # Try NDHDon/NDBan/Ten first
        ndban = root.find(".//NDBan")
        if ndban is not None:
            ten_el = ndban.find("Ten")
            if ten_el is not None and ten_el.text:
                seller_name = ten_el.text.strip()

        ttoan = root.find(".//TToan")
        subtotal = _to_decimal(find_text(ttoan, "TgTThue") if ttoan is not None else "")
        # Fallback to TgTHang (sum of line amounts)
        if subtotal == 0:
            subtotal = _to_decimal(find_text(ttoan, "TgTHang") if ttoan is not None else "")
        vat_amount = _to_decimal(find_text(ttoan, "TgTGTGT") if ttoan is not None else "")
        total_amount = _to_decimal(find_text(ttoan, "TgTTTBSo") if ttoan is not None else "")

        # VAT rate — TSuat can be "10" or "10%"
        tsuat = find_text(ttoan, "TSuat") if ttoan is not None else ""
        vat_rate = Decimal("0")
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)", tsuat)
        if m:
            vat_rate = (Decimal(m.group(1)) / Decimal("100")).quantize(Decimal("0.0001"))

        if total_amount == 0 and subtotal > 0:
            total_amount = subtotal + vat_amount

        return {
            "invoice_no": invoice_no,
            "invoice_date": date_val,
            "seller_tax_code": tax,
            "seller_name": seller_name,
            "amount_before_vat": subtotal,
            "vat_rate": vat_rate,
            "vat_amount": vat_amount,
            "total_amount": total_amount,
            "currency_code": "VND",
        }

    # ---------- AUTO-CREATE PI ----------
    @transaction.atomic
    def auto_create_purchase_invoice(
        self, input_invoice: InputInvoice, product_id: int | None = None
    ) -> object:
        """From extracted data, find/create Vendor + create PI + auto-post.

        Requires ``product_id`` to build a single line for the PI (the
        InputInvoice itself doesn't carry product detail).
        """
        if product_id is None:
            raise ValueError("product_id is required to auto-create PI")

        # 1. Find or create Vendor
        vendor = None
        if input_invoice.seller_tax_code:
            vendor = Vendor.objects.filter(
                company=self.company, tax_code=input_invoice.seller_tax_code
            ).first()
        if vendor is None:
            # generate vendor code from tax code or invoice_no
            base = input_invoice.seller_tax_code or (input_invoice.invoice_no or "VND")
            vcode = f"NCC_{base}"[:50]
            # ensure uniqueness
            n = 1
            while Vendor.objects.filter(company=self.company, code=vcode).exists():
                vcode = f"NCC_{base}_{n}"[:50]
                n += 1
            vendor = Vendor.objects.create(
                company=self.company,
                code=vcode,
                name=input_invoice.seller_name or vcode,
                tax_code=input_invoice.seller_tax_code,
                address=input_invoice.seller_address or "",
            )

        # 2. Build PI via PurchaseInvoiceService
        unit_price = input_invoice.amount_before_vat or Decimal("0")
        vat_rate = input_invoice.vat_rate or Decimal("0")
        if unit_price == 0 and input_invoice.total_amount:
            # derive unit_price from total minus vat
            unit_price = input_invoice.total_amount - (input_invoice.vat_amount or Decimal("0"))

        svc = PurchaseInvoiceService(company=self.company)
        pi = svc.create(
            {
                "invoice_no": input_invoice.invoice_no,
                "invoice_date": input_invoice.invoice_date,
                "vendor_id": vendor.id,
                "lines": [
                    {
                        "product_id": product_id,
                        "quantity": Decimal("1"),
                        "unit_price": unit_price,
                        "vat_rate": vat_rate,
                    }
                ],
                "post": True,
            }
        )

        # 3. Link InputInvoice
        input_invoice.purchase_invoice = pi
        input_invoice.extraction_status = InputInvoice.ExtractionStatus.MATCHED
        input_invoice.processed_at = timezone.now()
        input_invoice.save()

        return pi
