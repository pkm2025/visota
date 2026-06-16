# 02. Django Apps Structure

> Chi tiết cấu trúc Django apps, modules, services.

## 1. Bố cục thư mục dự án

```
pmketoan/                                  ← project root
├── manage.py
├── pyproject.toml                         ← PEP 621 metadata + uv config
├── uv.lock                                ← uv lock file
├── README.md
├── .env.example
│
├── config/                                ← Django project config
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py                        ← Settings chung
│   │   ├── dev.py                         ← Dev overrides
│   │   ├── prod.py                        ← Production overrides
│   │   └── test.py
│   ├── urls.py                            ← Root URL routing
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/                                  ← Django apps
│   ├── __init__.py
│   │
│   │   ─── Shared backend (models + services + API) ───
│   ├── core/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py                      ← Company (có branding fields)
│   │   ├── middleware/                    ← TenantMiddleware, BrandingMiddleware
│   │   ├── managers.py                    ← CompanyManager
│   │   ├── permissions.py                 ← Base permission classes
│   │   ├── context_processors.py          ← brand, current_layout, ux context
│   │   ├── exceptions.py
│   │   ├── utils.py
│   │   ├── ux/                            ← UX framework (plugin registry)
│   │   │   ├── registry.py                ← InteractionStyleRegistry
│   │   │   ├── workflows.py               ← WorkflowRegistry
│   │   │   ├── context.py                 ← UXContext (layout + style + workflow)
│   │   │   ├── defaults.py                ← Smart UX defaults theo role
│   │   │   └── middleware.py              ← UX detection middleware
│   │   └── migrations/
│   │
│   ├── identity/                          ← User, Role, Permission, UserLayoutPreference
│   │   ├── ...
│   │
│   ├── master_data/                       ← ChartOfAccounts, Currency, ...
│   │   ├── ...
│   │
│   ├── ledger/                            ← Voucher, posting, closing
│   │   ├── models/
│   │   ├── services/                      ← Shared business logic
│   │   ├── api/                           ← Shared API endpoints
│   │   └── migrations/
│   │   # NOTE: KHÔNG có views/ trong module nghiệp vụ
│   │   # Views nằm trong apps/ui_<layout>/
│   │
│   ├── treasury/
│   ├── sales/
│   ├── purchasing/
│   ├── inventory/
│   ├── assets/
│   ├── costing/
│   ├── hr/
│   ├── payroll/
│   ├── reporting/
│   ├── tax/
│   ├── system/
│   │
│   │   ─── Layout packs (View + Template layer, multi-UI) ───
│   ├── ui_modern/                         # /modern/* — Modern UI (default)
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── urls.py                        # URL routing cho Modern
│   │   ├── views/                         # View layer (HTML rendering cho HTMX)
│   │   │   ├── __init__.py
│   │   │   ├── dashboard_views.py
│   │   │   ├── ledger_views.py
│   │   │   ├── sales_views.py
│   │   │   └── ...
│   │   └── forms/
│   │
│   ├── ui_classic/                        # /classic/* — Classic UI
│   │   └── (tương tự ui_modern)
│   │
│   ├── ui_mobile/                         # /mobile/* — Mobile UI (PWA)
│   │   └── (tương tự)
│   │
│   └── ui_portal/                         # /portal/* — Customer/vendor portal
│       └── (tương tự)
│
├── shared/                                ← Cross-cutting concerns
│   ├── __init__.py
│   ├── value_objects.py                   ← Money, DateRange, VoucherNo
│   ├── events.py                          ← Domain events
│   ├── decimal_utils.py                   ← Decimal helpers
│   ├── exchange.py                        ← Exchange rate service
│   └── pdf.py                             ← PDF generation helpers
│
├── templates/                             ← Django templates (theo layout pack)
│   ├── shared/                            ← Components dùng chung mọi layout
│   │   ├── components/
│   │   │   ├── grid.html
│   │   │   ├── form_field.html
│   │   │   ├── modal.html
│   │   │   ├── tabs.html
│   │   │   └── ...
│   │   ├── _layout_switcher.html
│   │   ├── _company_switcher.html
│   │   └── _user_menu.html
│   │
│   ├── modern/                            ← Modern UI templates
│   │   ├── base/
│   │   │   ├── layout.html
│   │   │   ├── topbar.html
│   │   │   └── sidebar.html
│   │   ├── dashboard/
│   │   ├── ledger/
│   │   └── ...
│   │
│   ├── classic/                           ← Classic UI templates
│   │   ├── base/
│   │   ├── dashboard/
│   │   └── ...
│   │
│   ├── mobile/                            ← Mobile UI templates
│   │   └── ...
│   │
│   └── portal/                            ← Portal UI templates
│       └── ...
│   │   ├── voucher_list.html
│   │   ├── voucher_form.html
│   │   ├── voucher_detail.html
│   │   └── ...
│   ├── sales/
│   ├── ...
│   └── reporting/
│       ├── trial_balance.html
│       ├── balance_sheet.html
│       └── ...
│
├── static/
│   ├── css/
│   │   ├── main.css
│   │   ├── vendor/
│   │   │   ├── bootstrap.min.css
│   │   │   └── tabulator.min.css
│   │   └── components/
│   ├── js/
│   │   ├── main.js
│   │   ├── htmx.config.js
│   │   ├── alpine.components.js
│   │   └── vendor/
│   │       ├── htmx.min.js
│   │       ├── alpine.min.js
│   │       ├── bootstrap.bundle.min.js
│   │       └── tabulator.min.js
│   └── images/
│       ├── logo.svg
│       └── ...
│
├── locale/
│   ├── vi/LC_MESSAGES/
│   │   └── django.po                      ← Tiếng Việt
│   └── en/LC_MESSAGES/
│       └── django.po                      ← Tiếng Anh
│
├── tests/
│   ├── conftest.py
│   ├── factories/                         ← Factory Boy
│   ├── unit/
│   ├── integration/
│   └── e2e/                               ← Playwright
│
└── docs/                                  ← Tài liệu (cái này)
```

