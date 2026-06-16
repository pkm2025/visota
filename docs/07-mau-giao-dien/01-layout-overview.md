# 01. Layout tổng thể

> Quy ước layout chung cho toàn bộ ứng dụng.

## 1. Wireframe tổng thể

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [Logo] PMKetoan              [Search...]    [🔔3] [📅] [Website][Help] [▼SIS]
└─────────────────────────────────────────────────────────────────────────┘
│                                                                          │
│ ┌────────────────┐  ┌─────────────────────────────────────────────────┐ │
│ │                │  │  [Tab] [Tab] [Tab] [Tab] [Tab]                  │ │
│ │  [Tổng hợp ▼]  │  ├─────────────────────────────────────────────────┤ │
│ │                │  │                                                  │ │
│ │  Cập nhật số   │  │   Nội dung chính (main content)                  │ │
│ │  liệu    [▼]   │  │                                                  │ │
│ │  • Phiếu KT     │  │                                                  │ │
│ │  • Kết chuyển   │  │                                                  │ │
│ │  • Phân bổ      │  │                                                  │ │
│ │                │  │                                                  │ │
│ │  Sổ sách  [▼]  │  │                                                  │ │
│ │  • Nhật ký chung│  │                                                  │ │
│ │  • Sổ cái      │  │                                                  │ │
│ │                │  │                                                  │ │
│ │  Báo cáo  [▼]  │  │                                                  │ │
│ │  • BCĐTK       │  │                                                  │ │
│ │  • B01-DN      │  │                                                  │ │
│ │  • B02-DN      │  │                                                  │ │
│ │                │  │                                                  │ │
│ │  Danh mục [▼]  │  │                                                  │ │
│ │  • Tài khoản   │  │                                                  │ │
│ │  • Khách hàng  │  │                                                  │ │
│ │  • Hàng hóa    │  │                                                  │ │
│ │                │  │                                                  │ │
│ └────────────────┘  └─────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2. Kích thước & spacing

| Element | Size |
|---------|------|
| Sidebar width | 256px (desktop), collapse to 64px (mobile) |
| Topbar height | 56px |
| Content padding | 24px (desktop), 16px (mobile) |
| Card border radius | 8px |
| Button padding | 8px 16px |
| Form field height | 38px (default), 32px (small), 44px (large) |
| Grid row height | 36px |
| Font size base | 14px |
| Font size heading | 18px / 22px / 28px |
| Icon size | 16px (small), 20px (default), 24px (large) |

## 3. Color palette

```css
:root {
    /* Primary - Brand blue */
    --primary-50: #eff6ff;
    --primary-100: #dbeafe;
    --primary-500: #3b82f6;
    --primary-600: #2563eb;
    --primary-700: #1d4ed8;
    
    /* Success - Green */
    --success-50: #f0fdf4;
    --success-500: #22c55e;
    --success-600: #16a34a;
    
    /* Warning - Amber */
    --warning-50: #fffbeb;
    --warning-500: #f59e0b;
    --warning-600: #d97706;
    
    /* Danger - Red */
    --danger-50: #fef2f2;
    --danger-500: #ef4444;
    --danger-600: #dc2626;
    
    /* Gray scale */
    --gray-50: #f9fafb;
    --gray-100: #f3f4f6;
    --gray-200: #e5e7eb;
    --gray-300: #d1d5db;
    --gray-400: #9ca3af;
    --gray-500: #6b7280;
    --gray-600: #4b5563;
    --gray-700: #374151;
    --gray-800: #1f2937;
    --gray-900: #111827;
    
    /* Semantic */
    --color-bg: #ffffff;
    --color-bg-subtle: var(--gray-50);
    --color-bg-muted: var(--gray-100);
    --color-border: var(--gray-200);
    --color-text: var(--gray-900);
    --color-text-muted: var(--gray-500);
    --color-link: var(--primary-600);
    
    /* Accounting-specific */
    --color-debit: var(--success-600);   /* Nợ: xanh */
    --color-credit: var(--danger-600);   /* Có: đỏ */
    --color-negative: var(--danger-600); /* Số âm */
}
```

## 4. Typography

```css
body {
    font-family: 'Be Vietnam Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    color: var(--color-text);
}

/* Headings */
h1 { font-size: 28px; font-weight: 700; margin-bottom: 16px; }
h2 { font-size: 22px; font-weight: 600; margin-bottom: 12px; }
h3 { font-size: 18px; font-weight: 600; margin-bottom: 8px; }

/* Numeric (accounting) */
.num, .font-mono {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.02em;
}

/* Negative numbers in red */
.negative { color: var(--color-negative); }

/* Vietnamese number format */
.num-vi { /* formatted as 1.234.567,89 */ }
```

