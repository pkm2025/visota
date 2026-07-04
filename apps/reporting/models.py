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