## 2. Một Django app tiêu chuẩn (ví dụ: `ledger`)

```
apps/ledger/
├── __init__.py
├── apps.py                                ← AppConfig
├── models/
│   ├── __init__.py                        ← Re-export
│   ├── voucher.py
│   ├── balance.py
│   └── closing.py
├── managers.py                            ← Custom QuerySets
├── services/
│   ├── __init__.py
│   ├── voucher_service.py                 ← CRUD + business logic
│   ├── posting_service.py                 ← Post voucher → update balances
│   ├── closing_service.py                 ← Period closing
│   ├── year_end_service.py                ← Carry-forward
│   └── rebuild_service.py                 ← Rebuild projections
├── api/
│   ├── __init__.py
│   ├── schemas.py                         ← Pydantic schemas
│   ├── vouchers.py                        ← Voucher endpoints
│   ├── balances.py
│   ├── closing.py
│   └── reports.py
├── views/
│   ├── __init__.py
│   ├── voucher_views.py                   ← HTML views for HTMX
│   ├── balance_views.py
│   └── ...
├── forms/
│   ├── __init__.py
│   ├── voucher_form.py
│   └── voucher_line_formset.py
├── admin/
│   ├── __init__.py
│   └── voucher_admin.py
├── tasks.py                               ← django-q2 tasks
├── signals.py                             ← Django signals
├── utils.py
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py
└── tests/
    ├── __init__.py
    ├── test_voucher_service.py
    ├── test_posting_service.py
    └── test_closing_service.py
```

## 3. Quy ước code

### 3.1. Naming convention

- **Models**: PascalCase singular (`AccountingVoucher`, `VoucherLine`)
- **Tables**: snake_case plural (`accounting_voucher`, `voucher_line`)
- **Fields**: snake_case (`voucher_no`, `fiscal_year`)
- **Foreign keys**: `<entity>_id` (`company_id`, `customer_id`)
- **Boolean**: `is_` hoặc `has_` prefix (`is_active`, `has_dependents`)
- **Date/time**: `_date` cho DATE, `_at` cho DATETIME (`voucher_date`, `created_at`)
- **Services**: `<Entity>Service` (`VoucherService`, `PostingService`)
- **API endpoints**: RESTful (`/api/v1/vouchers/`, `/api/v1/vouchers/{id}/`)

### 3.2. Model pattern

