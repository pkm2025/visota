# 06. UX Variants Architecture — Đa luồng thao tác

> Thiết kế để **cùng một nghiệp vụ có nhiều cách thực hiện khác nhau**, tùy user và tình huống. Ví dụ: người mới dùng **wizard từng bước**, kế toán lâu năm dùng **form đầy đủ + phím tắt**, nhập liệu nhanh dùng **bulk paste từ Excel**.

## 1. Mục tiêu

- Cùng một operation (ví dụ "tạo hóa đơn") có nhiều **interaction styles** khác nhau
- Mỗi style tối ưu cho **nhóm user hoặc tình huống cụ thể**
- Thêm UX variant mới **không phải sửa code hiện tại** (registry pattern)
- Service layer **dùng chung** — chỉ View + Template khác

## 2. 3 chiều UX (tách bạch)

Hệ thống tách UX thành **3 chiều độc lập**, kết hợp với nhau tạo ra nhiều variant:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Chiều 1: LAYOUT (cấu trúc UI)                                       │
│   Modern │ Classic │ Mobile │ Portal                                │
│   (sidebar trái / top nav / bottom tab / portal KH)                │
└─────────────────────────────────────────────────────────────────────┘
                              ×
┌─────────────────────────────────────────────────────────────────────┐
│ Chiều 2: INTERACTION STYLE (cách thao tác)                          │
│   Guided │ Standard │ Quick │ Bulk                                  │
│   (wizard / form đầy đủ / minimal / paste Excel)                   │
└─────────────────────────────────────────────────────────────────────┘
                              ×
