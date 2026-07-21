"""CTGS (Chứng từ ghi sổ) workflow views and department master.

CTGS is the "book entry" accounting method where subsidiary transactions
are summarized into book entries that are then posted to the general ledger.

Workflow:
  1. Khai báo CTGS — create book entries from subsidiary vouchers
  2. Đăng ký CTGS — register (sequential numbering)
  3. Kiểm tra CTGS — validate (debit=credit check)
  4. Bảng kê CT gốc (S04-H) — list source documents by type
"""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ui_modern.mixins import require_current_company
from apps.ui_modern.views.report_views import _common_period_choices, _parse_period_kwargs


class CTGSCreateView(LoginRequiredMixin, TemplateView):
    """Khai báo chứng từ ghi sổ — create book entries from subsidiary vouchers.

    Lists all subsidiary vouchers (cash, sales, purchase) that have been posted
    to the ledger and allows creating CTGS summary entries.
    """

    template_name = "modern/tools/ctgs_workflow.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, period = _parse_period_kwargs(self.request)
        company = require_current_company(self.request)

        # Show subsidiary vouchers ready for CTGS creation
        vouchers = (
            AccountingVoucher.objects.filter(
                company=company,
                fiscal_year=fy,
                period=period,
                status__gte=AccountingVoucher.Status.LEDGER,
            )
            .exclude(voucher_type="closing")
            .order_by("voucher_date", "voucher_no")
        )

        rows = []
        for v in vouchers:
            totals = v.lines.aggregate(d=Sum("debit_vnd"), c=Sum("credit_vnd"))
            rows.append(
                {
                    "voucher_no": v.voucher_no,
                    "voucher_date": v.voucher_date,
                    "voucher_type": v.get_voucher_type_display(),
                    "description": v.description,
                    "debit_total": totals["d"] or Decimal("0"),
                    "credit_total": totals["c"] or Decimal("0"),
                    "is_balanced": (totals["d"] or 0) == (totals["c"] or 0),
                    "ctgs_status": "registered" if v.book_code else "pending",
                }
            )

        ctx.update(
            {
                "page_title": "Khai báo chứng từ ghi sổ",
                "fiscal_year": fy,
                "period": period,
                "rows": rows,
                "step": "create",
                **_common_period_choices(),
            }
        )
        return ctx


class CTGSRegisterView(LoginRequiredMixin, TemplateView):
    """Đăng ký chứng từ ghi sổ — register/book CTGS entries sequentially."""

    template_name = "modern/tools/ctgs_workflow.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, period = _parse_period_kwargs(self.request)
        company = require_current_company(self.request)

        vouchers = AccountingVoucher.objects.filter(
            company=company,
            fiscal_year=fy,
            period=period,
            status__gte=AccountingVoucher.Status.LEDGER,
        ).order_by("voucher_date", "voucher_no")

        rows = []
        for seq, v in enumerate(vouchers, 1):
            totals = v.lines.aggregate(d=Sum("debit_vnd"), c=Sum("credit_vnd"))
            rows.append(
                {
                    "seq": seq,
                    "voucher_no": v.voucher_no,
                    "voucher_date": v.voucher_date,
                    "description": v.description,
                    "amount": totals["d"] or Decimal("0"),
                    "book_code": v.book_code or f"CTGS-{fy}{period:02d}-{seq:03d}",
                }
            )

        ctx.update(
            {
                "page_title": "Đăng ký chứng từ ghi sổ",
                "fiscal_year": fy,
                "period": period,
                "rows": rows,
                "step": "register",
                **_common_period_choices(),
            }
        )
        return ctx

    def post(self, request, *args, **kwargs):
        fy, period = _parse_period_kwargs(request)
        company = require_current_company(request)

        vouchers = AccountingVoucher.objects.filter(
            company=company,
            fiscal_year=fy,
            period=period,
            status__gte=AccountingVoucher.Status.LEDGER,
        ).order_by("voucher_date", "voucher_no")

        updated = 0
        with transaction.atomic():
            for seq, v in enumerate(vouchers, 1):
                book_code = f"CTGS-{fy}{period:02d}-{seq:03d}"
                if v.book_code != book_code:
                    v.book_code = book_code
                    v.save(update_fields=["book_code"])
                    updated += 1

        messages.success(request, f"Đã đăng ký {updated} chứng từ ghi sổ.")
        return redirect("ui_modern:ctgs_register")


