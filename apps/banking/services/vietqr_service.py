"""VietQR dynamic QR code URL builder.

VietQR.io API returns PNG images for scan-to-pay via Vietnamese banking apps.
Spec: https://vietqr.net/en/api-doc
"""

from urllib.parse import quote


class VietQRService:
    """Build VietQR API URLs for scan-to-pay."""

    BASE = "https://api.vietqr.io/img"
    DEFAULT_TEMPLATE = "compact"  # compact | qr_only | print

    # Bank name (or fragment) → Napas 6-digit BIN
    BANK_BINS = {
        "Vietcombank": "970436",
        "Vietinbank": "970415",
        "BIDV": "970424",
        "Agribank": "970405",
        "ACB": "970416",
        "MB Bank": "970422",
        "Techcombank": "970407",
        "VPBank": "970432",
        "TPBank": "970423",
        "Sacombank": "970429",
        "VietABank": "970427",
        "OCB": "970448",
        "BacABank": "970409",
        "SHB": "970443",
        "OceanBank": "970414",
        "HDBank": "970437",
        "NamABank": "970428",
        "PVcomBank": "970412",
        "BaoVietBank": "970438",
        "SeABank": "970418",
        "VIB": "970441",
        "LienVietPostBank": "970449",
        "Eximbank": "970434",
        "VietBank": "970433",
        "KienLongBank": "970452",
        "GPBank": "970408",
        "CBBank": "970404",
        "CoopBank": "970446",
        "CapitalBank": "970426",
        "DBank": "970454",
    }

    class UnsupportedBankError(Exception):
        """Bank name not in our BIN mapping."""

    def build_url(self, bank_account, amount, memo, template=None) -> str:
        """Build VietQR PNG URL for the given bank account + payment info.

        Args:
            bank_account: BankAccount instance (uses bank_name + account_number).
            amount: Decimal or int — total amount to receive.
            memo: payment memo / addInfo (max 34 chars after URL-encode, will be truncated).
            template: VietQR template name; default 'compact'.

        Returns: full URL to fetch PNG from api.vietqr.io.
        """
        bin_code = self._resolve_bin(bank_account.bank_name)
        template = template or self.DEFAULT_TEMPLATE
        memo_safe = (memo or "")[:34]
        params = f"?amount={int(amount)}&addInfo={quote(memo_safe)}&template={template}"
        return f"{self.BASE}/{bin_code}/{bank_account.account_number}{params}"

    def _resolve_bin(self, bank_name: str) -> str:
        """Match bank_name against BANK_BINS keys (case-insensitive partial).

        Match strategy: check if any key is a substring of bank_name (or vice versa).
        E.g., 'Ngân hàng VCB - Vietcombank' contains 'Vietcombank' → match.
        """
        if not bank_name:
            raise self.UnsupportedBankError("Empty bank name")
        name_norm = bank_name.lower().strip()
        for key, bin_code in self.BANK_BINS.items():
            key_lower = key.lower()
            if key_lower in name_norm or name_norm in key_lower:
                return bin_code
        raise self.UnsupportedBankError(
            f"Bank '{bank_name}' not in VietQR mapping. Add BIN to VietQRService.BANK_BINS."
        )

    def build_memo(self, invoice_no: str, customer_code: str = "") -> str:
        """Generate payment memo. VietQR addInfo max is 34 chars.

        Format: 'INV <invoice_no> <customer_code>' (truncated if needed).
        """
        prefix = "INV "
        if customer_code:
            max_invoice_len = 34 - len(prefix) - 1 - len(customer_code)
            invoice_trunc = (invoice_no or "")[: max(max_invoice_len, 1)]
            memo = f"{prefix}{invoice_trunc} {customer_code}"
        else:
            max_invoice_len = 34 - len(prefix)
            invoice_trunc = (invoice_no or "")[: max(max_invoice_len, 1)]
            memo = f"{prefix}{invoice_trunc}"
        return memo[:34]