┌─────────────────────────────────────────────────────────────────────┐
│ Chiều 3: WORKFLOW (luồng nghiệp vụ)                                 │
│   Create-from-scratch │ From-template │ From-photo │ From-import   │
│   (nhập tay / dùng mẫu / chụp ảnh / import Excel)                  │
└─────────────────────────────────────────────────────────────────────┘
```

**Ví dụ combination**:
- Modern UI + Guided style + Create-from-scratch → wizard cho người mới
- Modern UI + Standard style + From-template → form đầy đủ với template có sẵn
- Classic UI + Quick style + Bulk → dense grid paste Excel cho kế toán lâu năm

## 3. Chiều 2: Interaction Styles

Mỗi operation có nhiều style. User chọn style phù hợp.

### 3.1. Guided Style — cho người mới

**Đặc điểm**:
- Wizard từng bước, mỗi bước 1-3 fields
- Tooltip giải thích từng field
- Validation ngay sau khi rời field
- Default values được điền sẵn thông minh
- "Skip" cho optional steps
- Hiển thị progress bar
- Có nút "Help" mở video hướng dẫn

**Khi nào dùng**:
- User mới lần đầu dùng phần mềm
- NV không phải kế toán (admin, sale)
- Đào tạo nhân viên mới

```
┌──────────────────────────────────────────────────┐
│ 🧙 Tạo hóa đơn — Bước 2/4                         │
├──────────────────────────────────────────────────┤
│                                                   │
│  Chọn khách hàng                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ [🔍 Tìm KH theo tên hoặc MST...]          │  │
│  │                                            │  │
│  │ Recently used:                             │  │
│  │   ● Công ty ABC (KH001) - MST 0101234567  │  │
│  │   ● Công ty XYZ (KH002) - MST 0307654321  │  │
│  │                                            │  │
│  │ [+ Tạo khách hàng mới]                    │  │
│  └────────────────────────────────────────────┘  │
│                                                   │
│  💡 Mẹo: Nhập MST để auto-điền tên và địa chỉ    │
│                                                   │
│              [Hủy]   [← Quay lại]   [Tiếp →]    │
└──────────────────────────────────────────────────┘
```

### 3.2. Standard Style — cho kế toán chuyên nghiệp (mặc định)

**Đặc điểm**:
- Một màn hình với tất cả fields
- Tabs để phân nhóm (Header / Lines / Attachments)
- Keyboard shortcuts (Ctrl+S save, Ctrl+Enter post, F2 add line)
- Quick add cho master data (KH, HH) inline
- Inline validation (không block)

**Khi nào dùng**:
- Kế toán viên có kinh nghiệm
- Daily operations

```
┌──────────────────────────────────────────────────┐
│ Hóa đơn bán hàng BC0001                  [Lưu][⏹]│
├──────────────────────────────────────────────────┤
│ [Header] [Lines] [Attachments] [Audit]            │
│                                                   │
│ Ngày: [15/06/2026] KH: [KH001 ABC ▼] [+KH]      │
│ NV: [Nguyễn A ▼]  Kho: [KHO_HN ▼]                │
│                                                   │
│ ┌───┬─────┬──────┬──────┬─────┬────┬──────────┐ │
│ │ # │ HH  │ SL   │ ĐG   │ CK% │ VAT│ Thành tiền│ │
│ ├───┼─────┼──────┼──────┼─────┼────┼──────────┤ │
│ │ 1 │ SP1 │ 100  │ 1000 │ 0   │ 10%│ 110.000  │ │
│ │ 2 │ SP2 │  50  │ 2000 │ 5%  │ 10%│ 104.500  │ │
│ │ + │ ... │      │      │     │    │          │ │
│ └───┴─────┴──────┴──────┴─────┴────┴──────────┘ │
│                            Total: 214.500 VND    │
└──────────────────────────────────────────────────┘
```

### 3.3. Quick Style — cho nhập liệu nhanh

**Đặc điểm**:
- Minimal fields, smart defaults
- Type-ahead search
- Auto-calculation
- Enter-to-next-field
- Save & new (liên tục tạo nhiều)

**Khi nào dùng**:
- Nhập nhiều chứng từ tương tự
- Phục vụ window counter (bán lẻ, dịch vụ)
- Bulk data entry

```
┌──────────────────────────────────────────────────┐
│ ⚡ Quick Add Hóa đơn                              │
├──────────────────────────────────────────────────┤
│ KH: [ABC▼]   HH: [SP001▼]   SL: [100]            │
│              Auto: 100.000đ + 10.000đ VAT        │
│              [Enter để lưu, Shift+Enter lưu&mới] │
└──────────────────────────────────────────────────┘
```

### 3.4. Bulk Style — paste từ Excel

**Đặc điểm**:
- Textarea paste từ clipboard
- Auto-parse sang structure
- Preview + validation
- Bulk create

**Khi nào dùng**:
- Import nhiều HĐ từ hệ thống khác
- Nhập liệu cuối ngày / cuối tuần

```
┌──────────────────────────────────────────────────┐
│ 📋 Bulk Import                                    │
├──────────────────────────────────────────────────┤
│ Paste từ Excel (Tab-separated):                   │
│ ┌──────────────────────────────────────────────┐ │
│ │ KH001  SP001  100  1000  10%                │ │
│ │ KH001  SP002   50  2000  10%                │ │
│ │ KH002  SP001  200  1000  10%                │ │
│ │ ...                                          │ │
│ └──────────────────────────────────────────────┘ │
│                                                   │
│ Preview:                                          │
│ 3 hóa đơn sẽ được tạo, tổng 540.000 VND          │
│                                                   │
│ [Validate] [Import]                              │
└──────────────────────────────────────────────────┘
```

## 4. Chiều 3: Workflows

Workflow = nguồn dữ liệu đầu vào cho operation.

### 4.1. Create-from-scratch (mặc định)

Nhập tay từng field.

### 4.2. From-template

User lưu template khi tạo chứng từ, dùng lại sau:

```python
class VoucherTemplate:
    name = 'HĐ bán hàng tiêu chuẩn cho KH ABC'
    voucher_type = 'sales_invoice'
    customer_id = 1  # default
    lines = [
        {'product_id': 5, 'quantity': 100, 'unit_price': 1000},  # default
    ]
```

Click "Dùng mẫu" → form pre-filled → chỉ cần nhập số lượng/ngày.

### 4.3. From-photo (OCR)

Chụp ảnh hóa đơn → OCR → pre-fill form:

```
[Camera/Upload] → OCR xử lý → Hiển thị form với dữ liệu tạm
                                   ↓
                            User xác nhận → Lưu