## 5. Components inventory

### 5.1. Buttons

```html
<button class="btn btn-primary">Lưu</button>
<button class="btn btn-secondary">Hủy</button>
<button class="btn btn-success">Ghi sổ</button>
<button class="btn btn-danger">Xóa</button>
<button class="btn btn-warning">Mở khóa</button>
<button class="btn btn-outline-secondary">Xuất Excel</button>
<button class="btn btn-sm btn-primary">Thêm dòng</button>
<button class="btn btn-icon"><i class="bi bi-pencil"></i></button>
```

### 5.2. Form fields

```html
<!-- Text input -->
<div class="form-group">
    <label for="voucher_no">Số chứng từ <span class="text-red-500">*</span></label>
    <input type="text" id="voucher_no" name="voucher_no" 
           class="form-control" required>
</div>

<!-- Select -->
<div class="form-group">
    <label for="customer_id">Khách hàng</label>
    <select id="customer_id" name="customer_id" class="form-control select2">
        <option value="">-- Chọn --</option>
        ...
    </select>
</div>

<!-- Date -->
<div class="form-group">
    <label>Ngày chứng từ</label>
    <input type="date" name="voucher_date" class="form-control">
</div>

<!-- Amount with auto-format -->
<div class="form-group">
    <label>Tiền nợ</label>
    <input type="text" name="debit_vnd" 
           class="form-control text-right num-vi"
           x-model="debit" @input="formatAmount">
</div>

<!-- Checkbox -->
<div class="form-check">
    <input type="checkbox" id="is_posted" name="is_posted" class="form-check-input">
    <label for="is_posted" class="form-check-label">Đăng sổ cái</label>
</div>
```

### 5.3. Badges / Status pills

```html
<span class="badge bg-warning">Lưu tạm</span>
<span class="badge bg-info">Sổ phụ</span>
<span class="badge bg-success">Đã ghi sổ</span>
<span class="badge bg-secondary">Đã khóa</span>
<span class="badge bg-danger">Đã hủy</span>
```

### 5.4. Alerts

```html
<div class="alert alert-success">
    <i class="bi bi-check-circle"></i> Đã ghi sổ thành công
</div>
<div class="alert alert-warning">
    <i class="bi bi-exclamation-triangle"></i> Tồn kho dưới mức tối thiểu
</div>
<div class="alert alert-danger">
    <i class="bi bi-x-circle"></i> Chứng từ không cân đối
</div>
```

### 5.5. Toast notifications

Auto-dismiss sau 5s, top-right.

```html
<div class="toast toast-success">
    <div class="toast-icon"><i class="bi bi-check"></i></div>
    <div class="toast-content">
        <div class="toast-title">Thành công</div>
        <div class="toast-message">Đã ghi sổ phiếu BC0001</div>
    </div>
    <button class="toast-close">×</button>
</div>
```

### 5.6. Modal dialog

```html
<div class="modal-overlay" x-show="showModal" x-transition>
    <div class="modal-dialog">
        <div class="modal-header">
            <h3 class="modal-title">Xác nhận xóa</h3>
            <button class="modal-close" @click="showModal = false">×</button>
        </div>
        <div class="modal-body">
            <p>Bạn có chắc muốn xóa phiếu <strong>BC0001</strong>?</p>
            <p class="text-muted">Hành động này không thể hoàn tác.</p>
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary" @click="showModal = false">Hủy</button>
            <button class="btn btn-danger" @click="confirmDelete">Xóa</button>
        </div>
    </div>
</div>
```

### 5.7. Tabs

```html
<ul class="nav nav-tabs">
    <li class="nav-item">
        <a class="nav-link active" data-bs-toggle="tab" href="#tab-info">
            Thông tin chung
        </a>
    </li>
    <li class="nav-item">
        <a class="nav-link" data-bs-toggle="tab" href="#tab-lines">
            Bút toán
        </a>
    </li>
    <li class="nav-item">
        <a class="nav-link" data-bs-toggle="tab" href="#tab-audit">
            Lịch sử
        </a>
    </li>
</ul>
<div class="tab-content">
    <div class="tab-pane fade show active" id="tab-info">...</div>
    <div class="tab-pane fade" id="tab-lines">...</div>
    <div class="tab-pane fade" id="tab-audit">...</div>
</div>
```

## 6. Page types

### 6.1. List page