class CTGSCheckView(LoginRequiredMixin, TemplateView):
    """Kiểm tra chứng từ ghi sổ — validate book entries for balance and completeness."""

    template_name = "modern/tools/ctgs_workflow.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, period = _parse_period_kwargs(self.request)
        company = require_current_company(self.request)

        vouchers = AccountingVoucher.objects.filter(
            company=company,
            fiscal_year=fy,
            period=period,
            status__gte=AccountingVoucher.Status.LEDGER,
        ).order_by("voucher_date", "voucher_no")

        rows = []
        errors = []
        for v in vouchers:
            totals = v.lines.aggregate(d=Sum("debit_vnd"), c=Sum("credit_vnd"))
            d = totals["d"] or Decimal("0")
            c = totals["c"] or Decimal("0")
            balanced = d == c
            has_lines = v.lines.exists()
            row = {
                "voucher_no": v.voucher_no,
                "voucher_date": v.voucher_date,
                "debit_total": d,
                "credit_total": c,
                "difference": d - c,
                "balanced": balanced,
                "has_lines": has_lines,
                "book_code": v.book_code,
            }
            rows.append(row)
            if not balanced:
                errors.append(f"{v.voucher_no}: Nợ {d} ≠ Có {c} (chênh {d - c})")
            if not has_lines:
                errors.append(f"{v.voucher_no}: không có bút toán")

        ctx.update(
            {
                "page_title": "Kiểm tra chứng từ ghi sổ",
                "fiscal_year": fy,
                "period": period,
                "rows": rows,
                "step": "check",
                "errors": errors,
                "all_ok": len(errors) == 0,
                **_common_period_choices(),
            }
        )
        return ctx


class SourceDocScheduleView(LoginRequiredMixin, TemplateView):
    """Bảng kê chứng từ gốc cùng loại - theo cột (Mẫu S04-H).

    Lists source documents grouped by type in column format.
    """

    template_name = "modern/tools/ctgs_workflow.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, period = _parse_period_kwargs(self.request)
        company = require_current_company(self.request)

        vouchers = AccountingVoucher.objects.filter(
            company=company,
            fiscal_year=fy,
            period=period,
            status__gte=AccountingVoucher.Status.LEDGER,
        ).order_by("voucher_type", "voucher_date")

        from collections import OrderedDict

        groups = OrderedDict()
        for v in vouchers:
            vtype = v.get_voucher_type_display()
            if vtype not in groups:
                groups[vtype] = {"rows": [], "total": Decimal("0")}
            totals = v.lines.aggregate(d=Sum("debit_vnd"))
            amount = totals["d"] or Decimal("0")
            groups[vtype]["rows"].append(
                {
                    "voucher_no": v.voucher_no,
                    "voucher_date": v.voucher_date,
                    "description": v.description,
                    "amount": amount,
                }
            )
            groups[vtype]["total"] += amount

        ctx.update(
            {
                "page_title": "Bảng kê chứng từ gốc (S04-H)",
                "fiscal_year": fy,
                "period": period,
                "groups": groups,
                "step": "schedule",
                **_common_period_choices(),
            }
        )
        return ctx


class DepartmentMasterView(LoginRequiredMixin, TemplateView):
    """Bộ phận hạch toán — department/cost center master data.

    Lists departments from the ``hr.Department`` model and allows creating
    new ones via POST.  Also shows cost-center activity from voucher lines
    for the selected period.
    """

    template_name = "modern/tools/department_master.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, period = _parse_period_kwargs(self.request)
        company = require_current_company(self.request)

        # List actual departments from hr.Department model
        from apps.hr.models import Department

        departments = (
            Department.objects.filter(company=company, is_active=True)
            .order_by("code")
            .values("id", "code", "name", "manager_code", "is_active")
        )

        # Also aggregate VoucherLine by cost_center_code for activity view
        dept_activity = (
            VoucherLine.objects.filter(
                voucher__company=company,
                voucher__fiscal_year=fy,
                voucher__period=period,
            )
            .exclude(cost_center_code="")
            .values("cost_center_code")
            .annotate(
                total_debit=Sum("debit_vnd"),
                total_credit=Sum("credit_vnd"),
            )
            .order_by("cost_center_code")
        )

        activity_map = {
            d["cost_center_code"]: {
                "total_debit": d["total_debit"] or Decimal("0"),
                "total_credit": d["total_credit"] or Decimal("0"),
            }
            for d in dept_activity
        }

        rows = []
        for dept in departments:
            act = activity_map.get(dept["code"], {})
            rows.append(
                {
                    "id": dept["id"],
                    "code": dept["code"],
                    "name": dept["name"],
                    "manager_code": dept["manager_code"],
                    "total_debit": act.get("total_debit", Decimal("0")),
                    "total_credit": act.get("total_credit", Decimal("0")),
                }
            )

        ctx.update(
            {
                "page_title": "Bộ phận hạch toán",
                "fiscal_year": fy,
                "period": period,
                "rows": rows,
                **_common_period_choices(),
            }
        )
        return ctx

    def post(self, request, *args, **kwargs):
        """Create a new department."""
        from apps.hr.models import Department

        company = require_current_company(request)
        code = request.POST.get("code", "").strip()
        name = request.POST.get("name", "").strip()
        manager_code = request.POST.get("manager_code", "").strip()

        if not code or not name:
            messages.error(request, "Vui lòng nhập mã và tên phòng ban.")
            return redirect("ui_modern:department_master")

        if Department.objects.filter(company=company, code=code).exists():
            messages.error(request, f"Mã phòng ban '{code}' đã tồn tại.")
            return redirect("ui_modern:department_master")

        Department.objects.create(
            company=company,
            code=code,
            name=name,
            manager_code=manager_code,
        )
        messages.success(request, f"Đã tạo phòng ban {code} - {name}")
        return redirect("ui_modern:department_master")