```

Use case: thu ngân chụp ảnh hóa đơn giấy của NCC → auto-tạo phiếu nhập.

### 4.4. From-import (Excel/CSV)

Import nhiều chứng từ từ file Excel:

```
[Upload .xlsx] → Parse → Preview → Validate → Bulk create
```

### 4.5. From-email (parsable inbox)

Hệ thống có inbox riêng (vd `invoices@yourcompany.pmketoan.vn`). Mọi email gửi tới có attachment PDF hóa đơn → auto-extract → tạo draft phiếu nhập.

### 4.6. From-API (partner integration)

Đối tác push đơn hàng qua API → auto-tạo hóa đơn + phiếu xuất kho.

## 5. Kiến trúc: Plugin Registry Pattern

Để hỗ trợ **vô số** tổ hợp Layout × Style × Workflow mà không sửa code, dùng **registry pattern**.

### 5.1. UX Registry (entry point)

```python
# apps/core/ux/registry.py

class InteractionStyle:
    """Base class cho interaction style"""
    code = None  # 'guided', 'standard', 'quick', 'bulk'
    name = None
    description = None
    
    # Template prefix — render templates từ đây
    template_prefix = None  # 'interaction/guided/'
    
    # URL suffix — /modern/invoice/new/<style>/
    url_suffix = None
    
    # Permissions cần có
    required_permission = None
    
    # Cho operation nào
    supported_operations = []  # ['invoice.create', 'voucher.create']
    
    @classmethod
    def get_template(cls, operation, template_name='form.html'):
        """Return template path cho operation"""
        return f'{cls.template_prefix}/{operation}/{template_name}'
    
    @classmethod
    def get_view_class(cls, operation):
        """Return View class cho operation"""
        # Override trong subclass
        raise NotImplementedError


class GuidedStyle(InteractionStyle):
    code = 'guided'
    name = 'Hướng dẫn'
    description = 'Wizard từng bước cho người mới'
    template_prefix = 'interaction/guided'
    url_suffix = 'guided'
    required_permission = 'ux.guided.use'


class StandardStyle(InteractionStyle):
    code = 'standard'
    name = 'Tiêu chuẩn'
    description = 'Form đầy đủ cho kế toán chuyên nghiệp'
    template_prefix = 'interaction/standard'
    url_suffix = 'standard'  # hoặc '' (default)
    required_permission = None  # mặc định, không cần quyền riêng


class QuickStyle(InteractionStyle):
    code = 'quick'
    name = 'Nhanh'
    description = 'Minimal fields, smart defaults'
    template_prefix = 'interaction/quick'
    url_suffix = 'quick'
    required_permission = 'ux.quick.use'


class BulkStyle(InteractionStyle):
    code = 'bulk'
    name = 'Hàng loạt'
    description = 'Paste/import nhiều cùng lúc'
    template_prefix = 'interaction/bulk'
    url_suffix = 'bulk'
    required_permission = 'ux.bulk.use'


# Registry
class InteractionStyleRegistry:
    _registry = {}
    
    @classmethod
    def register(cls, style_class):
        cls._registry[style_class.code] = style_class
    
    @classmethod
    def get(cls, code):
        return cls._registry.get(code)
    
    @classmethod
    def all(cls):
        return list(cls._registry.values())
    
    @classmethod
    def for_operation(cls, operation):
        """Lấy tất cả styles hỗ trợ operation này"""
        return [s for s in cls.all() if operation in s.supported_operations]
    
    @classmethod
    def for_user(cls, user, operation):
        """Lấy styles user được phép dùng cho operation"""
        return [
            s for s in cls.for_operation(operation)
            if not s.required_permission or user.has_perm(s.required_permission)
        ]


# Register built-in styles
InteractionStyleRegistry.register(GuidedStyle)
InteractionStyleRegistry.register(StandardStyle)
InteractionStyleRegistry.register(QuickStyle)
InteractionStyleRegistry.register(BulkStyle)

# Third-party có thể register thêm trong apps.py:
# from apps.core.ux.registry import InteractionStyleRegistry
# InteractionStyleRegistry.register(VoiceInputStyle)
```

### 5.2. Workflow Registry

```python
# apps/core/ux/workflows.py

class Workflow:
    """Nguồn dữ liệu đầu vào cho operation"""
    code = None  # 'scratch', 'template', 'photo', 'import', 'email'
    name = None
    supported_operations = []
    
    @classmethod
    def get_view_class(cls, operation):
        raise NotImplementedError