```
┌────────────────────────────────────────────────────┐
│ [Page Title]                    [Export] [+ New]   │
├────────────────────────────────────────────────────┤
│ [Filter bar: search + date range + status]         │
├────────────────────────────────────────────────────┤
│ [Master grid]                                      │
│                                                    │
│                                                    │
├────────────────────────────────────────────────────┤
│ [Pagination: 1 2 3 ... > | 25 per page]            │
└────────────────────────────────────────────────────┘
```

### 6.2. Master-Detail page

```
┌────────────────────────────────────────────────────┐
│ [Page Title]                    [Export] [+ New]   │
├────────────────────────────────────────────────────┤
│ [Filter bar]                                       │
├──────────────────────────────┬─────────────────────┤
│ [Master grid - 2/3 width]    │ [Detail - 1/3]      │
│                              │                     │
│                              │                     │
│                              │                     │
├──────────────────────────────┴─────────────────────┤
│ [Pagination]                                       │
└────────────────────────────────────────────────────┘
```

### 6.3. Form page (single record)

```
┌────────────────────────────────────────────────────┐
│ [Page Title] [breadcrumb]                          │
├────────────────────────────────────────────────────┤
│ [Card: Header info]                                │
│  Field1 | Field2 | Field3 | Field4                 │
├────────────────────────────────────────────────────┤
│ [Card: Lines]                                      │
│  [Add line] button                                 │
│                                                    │
│  Table:                                            │
│  Line# | Field | Field | [delete]                  │
│  Line# | Field | Field | [delete]                  │
├────────────────────────────────────────────────────┤
│ [Actions: Cancel] [Save Draft] [Save & Post]       │
└────────────────────────────────────────────────────┘
```

### 6.4. Report page

```
┌────────────────────────────────────────────────────┐
│ [Report Title]                                     │
├────────────────────────────────────────────────────┤
│ [Filter bar: period, accounts, format]             │
│ [Generate] [Export PDF] [Export Excel] [Save as]   │
├────────────────────────────────────────────────────┤
│ [Report content - formatted table]                 │
│                                                    │
│                                                    │
│                                                    │
├────────────────────────────────────────────────────┤
│ [Footer: generated at, generated by]               │
└────────────────────────────────────────────────────┘
```

### 6.5. Dashboard

```
┌────────────────────────────────────────────────────┐
│ [Dashboard]                                        │
├────────────────────────────────────────────────────┤
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐               │
│ │ KPI 1│ │ KPI 2│ │ KPI 3│ │ KPI 4│               │
│ └──────┘ └──────┘ └──────┘ └──────┘               │
├────────────────────────────────────────────────────┤
│ ┌──────────────────┐  ┌──────────────────┐         │
│ │ Chart: Revenue   │  │ Chart: AR Aging  │         │
│ └──────────────────┘  └──────────────────┘         │
├────────────────────────────────────────────────────┤
│ [Recent vouchers table]                            │
└────────────────────────────────────────────────────┘
```

## 7. Responsive breakpoints

| Breakpoint | Width | Layout |
|-----------|-------|--------|
| Mobile | < 640px | Single column, hamburger menu |
| Tablet | 640-1024px | 2 column where appropriate |
| Desktop | 1024-1280px | Full sidebar + content |
| Large | > 1280px | Wide content, optional right rail |

## 8. Empty states

```html
<div class="empty-state">
    <i class="bi bi-inbox text-4xl text-gray-400"></i>
    <h3 class="mt-4">Không có dữ liệu</h3>
    <p class="text-gray-500">Chưa có chứng từ nào trong kỳ này.</p>
    <button class="btn btn-primary mt-4">
        <i class="bi bi-plus"></i> Tạo chứng từ đầu tiên
    </button>
</div>
```

## 9. Loading states

### 9.1. Page loading

```html
<div class="page-loader">
    <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Đang tải...</span>
    </div>
</div>
```

### 9.2. HTMX loading indicator

```html
<div hx-get="/api/..." hx-indicator="#loader">
    Content
</div>
<div id="loader" class="htmx-indicator">
    <i class="bi bi-arrow-clockwise bi-spin"></i>
</div>
```

### 9.3. Skeleton loading

```html
<div class="skeleton skeleton-text"></div>
<div class="skeleton skeleton-text w-3/4"></div>
<div class="skeleton skeleton-button"></div>
```

## 10. Accessibility

- Skip to content link
- ARIA labels cho icon buttons
- Keyboard navigation (Tab order)
- Focus visible
- High contrast mode support
- Screen reader announcements for dynamic content

---

**Tiếp theo**: [02. Grid master-detail](./02-grid-master-detail.md)