```python
# apps/ledger/models/voucher.py
from django.db import models
from apps.core.models import TimestampedModel, CompanyOwnedModel
from apps.core.managers import CompanyQuerySet


class AccountingVoucherQuerySet(CompanyQuerySet):
    def posted(self):
        return self.filter(status__gte=2)
    
    def in_period(self, fiscal_year, period=None):
        q = self.filter(fiscal_year=fiscal_year)
        if period:
            q = q.filter(period=period)
        return q
    
    def locked(self):
        return self.filter(status=3)


class AccountingVoucher(CompanyOwnedModel, TimestampedModel):
    class VoucherType(models.TextChoices):
        JOURNAL = 'journal', 'Phiếu kế toán'
        CASH_RECEIPT = 'cash_receipt', 'Phiếu thu'
        CASH_PAYMENT = 'cash_payment', 'Phiếu chi'
        SALES_INVOICE = 'sales_invoice', 'Hóa đơn bán'
        PURCHASE_INVOICE = 'purchase_invoice', 'Phiếu nhập mua'
        STOCK_VOUCHER = 'stock_voucher', 'Phiếu nhập xuất'
        DEPRECIATION = 'depreciation', 'Khấu hao'
        ALLOCATION = 'allocation', 'Phân bổ'
        CLOSING = 'closing', 'Kết chuyển'
        # ...
    
    class Status(models.IntegerChoices):
        DRAFT = 0, 'Lưu tạm'
        SUBSIDIARY = 1, 'Ghi sổ phụ'
        LEDGER = 2, 'Ghi sổ cái'
        LOCKED = 3, 'Đã khóa'
    
    fiscal_year = models.SmallIntegerField()
    period = models.PositiveSmallIntegerField()
    voucher_no = models.CharField(max_length=50)
    voucher_type = models.CharField(max_length=30, choices=VoucherType.choices)
    voucher_date = models.DateField()
    posting_date = models.DateField(null=True)
    book_code = models.CharField(max_length=20, blank=True)
    status = models.PositiveSmallIntegerField(
        choices=Status.choices, default=Status.LEDGER
    )
    currency_code = models.CharField(max_length=3, default='VND')
    exchange_rate = models.DecimalField(
        max_digits=18, decimal_places=6, default=1
    )
    total_fc = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_vnd = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    description = models.TextField(blank=True)
    source = models.CharField(max_length=20, default='manual')
    source_reference_id = models.BigIntegerField(null=True, blank=True)
    is_reversed = models.BooleanField(default=False)
    reversal_voucher = models.ForeignKey('self', on_delete=models.SET_NULL, null=True)
    
    objects = AccountingVoucherQuerySet.as_manager()
    
    class Meta:
        db_table = 'accounting_voucher'
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'fiscal_year', 'voucher_type', 'voucher_no'],
                name='uk_voucher_no'
            )
        ]
        indexes = [
            models.Index(fields=['company', 'voucher_date']),
            models.Index(fields=['company', 'fiscal_year', 'period', 'status']),
        ]
    
    def __str__(self):
        return f"{self.voucher_no} ({self.voucher_date})"
    
    @property
    def is_posted(self):
        return self.status >= self.Status.LEDGER
    
    @property
    def is_locked(self):
        return self.status == self.Status.LOCKED
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.posting_date and self.posting_date < self.voucher_date:
            raise ValidationError("Posting date cannot be before voucher date")
```

### 3.3. Service pattern

```python
# apps/ledger/services/posting_service.py
from decimal import Decimal
from django.db import transaction
from apps.ledger.models import AccountingVoucher, AccountPeriodBalance


class VoucherPostingService:
    """
    Service để post voucher: cập nhật sổ cái, sổ chi tiết, số dư
    """
    
    @transaction.atomic
    def post(self, voucher: AccountingVoucher) -> None:
        self._validate(voucher)
        self._update_balances(voucher)
        voucher.status = AccountingVoucher.Status.LEDGER
        voucher.save(update_fields=['status', 'updated_at', 'updated_by'])
    
    def _validate(self, voucher: AccountingVoucher) -> None:
        # N = C
        total_debit = sum(line.debit_vnd for line in voucher.lines.all())
        total_credit = sum(line.credit_vnd for line in voucher.lines.all())
        if abs(total_debit - total_credit) > Decimal('0.01'):
            raise VoucherNotBalancedError(
                f"Debit {total_debit} != Credit {total_credit}"
            )
        
        # Voucher date trong fiscal year
        # Period khớp voucher_date
        # ...
    
    def _update_balances(self, voucher: AccountingVoucher) -> None:
        for line in voucher.lines.all():
            self._update_account_balance(line)
    
    def _update_account_balance(self, line) -> None:
        balance, _ = AccountPeriodBalance.objects.get_or_create(
            company=line.voucher.company,
            fiscal_year=line.voucher.fiscal_year,
            period=line.voucher.period,
            account_code=line.account_code,
            object_type=line.object_type,
            object_code=line.object_code,
        )
        balance.period_debit += line.debit_vnd
        balance.period_credit += line.credit_vnd
        balance.closing_debit = (
            balance.opening_debit 
            + balance.period_debit 
            - balance.period_credit
        ) if (balance.opening_debit + balance.period_debit) > balance.period_credit else 0
        # ... compute closing balances
        balance.save()
```