class FromScratchWorkflow(Workflow):
    code = 'scratch'
    name = 'Nhập mới'
    supported_operations = ['invoice.create', 'voucher.create', 'customer.create']


class FromTemplateWorkflow(Workflow):
    code = 'template'
    name = 'Từ mẫu'
    supported_operations = ['invoice.create', 'voucher.create']
    
    @classmethod
    def get_view_class(cls, operation):
        return FromTemplateView  # Hiển thị list templates → chọn → tạo


class FromPhotoWorkflow(Workflow):
    code = 'photo'
    name = 'Từ ảnh (OCR)'
    supported_operations = ['invoice.create', 'purchase_invoice.create']
    
    @classmethod
    def get_view_class(cls, operation):
        return FromPhotoView  # Upload → OCR → preview → confirm


class FromImportWorkflow(Workflow):
    code = 'import'
    name = 'Import Excel'
    supported_operations = ['customer.create', 'product.create', 'invoice.create']


class WorkflowRegistry:
    _registry = {}
    
    @classmethod
    def register(cls, workflow_class):
        cls._registry[workflow_class.code] = workflow_class
    
    # ... get, all, for_operation, for_user ...
```

### 5.3. UX Context cho View

```python
# apps/core/ux/context.py
from dataclasses import dataclass


@dataclass
class UXContext:
    """Context cho mọi view, xác định UX variant nào đang được dùng"""
    layout: str          # 'modern', 'classic', 'mobile', 'portal'
    style: str           # 'guided', 'standard', 'quick', 'bulk'
    workflow: str        # 'scratch', 'template', 'photo', 'import'
    
    @classmethod
    def from_request(cls, request):
        layout = getattr(request, 'current_layout', 'modern')
        style = request.GET.get('style') or request.session.get(
            f'ux_style_{layout}', 
            cls.default_style_for_layout(layout)
        )
        workflow = request.GET.get('workflow', 'scratch')
        return cls(layout=layout, style=style, workflow=workflow)
    
    @staticmethod
    def default_style_for_layout(layout):
        # Mobile default = guided (touch-friendly)
        # Portal default = standard (KH chỉ xem)
        # Modern/Classic default = standard
        return {
            'mobile': 'guided',
            'portal': 'standard',
        }.get(layout, 'standard')
    
    def get_template(self, operation, template_name='form.html'):
        """Get template path: e.g. 'modern/invoice/create/guided/form.html'"""
        return f'{self.layout}/{operation}/{self.style}/{template_name}'


# Usage in view:
def create_invoice(request):
    ux = UXContext.from_request(request)
    template = ux.get_template('invoice/create', 'form.html')
    # → 'modern/invoice/create/guided/form.html' nếu user dùng guided
    
    return render(request, template, {
        'ux': ux,
        # ... form context ...
    })
```

### 5.4. URL routing tự động theo registry

Thay vì hard-code URL cho từng combination:

```python
# apps/ui_modern/urls.py
from django.urls import path
from apps.core.ux.registry import InteractionStyleRegistry
from .views import CreateInvoiceView

app_name = 'ui_modern'

# Dynamic URL routing cho mọi interaction styles
invoice_create_patterns = [path('', CreateInvoiceView.as_view(), name='invoice_create')]

for style in InteractionStyleRegistry.all():
    if 'invoice.create' in style.supported_operations:
        invoice_create_patterns.append(
            path(f'{style.url_suffix}/', CreateInvoiceView.as_view(), 
                 name=f'invoice_create_{style.code}',
                 kwargs={'style_code': style.code})
        )

urlpatterns = [
    path('invoices/new/', include(invoice_create_patterns)),
    # → /modern/invoices/new/                 (standard)
    # → /modern/invoices/new/guided/          (guided)
    # → /modern/invoices/new/quick/           (quick)
    # → /modern/invoices/new/bulk/            (bulk)
]
```

### 5.5. View dispatcher theo style

```python
# apps/ui_modern/views/invoice_views.py
from django.views import View
from apps.core.ux.context import UXContext
from apps.core.ux.registry import InteractionStyleRegistry


