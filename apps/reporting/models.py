"""Financial report configuration models.

FinancialReportLine drives the layout of the four statutory financial
statements (B01-DN, B02-DN, B03-DN direct/indirect) via a database table
instead of hard-coded Python line lists.  Each row describes a single
line on the report: its label, account-code pattern(s) to aggregate, an
optional formula referencing other lines, and display attributes.
"""

from django.db import models


class FinancialReportLine(models.Model):
    """Configuration row for a financial-statement report line.

    The four supported report types follow TT133/TT200 conventions:

    - ``B01-DN``           - Balance Sheet (Bảng cân đối kế toán)
    - ``B02-DN``           - Profit & Loss (Báo cáo kết quả HĐKD)
    - ``B03-DN-direct``    - Cash Flow, direct method
    - ``B03-DN-indirect``  - Cash Flow, indirect method

    A line carries zero or more of the following data sources (evaluated
    in order of precedence):

    1. ``cong_thuc`` - a formula expression like ``110+120+130+140``
       that references other ``ma_so`` values within the same report.
    2. ``tk_no_pattern`` / ``tk_co_pattern`` - wildcard account-code
       patterns (e.g. ``1331*`` or ``111``) aggregated from
       ``AccountPeriodBalance``.
    """

    REPORT_TYPES = [
        ("B01-DN", "Bảng cân đối kế toán (B01-DN)"),
        ("B02-DN", "Báo cáo kết quả HĐKD (B02-DN)"),
        ("B03-DN-direct", "BC dòng tiền PP trực tiếp (B03-DN)"),
        ("B03-DN-indirect", "BC dòng tiền PP gián tiếp (B03-DN)"),
    ]

    report_type = models.CharField(max_length=30, choices=REPORT_TYPES, db_index=True)
    stt = models.CharField(max_length=20, blank=True, default="")
    ma_so = models.CharField(max_length=20, blank=True, default="")
    chi_tieu = models.CharField(max_length=300)
    thuyet_minh = models.CharField(max_length=500, blank=True, default="")

    # Account-code patterns used for direct aggregation from balances.
    # Wildcard suffix ``*`` matches any continuation, e.g. ``1331*``.
    tk_no_pattern = models.CharField(max_length=100, blank=True, default="")
    tk_co_pattern = models.CharField(max_length=100, blank=True, default="")

    # Counterpart (offsetting) account-code pattern for the cash-flow
    # direct method.  A direct-method line aggregates the cash leg
    # (TK 111*/112*) but only for vouchers whose *other* leg hits an
    # account matching this pattern.  Comma-separated wildcards allowed,
    # e.g. ``511*,131*`` (cash from customers) or ``331*,152*`` (cash
    # paid to suppliers).  Empty means "no offset filter" (legacy
    # behaviour - aggregate the cash accounts unconditionally).
    tk_doi_ung_pattern = models.CharField(max_length=200, blank=True, default="")

    # Formula expression referencing other ``ma_so`` codes.
    # e.g. ``110+120+130+140`` or ``=511-632``.
    cong_thuc = models.CharField(max_length=500, blank=True, default="")

    # Optional subtraction formula (for lines that present a net figure
    # by subtracting one set of accounts from another).
    tinh_giam_tru = models.CharField(max_length=500, blank=True, default="")

    is_header = models.BooleanField(default=False)
    parent_ma_so = models.CharField(max_length=20, blank=True, default="")
    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reporting_financial_report_line"
        unique_together = [("report_type", "display_order")]
        ordering = ["report_type", "display_order"]
        indexes = [
            models.Index(fields=["report_type", "display_order"]),
        ]

    def __str__(self):
        return f"[{self.report_type}] {self.ma_so} - {self.chi_tieu[:50]}"


class VATReportLine(models.Model):
    """Configuration row for a single line on the VAT return (TT80/2021).

    Each row describes how to compute the value displayed at a given
    line code (e.g. ``21``, ``22``, ``28``).  The TT80 form layout is:

        Section A — Thông tin chung (header only, no data lines)
        Section B — Kê khai thuế GTGT
            I  — Hàng hóa, dịch vụ mua vào (input VAT)
            II — Hàng hóa, dịch vụ bán ra (output VAT)
        Section C — Thuế GTGT của hoạt động SXKD (payable / credit)

    Line value resolution (in precedence order):

    1. ``cong_thuc`` — formula expression like ``[25]+[26]-[27]``
       referencing sibling ``line_code`` values.  Constants are also
       supported (rarely used on TT80).
    2. Direct aggregation — sum ``tax_amount_vnd`` (or
       ``goods_amount_vnd`` for goods-value lines) over the posted
       ``VoucherLine`` rows that match the three filters below.
    3. Header / pure-label lines (``is_header=True`` and no formula or
       filters) — value is ``None`` (blank).
    """

    SECTIONS = [
        ("A", "A — Thông tin chung"),
        ("B-I", "B.I — Hàng hóa dịch vụ mua vào"),
        ("B-II", "B.II — Hàng hóa dịch vụ bán ra"),
        ("C", "C — Thuế GTGT của hoạt động SXKD"),
    ]

    line_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Mã dòng trên tờ khai, e.g. '21', '22', '40'.",
    )
    section = models.CharField(max_length=10, choices=SECTIONS, default="A")
    stt = models.CharField(max_length=20, blank=True, default="")
    chi_tieu = models.CharField(max_length=300)
    thuyet_minh = models.CharField(max_length=500, blank=True, default="")

    # Account-code wildcard (e.g. ``1331*`` or ``33311``).  Matches the
    # ``account_code`` column on ``VoucherLine``.
    tk_filter = models.CharField(max_length=100, blank=True, default="")
    # Invoice-group code (e.g. ``4`` INPUT or ``5`` OUTPUT).  Matches
    # ``invoice_group_code_id`` on ``VoucherLine``.  Empty = any group.
    invoice_group_filter = models.CharField(max_length=10, blank=True, default="")
    # Tax-rate code (e.g. ``00``, ``05``, ``10``).  Matches
    # ``tax_code_id`` on ``VoucherLine``.  Empty = any rate.
    tax_code_filter = models.CharField(max_length=10, blank=True, default="")

    # Which VoucherLine amount column to aggregate.
    AMOUNT_FIELD_CHOICES = [
        ("tax_amount_vnd", "Tiền thuế GTGT"),
        ("goods_amount_vnd", "Tiền hàng hóa/dịch vụ"),
        ("debit_vnd", "PS Nợ"),
        ("credit_vnd", "PS Có"),
    ]
    amount_field = models.CharField(
        max_length=30,
        choices=AMOUNT_FIELD_CHOICES,
        default="tax_amount_vnd",
    )

    # Formula referencing sibling line codes, e.g. ``[25]+[26]-[27]``.
    cong_thuc = models.CharField(max_length=500, blank=True, default="")

    is_header = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reporting_vat_report_line"
        ordering = ["display_order"]
        indexes = [
            models.Index(fields=["display_order"]),
        ]

    def __str__(self):
        return f"[{self.line_code}] {self.chi_tieu[:60]}"