### 3.4. API pattern (django-ninja)

```python
# apps/ledger/api/vouchers.py
from ninja import Router, Schema, Field
from ninja.pagination import paginate
from apps.ledger.models import AccountingVoucher
from apps.ledger.services import VoucherService
from apps.identity.permissions import require_permission

router = Router(tags=['ledger'])


class VoucherSchema(Schema):
    id: int
    voucher_no: str
    voucher_date: str
    description: str
    total_vnd: Decimal
    status: int
    
    @staticmethod
    def resolve_voucher_date(obj):
        return obj.voucher_date.isoformat()


class VoucherCreateSchema(Schema):
    voucher_no: str | None = None
    voucher_date: str
    description: str
    currency_code: str = 'VND'
    exchange_rate: Decimal = Decimal('1')
    lines: list['VoucherLineSchema']


class VoucherLineSchema(Schema):
    account_code: str
    object_type: str | None = None
    object_code: str | None = None
    debit_vnd: Decimal = Decimal('0')
    credit_vnd: Decimal = Decimal('0')
    description: str | None = None


@router.get('/vouchers/', response=list[VoucherSchema])
@paginate
@require_permission('ledger.voucher.view')
def list_vouchers(request, fiscal_year: int, period: int | None = None):
    qs = AccountingVoucher.objects.for_company(request.company_id)
    qs = qs.filter(fiscal_year=fiscal_year)
    if period:
        qs = qs.filter(period=period)
    return qs.order_by('-voucher_date', '-id')


@router.post('/vouchers/', response={201: VoucherSchema})
@require_permission('ledger.voucher.create')
def create_voucher(request, payload: VoucherCreateSchema):
    service = VoucherService(company_id=request.company_id, user=request.user)
    voucher = service.create(payload.dict())
    return 201, voucher
```

### 3.5. View pattern (cho HTMX)

```python
# apps/ledger/views/voucher_views.py
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from apps.ledger.models import AccountingVoucher


@require_http_methods(['GET'])
def voucher_list_partial(request):
    """Return HTML fragment for HTMX"""
    vouchers = (
        AccountingVoucher.objects
        .for_company(request.company_id)
        .filter(fiscal_year=request.current_fiscal_year)
        .order_by('-voucher_date')
    )
    return render(request, 'ledger/voucher/_list_rows.html', {
        'vouchers': vouchers,
    })


@require_http_methods(['GET'])
def voucher_detail(request, pk):
    voucher = get_object_or_404(AccountingVoucher, pk=pk, company_id=request.company_id)
    return render(request, 'ledger/voucher/detail.html', {'voucher': voucher})
```

### 3.6. Template pattern (HTMX)

```html
<!-- templates/ledger/voucher/_list_rows.html -->
<tbody>
{% for v in vouchers %}
  <tr class="hover:bg-gray-50 cursor-pointer"
      hx-get="/ledger/vouchers/{{ v.id }}/"
      hx-target="#voucher-detail"
      hx-swap="innerHTML">
    <td>{{ v.voucher_date|date:"d-m-Y" }}</td>
    <td>{{ v.voucher_no }}</td>
    <td>{{ v.description|truncatechars:60 }}</td>
    <td class="text-right">{{ v.total_vnd|floatformat:0 }}</td>
    <td>
      <span class="badge badge-{{ v.status_class }}">{{ v.get_status_display }}</span>
    </td>
  </tr>
{% empty %}
  <tr><td colspan="5" class="text-center py-8 text-gray-400">Không có dữ liệu</td></tr>
{% endfor %}
</tbody>
```

## 4. URL routing

```python
# config/urls.py
from django.contrib import admin
from django.urls import path, include
from ninja import NinjaAPI

api = NinjaAPI(title='PMKetoan API', version='1.0.0')

# Mount API routers
api.add_router('/identity/', 'apps.identity.api.router')
api.add_router('/master-data/', 'apps.master_data.api.router')
api.add_router('/ledger/', 'apps.ledger.api.router')
api.add_router('/sales/', 'apps.sales.api.router')
# ...

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', api.urls),
    
    # HTMX routes (HTML views)
    path('', include('apps.core.urls')),
    path('ledger/', include('apps.ledger.urls')),
    path('sales/', include('apps.sales.urls')),
    # ...
]
```

---

**Tiếp theo**: [03. django-ninja API](./03-django-ninja-api.md)