class CreateInvoiceView(View):
    """Dispatcher: chọn view con theo interaction style"""
    
    def get(self, request, style_code=None, **kwargs):
        ux = UXContext.from_request(request)
        if style_code:
            ux.style = style_code
        
        # Get style-specific view
        style_class = InteractionStyleRegistry.get(ux.style)
        view_class = style_class.get_view_class('invoice.create')
        
        if not view_class or 'invoice.create' not in style_class.supported_operations:
            # Fallback to standard
            style_class = InteractionStyleRegistry.get('standard')
            view_class = style_class.get_view_class('invoice.create')
        
        # Delegate to style-specific view
        return view_class.as_view()(request, ux=ux, **kwargs)
    
    def post(self, request, *args, **kwargs):
        # Tương tự get
        pass
```

### 5.6. Style-specific views

```python
# apps/ui_modern/views/invoice/guided_view.py
class GuidedCreateInvoiceView(View):
    """Wizard-style: 4 steps"""
    template_name = 'modern/invoice/create/guided/wizard.html'
    
    def get(self, request, ux=None, **kwargs):
        step = int(request.GET.get('step', 1))
        form = GuidedInvoiceForm(step=step, ...)
        return render(request, self.template_name, {
            'ux': ux,
            'step': step,
            'form': form,
        })
    
    def post(self, request, ux=None, **kwargs):
        step = int(request.POST.get('step', 1))
        if step < 4:
            # Save to session, go to next step
            request.session[f'invoice_wizard_step_{step}'] = request.POST
            return redirect(f'?step={step+1}')
        else:
            # Final step: gather all session data → create
            data = self._gather_wizard_data(request)
            service = InvoiceService(request)
            invoice = service.create(data)
            return redirect(invoice.get_absolute_url())


# apps/ui_modern/views/invoice/standard_view.py
class StandardCreateInvoiceView(View):
    """Single-page form with all fields"""
    template_name = 'modern/invoice/create/standard/form.html'
    
    def get(self, request, ux=None, **kwargs):
        form = StandardInvoiceForm()
        return render(request, self.template_name, {'ux': ux, 'form': form})


# apps/ui_modern/views/invoice/quick_view.py
class QuickCreateInvoiceView(View):
    """Minimal form, smart defaults"""
    template_name = 'modern/invoice/create/quick/form.html'
    
    def get(self, request, ux=None, **kwargs):
        form = QuickInvoiceForm(initial=self._get_smart_defaults(request))
        return render(request, self.template_name, {'ux': ux, 'form': form})


# apps/ui_modern/views/invoice/bulk_view.py
class BulkCreateInvoiceView(View):
    """Paste from Excel"""
    template_name = 'modern/invoice/create/bulk/form.html'
    
    def get(self, request, ux=None, **kwargs):
        form = BulkInvoiceForm()
        return render(request, self.template_name, {'ux': ux, 'form': form})
```

### 5.7. Style registry registration (trong apps.py)

```python
# apps/ui_modern/apps.py
from django.apps import AppConfig


class UiModernConfig(AppConfig):
    name = 'apps.ui_modern'
    
    def ready(self):
        # Register style-specific views cho layout Modern
        from apps.core.ux.registry import InteractionStyleRegistry, GuidedStyle, \
            StandardStyle, QuickStyle, BulkStyle
        from .views.invoice.guided_view import GuidedCreateInvoiceView
        from .views.invoice.standard_view import StandardCreateInvoiceView
        from .views.invoice.quick_view import QuickCreateInvoiceView
        from .views.invoice.bulk_view import BulkCreateInvoiceView
        
        # Bind views cho operation 'invoice.create'
        GuidedStyle.bind_view('invoice.create', GuidedCreateInvoiceView)
        StandardStyle.bind_view('invoice.create', StandardCreateInvoiceView)
        QuickStyle.bind_view('invoice.create', QuickCreateInvoiceView)
        BulkStyle.bind_view('invoice.create', BulkCreateInvoiceView)
