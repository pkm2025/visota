# 05. Multi-UI Architecture (Đa giao diện song song)

> Thiết kế để **nhiều layout packs chạy song song** qua URL riêng + **multi-tenant branding** cho mỗi company.

## 1. Mục tiêu

- Mỗi **layout pack** có URL riêng (`/modern/`, `/classic/`, `/mobile/`...) — cùng chạy song song, user tự chọn
- Mỗi **company (tenant)** có brand riêng: logo, màu, favicon, custom CSS
- **Backend dùng chung** — chỉ View + Template khác
- Bắt đầu với **2-3 layout packs** trong Phase 1

## 2. Sơ đồ kiến trúc

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│              SHARED BACKEND (một bộ code nghiệp vụ)                  │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │  Models      │  │  Services    │  │  API (django-ninja)       │  │
│  │  (Django ORM)│  │  (Business   │  │  /api/v1/*                │  │
│  │              │  │   Logic)     │  │                           │  │
│  └──────────────┘  └──────────────┘  └───────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
         ↑                   ↑                   ↑                   ↑
         │                   │                   │                   │
┌────────┴────────┐ ┌────────┴────────┐ ┌────────┴────────┐ ┌────────┴────────┐
│                  │ │                 │ │                 │ │                 │
│  Modern UI       │ │  Classic UI    │ │  Mobile UI      │ │  Portal UI      │
│  (sidebar trái, │ │  (top nav,    │ │  (bottom tab,  │ │  (KH xem công  │
│   Bootstrap 5,   │ │   giống MISA/ │ │   responsive)  │ │   nợ, login     │
│   HTMX)          │ │   Bravo cũ)   │ │                 │ │   bằng OTP)    │
│                  │ │                │ │                 │ │                 │
│  /modern/*       │ │  /classic/*   │ │  /mobile/*     │ │  /portal/*     │
│                  │ │                │ │                 │ │                 │
│  apps/ui_modern  │ │ apps/ui_classic│ │ apps/ui_mobile │ │ apps/ui_portal │
│                  │ │                │ │                 │ │                 │
└──────────────────┘ └────────────────┘ └─────────────────┘ └─────────────────┘
         │                   │                   │                   │
         └───────────────────┴───────────────────┴───────────────────┘
                                     │
                                     ↓
                  ┌─────────────────────────────────────┐
                  │  Branding Layer (per-tenant)        │
                  │  - Logo, màu, favicon               │
                  │  - Custom CSS                       │
                  │  - Default layout                   │
                  └─────────────────────────────────────┘
```

## 3. Layout Packs chi tiết

### 3.1. Modern UI (mặc định)

- **URL prefix**: `/modern/*` (cũng là `/` mặc định)
- **App**: `apps/ui_modern`
- **Template dir**: `templates/modern/`
- **Đặc điểm**:
  - Sidebar trái 256px, có thể collapse
  - Top bar mỏng với breadcrumb + search + notifications
  - Bootstrap 5.3, màu sắc hiện đại (blue/gray)
  - Card-based layout, nhiều khoảng trắng
  - HTMX cho tương tác
- **Đối tượng**: user trẻ, quen web hiện đại (Gmail, Notion)

```
┌──────────────────────────────────────────────────────────┐
│ [≡] PMKetoan  [🔍 Search...]   [🔔3] [📅] [▼ SIS]      │
├────────┬─────────────────────────────────────────────────┤
│ [▼ Tổng│  Trang chủ > Phiếu kế toán                      │
│   • PKT│  ┌──────────────────────────────────────────┐  │
│   • K/C│  │  Phiếu kế toán         [+ Thêm] [Export] │  │
│ [▼ Sổ ]│  │  [Filter: status, date, search...]       │  │
│   • NKC│  │  ┌────────────────────────────────────┐  │  │
│   • Sổ │  │  │ Grid (master-detail)               │  │  │
│ [▼ BC ]│  │  │                                    │  │  │
│        │  │  └────────────────────────────────────┘  │  │
│        │  └──────────────────────────────────────────┘  │
└────────┴─────────────────────────────────────────────────┘
```

### 3.2. Classic UI

- **URL prefix**: `/classic/*`
- **App**: `apps/ui_classic`
- **Template dir**: `templates/classic/`
- **Đặc điểm**:
  - Top navigation đầy đủ (giống MISA/Bravo/SIS cũ)
  - Menu ngang với dropdown
  - Density cao, font nhỏ, ít khoảng trắng
  - Grid dày, nhiều cột hiển thị cùng lúc
  - Phím tắt nhiều
- **Đối tượng**: kế toán viên lâu năm, quen phần mềm truyền thống

```
┌──────────────────────────────────────────────────────────┐
│ [Logo]  Cập nhật | Sổ sách | Báo cáo | Danh mục | Hệ thống│
├──────────────────────────────────────────────────────────┤
│ Sub-menu: Phiếu KT | Kết chuyển | Phân bổ | Khóa số liệu │
├──────────────────────────────────────────────────────────┤
│ [🔍] [Từ ngày ▼] [Đến ngày ▼] [Status ▼] [+ Thêm] [📤]   │
├──────────────────────────────────────────────────────────┤
│ Ngày       │ Số CT  │ Diễn giải   │ Nợ         │ Có      │
│ 15/06/2026 │ BC0001 │ Bán hàng    │ 110.000.000│         │
│ 14/06/2026 │ BC0002 │ Mua hàng    │            │ 55tr    │
│ ...                                                      │
└──────────────────────────────────────────────────────────┘
```

### 3.3. Mobile UI

- **URL prefix**: `/mobile/*`
- **App**: `apps/ui_mobile`
- **Template dir**: `templates/mobile/`
- **Đặc điểm**:
  - Bottom tab bar (Home, Tìm, Tạo, TB, Profile)
  - Card-based, swipe gestures
  - Touch-first, button lớn
  - offline-first (PWA)
- **Đối tượng**: truy cập nhanh trên điện thoại (xem số dư, duyệt chứng từ)

```
┌──────────────────────┐
│ ☰  Phiếu kế toán  ⚙ │
├──────────────────────┤
│                      │
│ ┌────────────────┐   │
│ │ 📄 BC0001      │   │
│ │ 15/06 · 110tr  │   │
│ │ ✓ Đã ghi sổ   │   │
│ └────────────────┘   │
│ ┌────────────────┐   │
│ │ 📄 BC0002      │   │
│ │ 14/06 · 55tr   │   │
│ │ ⚠ Lưu tạm     │   │
│ └────────────────┘   │
│                      │
├──────────────────────┤
│ 🏠  🔍  ＋  🔔  👤  │
└──────────────────────┘
```

### 3.4. Portal UI (Customer/Partner Portal) — Phase sau

- **URL prefix**: `/portal/*`
- **App**: `apps/ui_portal`
- **Template dir**: `templates/portal/`
- **Đặc điểm**:
  - Login bằng email + OTP (không cần account nội bộ)
  - Chỉ xem: công nợ, hóa đơn, lịch sử thanh toán
  - Có nút "Tải hóa đơn PDF", "Thanh toán online"
  - Branding của company (không hiện PMKetoan logo)
- **Đối tượng**: khách hàng, nhà cung cấp của tenant

## 4. URL routing

```python
# config/urls.py
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', api.urls),
    
    # Default: detect layout
    path('', RedirectView.as_view(url='/modern/', permanent=False)),
    
    # Layout packs (multi-UI running concurrently)
    path('modern/', include('apps.ui_modern.urls')),
    path('classic/', include('apps.ui_classic.urls')),
    path('mobile/', include('apps.ui_mobile.urls')),
    path('portal/', include('apps.ui_portal.urls')),
    
    # Layout switcher endpoint (HTMX)
    path('switch-layout/<str:layout>/', SwitchLayoutView.as_view(), name='switch_layout'),
]
```

```python
# apps/ui_modern/urls.py
from django.urls import path
from .views import (
    DashboardView, VoucherListView, VoucherDetailView, VoucherCreateView,
    CustomerListView, SalesInvoiceListView,
)

app_name = 'ui_modern'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    
    # Ledger
    path('vouchers/', VoucherListView.as_view(), name='voucher_list'),
    path('vouchers/<int:pk>/', VoucherDetailView.as_view(), name='voucher_detail'),
    path('vouchers/new/', VoucherCreateView.as_view(), name='voucher_create'),
    
    # Sales
    path('customers/', CustomerListView.as_view(), name='customer_list'),
    path('invoices/', SalesInvoiceListView.as_view(), name='sales_invoice_list'),
    
    # ... all other modules
]
```

```python
# apps/ui_classic/urls.py — cấu trúc tương tự
app_name = 'ui_classic'
urlpatterns = [
    path('vouchers/', ClassicVoucherListView.as_view(), name='voucher_list'),
    ...
]
```

**Reverse URL theo layout**:

```python
# Template
<a href="{% url 'ui_modern:voucher_list' %}">Modern</a>
<a href="{% url 'ui_classic:voucher_list' %}">Classic</a>
<a href="{% url 'ui_mobile:voucher_list' %}">Mobile</a>

# Python
from django.urls import reverse
url = reverse(f'ui_{layout}:voucher_list')
```

## 5. Multi-tenant branding

### 5.1. Mở rộng Company model

```python
# apps/core/models.py
class Company(models.Model):
    # ... existing fields ...
    
    # Branding
    brand_name = models.CharField(max_length=255, blank=True,
                                   help_text='Tên hiển thị (nếu khác tên pháp lý)')
    brand_short_name = models.CharField(max_length=50, blank=True)
    brand_logo = models.ImageField(upload_to='brands/logos/', null=True, blank=True)
    brand_logo_dark = models.ImageField(upload_to='brands/logos/', null=True, blank=True)
    brand_favicon = models.ImageField(upload_to='brands/favicons/', null=True, blank=True)
    
    # Brand colors (CSS hex)
    brand_primary_color = models.CharField(max_length=7, default='#2563eb',
                                            validators=[validate_hex_color])
    brand_accent_color = models.CharField(max_length=7, default='#16a34a')
    brand_sidebar_color = models.CharField(max_length=20, default='light',
        help_text='light/dark/brand-<color>')
    
    # Default layout cho user mới của company này
    default_layout = models.CharField(max_length=20, default='modern',
        choices=[('modern','Modern'), ('classic','Classic'), ('mobile','Mobile')])
    
    # Custom CSS (advanced)
    custom_css = models.TextField(blank=True, validators=[validate_css])
    
    # White-label options
    hide_pmketoan_branding = models.BooleanField(default=False,
        help_text='Ẩn nhãn "Powered by PMKetoan"')
    custom_domain = models.CharField(max_length=255, blank=True,
        help_text='VD: accounting.yourcompany.com')
```

### 5.2. UserPreference model

```python
class UserLayoutPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    preferred_layout = models.CharField(max_length=20, default='modern')
    preferred_theme = models.CharField(max_length=20, default='light',
        choices=[('light','Sáng'), ('dark','Tối'), ('auto','Theo hệ thống')])
    preferred_density = models.CharField(max_length=20, default='comfortable',
        choices=[('compact','Chặt'), ('comfortable','Thoáng')])
    sidebar_collapsed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = [('user', 'company')]
```

### 5.3. Middleware: set branding context

```python
# apps/core/middleware/branding.py
class BrandingMiddleware:
    DEFAULT_BRAND = {
        'name': 'PMKetoan',
        'logo': '/static/images/logo.svg',
        'primary_color': '#2563eb',
        'accent_color': '#16a34a',
        'favicon': '/static/favicon.ico',
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Detect layout from URL
        request.current_layout = self._detect_layout(request.path)
        
        # Set brand from current company
        if hasattr(request, 'current_company') and request.current_company:
            c = request.current_company
            request.brand = {
                'name': c.brand_name or c.name,
                'logo': c.brand_logo.url if c.brand_logo else self.DEFAULT_BRAND['logo'],
                'primary_color': c.brand_primary_color,
                'accent_color': c.brand_accent_color,
                'favicon': c.brand_favicon.url if c.brand_favicon else self.DEFAULT_BRAND['favicon'],
                'hide_pmketoan_branding': c.hide_pmketoan_branding,
                'custom_css': c.custom_css,
            }
        else:
            request.brand = self.DEFAULT_BRAND.copy()
        
        return self.get_response(request)
    
    def _detect_layout(self, path):
        if path.startswith('/modern/'): return 'modern'
        if path.startswith('/classic/'): return 'classic'
        if path.startswith('/mobile/'): return 'mobile'
        if path.startswith('/portal/'): return 'portal'
        return 'modern'
```

### 5.4. Context processor

```python
# apps/core/context_processors.py
def branding(request):
    return {
        'brand': getattr(request, 'brand', {}),
        'current_layout': getattr(request, 'current_layout', 'modern'),
        'available_layouts': [
            {'code': 'modern', 'name': 'Modern', 'icon': 'bi-window-stack'},
            {'code': 'classic', 'name': 'Classic', 'icon': 'bi-table'},
            {'code': 'mobile', 'name': 'Mobile', 'icon': 'bi-phone'},
        ],
    }
```

### 5.5. Base template với brand vars

```html
<!-- templates/modern/base/layout.html -->
<!DOCTYPE html>
<html lang="vi" data-layout="modern">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}{{ brand.name }}{% endblock %}</title>
    
    <link rel="icon" href="{{ brand.favicon }}">
    
    <!-- CSS variables from brand -->
    <style>
    :root {
        --brand-primary: {{ brand.primary_color }};
        --brand-accent: {{ brand.accent_color }};
        --brand-name: "{{ brand.name }}";
    }
    </style>
    
    <!-- Vendor CSS -->
    <link rel="stylesheet" href="{% static 'vendor/css/bootstrap.min.css' %}">
    <link rel="stylesheet" href="{% static 'modern/css/main.css' %}">
    
    {% if brand.custom_css %}
    <style>{{ brand.custom_css|safe }}</style>
    {% endif %}
</head>
<body class="layout-modern">
    {% include 'modern/base/topbar.html' %}
    {% include 'modern/base/sidebar.html' %}
    
    <main class="main-content">
        {% block content %}{% endblock %}
    </main>
    
    <!-- Layout switcher -->
    {% include 'shared/_layout_switcher.html' %}
</body>
</html>
```

### 5.6. Layout switcher component

```html
<!-- templates/shared/_layout_switcher.html -->
<div class="layout-switcher fixed bottom-4 right-4 z-50">
    <div class="bg-white rounded-full shadow-lg border p-1 flex gap-1">
        {% for layout in available_layouts %}
        <a href="{% url 'ui_'|add:layout.code|add:':dashboard' %}"
           class="px-3 py-2 rounded-full text-sm hover:bg-gray-100 {% if current_layout == layout.code %}bg-blue-100 text-blue-700{% endif %}"
           title="{{ layout.name }}">
            <i class="bi {{ layout.icon }}"></i>
            <span class="hidden sm:inline">{{ layout.name }}</span>
        </a>
        {% endfor %}
    </div>
</div>
```

## 6. Code organization

### 6.1. Django apps

```
apps/
├── core/                       # Shared (models, services)
├── identity/                   # Shared (user, auth)
├── master_data/                # Shared
├── ledger/                     # Shared (models + services + api)
├── treasury/                   # Shared
├── sales/
├── purchasing/
├── inventory/
├── assets/
├── costing/
├── hr/
├── payroll/
├── reporting/
├── tax/
├── system/
│
├── ui_modern/                  # ← Layout pack: Modern
│   ├── __init__.py
│   ├── apps.py
│   ├── urls.py                 # URL routing cho Modern
│   ├── views/                  # View layer
│   │   ├── __init__.py
│   │   ├── dashboard.py
│   │   ├── ledger_views.py
│   │   ├── sales_views.py
│   │   └── ...
│   ├── forms/
│   └── README.md
│
├── ui_classic/                 # ← Layout pack: Classic
│   ├── (tương tự ui_modern)
│   └── ...
│
├── ui_mobile/                  # ← Layout pack: Mobile
│   ├── (tương tự)
│   └── ...
│
└── ui_portal/                  # ← Layout pack: Portal (KH/NCC)
    ├── (tương tự)
    └── ...
```

### 6.2. Templates

```
templates/
├── shared/                     # Components dùng chung
│   ├── components/
│   │   ├── _grid.html
│   │   ├── _form_field.html
│   │   ├── _pagination.html
│   │   └── ...
│   ├── _layout_switcher.html
│   ├── _company_switcher.html
│   └── _user_menu.html
│
├── modern/                     # Modern UI templates
│   ├── base/
│   │   ├── layout.html
│   │   ├── topbar.html
│   │   └── sidebar.html
│   ├── dashboard/
│   │   └── index.html
│   ├── ledger/
│   │   ├── voucher_list.html
│   │   ├── voucher_detail.html
│   │   └── voucher_form.html
│   └── ...
│
├── classic/                    # Classic UI templates
│   ├── base/
│   │   ├── layout.html
│   │   ├── topnav.html
│   │   └── submenu.html
│   ├── dashboard/
│   └── ledger/
│       └── ...
│
├── mobile/
│   ├── base/
│   │   ├── layout.html
│   │   └── tabbar.html
│   ├── ledger/
│   └── ...
│
└── portal/
    ├── base/
    │   └── layout.html
    ├── login.html
    ├── invoices.html
    └── payments.html
```

### 6.3. Static files

```
static/
├── shared/                     # CSS/JS dùng chung
│   ├── css/
│   │   ├── variables.css
│   │   └── components.css
│   └── js/
│       ├── htmx.config.js
│       └── utils.js
├── modern/
│   ├── css/
│   │   └── main.css
│   ├── js/
│   │   └── main.js
│   └── images/
├── classic/
│   ├── css/
│   └── js/
├── mobile/
│   └── ...
└── vendor/                     # Vendor libs (Bootstrap, HTMX, etc.)
```

## 7. View pattern (ví dụ)

### 7.1. Modern view (HTMX-friendly)

```python
# apps/ui_modern/views/ledger_views.py
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from apps.ledger.services import VoucherService
from apps.ledger.models import AccountingVoucher


@require_http_methods(['GET'])
def voucher_list(request):
    """Modern UI: master-detail với HTMX"""
    service = VoucherService(request)
    vouchers = service.list(filters=request.GET)
    
    return render(request, 'modern/ledger/voucher_list.html', {
        'vouchers': vouchers,
        'filter_form': VoucherFilterForm(request.GET),
    })


@require_http_methods(['GET'])
def voucher_list_partial(request):
    """HTMX partial: chỉ trả về <tbody>"""
    service = VoucherService(request)
    vouchers = service.list(filters=request.GET, paginate=True)
    
    return render(request, 'modern/ledger/voucher/_list_rows.html', {
        'vouchers': vouchers,
        'page_obj': vouchers,
    })


@require_http_methods(['GET'])
def voucher_detail_partial(request, pk):
    """HTMX partial: chỉ trả về detail panel"""
    service = VoucherService(request)
    voucher = service.get(pk)
    return render(request, 'modern/ledger/voucher/_detail.html', {
        'voucher': voucher,
    })
```

### 7.2. Classic view (full-page reload)

```python
# apps/ui_classic/views/ledger_views.py
def voucher_list(request):
    """Classic UI: full page, dense grid"""
    service = VoucherService(request)
    vouchers = service.list(filters=request.GET, paginate=True, page_size=100)
    
    return render(request, 'classic/ledger/voucher_list.html', {
        'vouchers': vouchers,
        'page_obj': vouchers,
        'filters': request.GET,
    })
```

### 7.3. Mobile view (simplified)

```python
# apps/ui_mobile/views/ledger_views.py
def voucher_list(request):
    """Mobile UI: card list, paginated 10/page"""
    service = VoucherService(request)
    vouchers = service.list(filters=request.GET, paginate=True, page_size=10)
    
    return render(request, 'mobile/ledger/voucher_list.html', {
        'vouchers': vouchers,
        'page_obj': vouchers,
    })
```

### 7.4. Shared service

```python
# apps/ledger/services/voucher_service.py
class VoucherService:
    """Service dùng chung cho mọi layout pack"""
    
    def __init__(self, request):
        self.request = request
        self.company_id = request.current_company.id
        self.user = request.user
    
    def list(self, filters=None, paginate=False, page_size=25):
        qs = (
            AccountingVoucher.objects
            .for_company(self.company_id)
            .select_related('created_by')
            .order_by('-voucher_date', '-id')
        )
        if filters:
            qs = apply_filters(qs, filters)
        
        if paginate:
            from django.core.paginator import Paginator
            size = int(filters.get('page_size', page_size)) if filters else page_size
            return Paginator(qs, size).get_page(int(filters.get('page', 1)) if filters else 1)
        return qs
    
    def get(self, pk):
        return get_object_or_404(
            AccountingVoucher.objects.for_company(self.company_id).prefetch_related('lines'),
            pk=pk
        )
    
    def create(self, data):
        # ... business logic ...
        pass
```

## 8. Layout pack development workflow

### 8.1. Tạo layout pack mới

```bash
# Bước 1: Tạo Django app
python manage.py startapp ui_newlayout
# Di chuyển vào apps/

# Bước 2: Đăng ký app
# config/settings/base.py
INSTALLED_APPS += ['apps.ui_newlayout']

# Bước 3: Thêm URL
# config/urls.py
urlpatterns += [path('newlayout/', include('apps.ui_newlayout.urls'))]

# Bước 4: Tạo templates/templates dir
mkdir -p templates/newlayout/base
mkdir -p static/newlayout/{css,js,images}

# Bước 5: Copy base layout từ modern, modify theo ý
cp -r templates/modern/base templates/newlayout/base
# Edit layout.html cho phù hợp

# Bước 6: Implement views (copy từ ui_modern, đổi template_name)
```

### 8.2. Layout pack contract

Mỗi layout pack phải tuân thủ:

1. **URL namespace**: `app_name = 'ui_<layout>'`
2. **URL patterns**: phải có các route tương đương:
   - `dashboard`, `voucher_list`, `voucher_detail`, `voucher_create`
   - `customer_list`, `vendor_list`, `product_list`
   - `sales_invoice_list`, `purchase_invoice_list`, `stock_voucher_list`
   - `report_trial_balance`, `report_balance_sheet`, ...
3. **Service layer**: dùng `apps.<module>.services` (không gọi DB trực tiếp)
4. **Auth/permission**: cùng permission system

### 8.3. Kiểm thử cross-layout

```python
# tests/test_layout_consistency.py
import pytest
from django.urls import reverse

LAYOUTS = ['modern', 'classic', 'mobile']
KEY_ROUTES = [
    'dashboard', 'voucher_list', 'customer_list',
    'sales_invoice_list', 'report_trial_balance',
]


@pytest.mark.parametrize('layout', LAYOUTS)
@pytest.mark.parametrize('route', KEY_ROUTES)
def test_route_exists_for_layout(client, layout, route):
    """Mỗi layout phải có các route cốt lõi"""
    url = reverse(f'ui_{layout}:{route}')
    response = client.get(url)
    assert response.status_code != 404, f"Missing route: {url}"
```

## 9. Phân quyền theo layout

```python
# Permission theo layout
class LayoutPermission(BasePermission):
    """User phải có quyền truy cập layout"""
    def has_permission(self, request, view):
        layout = request.current_layout
        return f'ui.{layout}.access' in request.user_permissions
```

Ví dụ:
- `ui.modern.access` — truy cập Modern UI
- `ui.classic.access` — truy cập Classic UI
- `ui.mobile.access` — truy cập Mobile UI
- `ui.portal.access` — truy cập Portal UI (cho KH/NCC)

## 10. Branding customization

### 10.1. Admin UI cho branding

```python
# apps/system/admin.py
class CompanyAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Thông tin pháp lý', {'fields': ('name', 'tax_code', 'address', ...)}),
        ('Branding', {
            'fields': (
                'brand_name', 'brand_logo', 'brand_logo_dark',
                'brand_favicon', 'brand_primary_color', 'brand_accent_color',
                'brand_sidebar_color',
            ),
            'classes': ('wide',),
        }),
        ('Layout mặc định', {
            'fields': ('default_layout',),
        }),
        ('White-label', {
            'fields': ('hide_pmketoan_branding', 'custom_domain', 'custom_css'),
            'classes': ('collapse',),
        }),
    )
```

### 10.2. CSS theming với variables

Mọi component dùng CSS variables, chỉ cần override `:root` là đổi màu:

```css
/* static/shared/css/variables.css */
:root {
    --color-primary: #2563eb;      /* overridden by brand */
    --color-primary-hover: #1d4ed8;
    --color-primary-light: #dbeafe;
    
    --color-accent: #16a34a;
    --color-success: #16a34a;
    --color-warning: #d97706;
    --color-danger: #dc2626;
    
    --color-text: #111827;
    --color-text-muted: #6b7280;
    --color-bg: #ffffff;
    --color-bg-subtle: #f9fafb;
    --color-border: #e5e7eb;
    
    --sidebar-width: 256px;
    --topbar-height: 56px;
    
    --spacing-unit: 8px;
}

/* Auto-generated từ brand settings */
body[data-brand] {
    --color-primary: var(--brand-primary, #2563eb);
}
```

### 10.3. Custom domain (white-label)

```python
# apps/core/middleware/custom_domain.py
class CustomDomainMiddleware:
    def __call__(self, request):
        host = request.get_host().split(':')[0]  # strip port
        try:
            company = Company.objects.get(custom_domain=host)
            request.current_company = company
            request.current_layout = company.default_layout
        except Company.DoesNotExist:
            pass
        return self.get_response(request)
```

Khi `accounting.acme.com` → auto-redirect tới công ty ACME, dùng brand của ACME.

## 11. Functional requirements bổ sung

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-UI-01 | Hệ thống hỗ trợ ≥2 layout packs chạy song song qua URL riêng | P0 |
| FR-UI-02 | Mỗi layout pack có URL namespace riêng: `/modern/`, `/classic/`, `/mobile/` | P0 |
| FR-UI-03 | Layout switcher component hiển thị ở mọi page, click để đổi UI | P0 |
| FR-UI-04 | Khi đổi layout, giữ nguyên context (cùng voucher, cùng filter) | P1 |
| FR-UI-05 | User có thể đặt preferred layout trong profile | P0 |
| FR-UI-06 | Company có thể đặt default layout cho user mới | P0 |
| FR-UI-07 | Mỗi company có: logo, primary color, accent color, favicon riêng | P0 |
| FR-UI-08 | Hỗ trợ logo light + dark variant (cho sidebar tối) | P1 |
| FR-UI-09 | Hide white-label branding (ẩn "Powered by PMKetoan") | P1 |
| FR-UI-10 | Custom CSS field cho tenant (advanced) | P2 |
| FR-UI-11 | Custom domain: `accounting.acme.com` auto-trỏ tới ACME company | P2 |
| FR-UI-12 | Permission riêng cho từng layout (`ui.modern.access`, ...) | P1 |
| FR-UI-13 | Layout packs cùng dùng chung services và models (DRY) | P0 |
| FR-UI-14 | Test cross-layout: mỗi route cốt lõi phải tồn tại trong mọi layout | P1 |

## 12. Roadmap triển khai

### Phase 1 (Modern UI only)

- Build Modern UI đầy đủ
- Branding infrastructure (logo, colors)
- Company branding fields

**Effort**: ~6 tháng (đã có trong roadmap)

### Phase 2 (Add Classic UI)

- Tạo `apps/ui_classic`
- Copy base từ modern, redesign templates
- Implement top-nav layout
- Add layout switcher
- Implement user layout preference

**Effort**: ~2 tháng

### Phase 3 (Add Mobile UI)

- Tạo `apps/ui_mobile`
- Build PWA (Progressive Web App)
- Offline-first với service worker
- Bottom tab navigation
- Touch-optimized forms

**Effort**: ~2-3 tháng

### Phase 4 (Add Portal UI)

- Tạo `apps/ui_portal`
- OTP login cho customer/vendor
- Limited view (chỉ xem công nợ, hóa đơn)
- Online payment integration

**Effort**: ~2 tháng

**Tổng cộng multi-UI**: thêm 6-7 tháng sau khi Modern UI hoàn thành.

## 13. Trade-offs & considerations

### 13.1. Lợi ích

✅ **User choice**: mỗi user/nhóm dùng UI phù hợp (kế toán lâu năm dùng Classic, sếp dùng Mobile)
✅ **Migration dễ**: KH quen SIS cũ có thể bắt đầu với Classic, dần chuyển sang Modern
✅ **White-label**: bán SaaS cho nhiều company, mỗi nơi brand riêng
✅ **A/B testing**: thử nghiệm UI mới trên subset user
✅ **Backward compatible**: khi Modern redesign, Classic vẫn dùng được

### 13.2. Chi phí

❌ **Code duplication**: mỗi layout pack phải implement view + template riêng (~30% code UI)
❌ **Maintenance burden**: mỗi feature mới phải build cho N layouts
❌ **Test effort**: cross-layout testing cho mỗi feature
❌ **Bundle size**: nhiều CSS/JS hơn (nhưng load riêng per-layout nên OK)

### 13.3. Mitigation

- **Dùng shared services** → business logic chỉ 1 lần
- **Component library** → grid, form field, modal dùng chung
- **Pattern library** → mỗi layout có doc riêng, copy-paste nhanh
- **Layout-agnostic CSS** → dùng CSS variables, ít code chuyên biệt

## 14. Khuyến nghị cuối

Cho **Phase 1**: chỉ build Modern UI đầy đủ + branding infrastructure. Chuẩn bị kiến trúc nhưng chưa build layout packs khác.

Cho **Phase 2+**: thêm Classic UI khi có user feedback (kế toán phàn nàn Modern khó dùng), Mobile UI khi có nhu cầu, Portal UI khi khách hàng yêu cầu.

**Quy ước code** từ đầu:
- View layer trong `apps/ui_<layout>/` (không để view trong `apps/<module>/views/`)
- Template trong `templates/<layout>/`
- Static trong `static/<layout>/`
- Service trong `apps/<module>/services/` (shared)

→ Khi thêm layout pack mới, không phải refactor code cũ.

---

**Trở về**: [README.md](../README.md) | **Tiếp theo**: [06. Component library](./06-component-library.md) (sẽ viết sau)