```

Tương tự cho `ui_classic`, `ui_mobile`, `ui_portal` — mỗi layout bind view riêng.

## 6. Template structure cho UX variants

```
templates/
├── shared/                              ← Components dùng chung mọi layout/style
│   ├── components/
│   │   ├── data_grid.html
│   │   ├── form_field.html
│   │   └── ...
│   └── _layout_switcher.html
│
├── modern/                              ← Modern layout
│   ├── base/
│   │   └── layout.html
│   ├── invoice/
│   │   ├── list.html                    ← List view (chung mọi style)
│   │   ├── detail.html                  ← Detail view (chung)
│   │   └── create/
│   │       ├── guided/                  ← Style: guided (wizard)
│   │       │   ├── wizard.html
│   │       │   ├── _step1_customer.html
│   │       │   ├── _step2_products.html
│   │       │   ├── _step3_summary.html
│   │       │   └── _step4_confirm.html
│   │       ├── standard/                ← Style: standard (full form)
│   │       │   ├── form.html
│   │       │   ├── _header.html
│   │       │   ├── _lines.html
│   │       │   └── _actions.html
│   │       ├── quick/                   ← Style: quick (minimal)
│   │       │   └── form.html
│   │       └── bulk/                    ← Style: bulk (paste)
│   │           ├── form.html
│   │           └── _preview.html
│   │
│   ├── voucher/
│   │   └── create/
│   │       ├── guided/
│   │       ├── standard/
│   │       └── ...
│   └── ...
│
├── classic/                             ← Classic layout (tương tự)
│   ├── invoice/create/
│   │   ├── guided/                      ← Classic + Guided
│   │   ├── standard/                    ← Classic + Standard
│   │   └── ...
│   └── ...
│
├── mobile/
│   └── ...
└── portal/
    └── ...
```

## 7. Smart UX selection

Hệ thống tự đề xuất UX variant phù hợp:

### 7.1. Theo user role

```python
# apps/core/ux/defaults.py
ROLE_DEFAULT_UX = {
    'admin':           {'layout': 'modern',  'style': 'standard'},
    'chief_accountant': {'layout': 'classic', 'style': 'standard'},
    'accountant':      {'layout': 'modern',  'style': 'standard'},
    'data_entry':      {'layout': 'modern',  'style': 'quick'},
    'sales':           {'layout': 'modern',  'style': 'guided'},
    'manager':         {'layout': 'modern',  'style': 'standard'},
    'auditor':         {'layout': 'classic', 'style': 'standard'},
    'customer':        {'layout': 'portal',  'style': 'standard'},
}


def suggest_ux_for_user(user, company):
    """Suggest UX defaults cho user mới"""
    role = user.get_role_in(company)
    return ROLE_DEFAULT_UX.get(role.code, {'layout': 'modern', 'style': 'standard'})
```

### 7.2. Theo context (new user, after error, etc.)

```python
# Khi user mới đăng nhập lần đầu → tự động đề xuất guided
if user.login_count == 1:
    suggested_ux = {'layout': 'modern', 'style': 'guided'}
    show_notification("Bạn có muốn dùng chế độ hướng dẫn không?")

# Khi user gặp lỗi validation nhiều lần → đề xuất chuyển sang guided
if user.recent_errors > 3:
    suggest("Chế độ hướng dẫn có thể giúp bạn nhập chính xác hơn")
```

### 7.3. UX switcher UI

Trong top bar, có dropdown chọn UX:

```html
<div class="ux-switcher">
    <button class="btn btn-light btn-sm">
        <i class="bi bi-gear"></i> UX
    </button>
    <div class="dropdown-menu">
        <h6>Layout</h6>
        <a href="/modern/...">Modern</a>
        <a href="/classic/...">Classic</a>
        <a href="/mobile/...">Mobile</a>
        
        <h6>Interaction Style</h6>
        <a href="?style=guided">Guided (cho người mới)</a>
        <a href="?style=standard">Standard</a>
        <a href="?style=quick">Quick (nhập nhanh)</a>
        <a href="?style=bulk">Bulk (paste Excel)</a>
        
        <h6>Workflow</h6>
        <a href="?workflow=scratch">Nhập mới</a>
        <a href="?workflow=template">Từ mẫu</a>
        <a href="?workflow=photo">Từ ảnh (OCR)</a>
        <a href="?workflow=import">Import Excel</a>
    </div>
</div>
```

## 8. Onboarding flow cho người mới

Quy trình khi user mới login lần đầu:

```
1. Welcome modal:
   "Chào mừng bạn đến với PMKetoan!"
   "Bạn là ai?"
   □ Kế toán viên     → suggest Modern + Standard
   □ Kế toán trưởng   → suggest Classic + Standard
   □ Nhân viên bán hàng → suggest Modern + Guided
   □ Quản lý          → suggest Modern + Standard (read-only bias)
   □ Tôi chưa rõ     → suggest Modern + Guided (default)

2. Tour wizard (3 phút):
   - Step 1: Tạo chứng từ đầu tiên (guided style)
   - Step 2: Xem báo cáo tổng quan
   - Step 3: Chỉnh sửa profile + UX preference

3. First-week nudges:
   - Sau 3 ngày: "Bạn đã thử chế độ Quick chưa?"
   - Sau 7 ngày: "Đã đến lúc thử Classic UI?"
   - Save user preference sau khi thử

4. Progressive disclosure:
   - Standard style: ẩn advanced features mặc định
   - Có nút "Hiển thị tính năng nâng cao"
```

## 9. Code organization

```
apps/
├── core/
│   ├── ux/                               ← UX framework (shared)
│   │   ├── __init__.py
│   │   ├── registry.py                   ← InteractionStyleRegistry
│   │   ├── workflows.py                  ← WorkflowRegistry
│   │   ├── context.py                    ← UXContext
│   │   ├── defaults.py                   ← Smart defaults
│   │   ├── middleware.py                 ← UX detection middleware
│   │   └── permissions.py                ← UX permission checks
│   │
│   └── ...
│
├── ledger/                               ← Shared services (no views)
│   ├── services/
│   │   └── invoice_service.py            ← InvoiceService.create()
│   └── ...
│
├── ui_modern/
│   ├── views/
│   │   ├── invoice/
│   │   │   ├── __init__.py
│   │   │   ├── list_view.py              ← List (chung mọi style)
│   │   │   ├── detail_view.py            ← Detail (chung)
│   │   │   ├── create_view.py            ← Dispatcher
│   │   │   ├── guided_create_view.py     ← Style-specific
│   │   │   ├── standard_create_view.py
│   │   │   ├── quick_create_view.py
│   │   │   └── bulk_create_view.py
│   │   │
│   │   ├── voucher/
│   │   │   └── (tương tự)
│   │   └── ...
│   │
│   ├── workflows/                        ← Workflow-specific views
│   │   ├── __init__.py
│   │   ├── from_template.py
│   │   ├── from_photo.py
│   │   └── from_import.py
│   │
│   └── apps.py                           ← Register styles + bind views
│
├── ui_classic/
│   └── (tương tự, có thể bind views khác)
│
└── ...
```

## 10. Testing cross-UX

```python
# tests/test_ux_consistency.py
import pytest
from apps.core.ux.registry import InteractionStyleRegistry, WorkflowRegistry

LAYOUTS = ['modern', 'classic', 'mobile', 'portal']
STYLES = InteractionStyleRegistry.all_codes()
OPERATIONS = ['invoice.create', 'voucher.create', 'customer.create']


@pytest.mark.parametrize('layout', LAYOUTS)
@pytest.mark.parametrize('style', STYLES)
@pytest.mark.parametrize('operation', OPERATIONS)
def test_ux_variant_exists(client, layout, style, operation):
    """Mỗi tổ hợp layout × style × operation phải có route + template"""
    style_class = InteractionStyleRegistry.get(style)
    if operation not in style_class.supported_operations:
        pytest.skip(f"Style {style} doesn't support {operation}")
    
    url = reverse(f'ui_{layout}:{operation}_{style}')
    response = client.get(url)
    assert response.status_code == 200
    
    # Verify template exists
    template = response.templates[0]
    assert template.name.startswith(f'{layout}/')


def test_smart_defaults_for_new_user(new_user):
    """User mới được suggest Guided style"""
    ux = suggest_ux_for_user(new_user, new_user.company)
    assert ux['style'] == 'guided'


def test_user_can_override_ux(authenticated_client):
    """User có thể đổi style trong session"""
    authenticated_client.post('/ux-preference/', {'style': 'quick'})
    response = authenticated_client.get('/modern/invoices/new/')
    assert response.context['ux'].style == 'quick'
```

## 11. Functional requirements bổ sung

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-UX-17 | Hệ thống phân tách UX thành 3 chiều: Layout, Interaction Style, Workflow | P0 |
| FR-UX-18 | Hỗ trợ ≥3 interaction styles: Guided, Standard, Quick | P0 |
| FR-UX-19 | Hỗ trợ ≥2 workflows: From-scratch, From-template | P0 |
| FR-UX-20 | Plugin registry cho phép đăng ký UX variant mới mà không sửa core code | P0 |
| FR-UX-21 | Smart UX defaults theo user role (kế toán → Standard, sales → Guided, ...) | P1 |
| FR-UX-22 | UX switcher UI ở top bar cho phép đổi style nhanh | P0 |
| FR-UX-23 | User preference lưu được UX choice (per user, per layout) | P0 |
| FR-UX-24 | Onboarding flow cho user mới (welcome modal, tour wizard, first-week nudges) | P1 |
| FR-UX-25 | Guided style phải có: progress bar, tooltip, validation inline, smart defaults | P0 |
| FR-UX-26 | Quick style phải có: type-ahead search, Enter-to-next, save & new | P0 |
| FR-UX-27 | Bulk style phải có: paste Excel, preview, validation, bulk create | P0 |
| FR-UX-28 | From-photo workflow (OCR) cho phép chụp ảnh hóa đơn → auto-fill | P2 |
| FR-UX-29 | From-import workflow cho phép upload Excel/CSV nhiều dòng | P0 |
| FR-UX-30 | Voucher templates: user lưu + dùng lại được | P0 |
| FR-UX-31 | Tổ hợp Layout × Style × Workflow phải có route riêng (vd `/modern/invoices/new/guided/`) | P0 |
| FR-UX-32 | Test cross-UX: mỗi operation phải work với mọi supported style | P1 |

## 12. Roadmap triển khai UX variants

### Phase 1-6: Foundation + Standard style only

- Build shared services + Standard style đầy đủ
- UX framework setup (registry, context, dispatcher)
- Mọi operation có Standard style
- UX switcher UI (placeholder cho styles khác)

**Effort**: trong scope Phase 1-6 (~9-10 tháng)

### Phase 7: Guided style cho core operations

- Add Guided wizard cho: create invoice, create voucher, period closing
- Onboarding flow cho user mới
- Smart defaults

**Effort**: 1-2 tháng

### Phase 8: Quick + Bulk styles

- Add Quick cho: create invoice, create voucher
- Add Bulk paste Excel cho: invoices, vouchers, customers, products
- From-import workflow

**Effort**: 1-2 tháng

### Phase 9: Advanced workflows

- From-template (voucher templates)
- From-photo (OCR integration)
- From-email (inbox parsing)

**Effort**: 2-3 tháng

### Phase 10: Role-based UX profiles + AI suggestions

- Auto-suggest UX theo role và usage pattern
- A/B testing infrastructure cho UX variants
- Personalization

**Effort**: 2 tháng

## 13. Lợi ích kiến trúc

✅ **Future-proof**: thêm UX mới = register 1 class, không refactor
✅ **A/B testing**: thử nghiệm UX mới trên subset user dễ dàng
✅ **Personalization**: mỗi user/nhóm dùng UX tối ưu
✅ **Third-party UX**: partner có thể build custom UX (SDK)
✅ **Backward compatible**: khi thêm style mới, style cũ vẫn dùng được
✅ **Service reuse**: business logic 1 lần, chia sẻ cho mọi UX variant

## 14. Trade-offs

❌ **Code complexity tăng**: dispatcher pattern, registry, context object
❌ **Template duplication**: mỗi style có template riêng
❌ **Test effort**: N layouts × M styles × K workflows = nhiều combinations

### Mitigation

- **Component library**: grid, form field, modal dùng chung mọi style
- **Template inheritance**: Guided extends BaseForm, override chỉ phần khác
- **Service layer reuse**: business logic 1 lần, được test độc lập
- **Automated cross-UX testing**: parametrize tests cho mọi combinations
- **Progressive rollout**: thêm style mới theo nhu cầu thực tế, không build all upfront

---

**Trở về**: [README.md](../README.md) | **Tiếp theo**: [07. Onboarding UX](./07-onboarding-ux.md) (sẽ viết sau)
