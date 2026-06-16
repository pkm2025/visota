# 02. Grid Master-Detail Component

> Component tái sử dụng cho mọi màn hình list (Phiếu KT, KH, NCC, ...).

## 1. Tổng quan

Đây là **component quan trọng nhất** của PMKetoan, được dùng ở ~80% màn hình.

**Đặc điểm**:
- Master grid (bảng dữ liệu chính) + Detail panel (chi tiết dòng chọn)
- Server-side pagination
- Inline filtering ở header column
- Row click → load detail qua HTMX
- Multi-select với checkbox
- Context menu (right-click) cho actions
- Export Excel/PDF

## 2. Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [Page Title]                                            [Export] [+ New] │
├─────────────────────────────────────────────────────────────────────────┤
│ [🔍 Search...]  [Status ▼] [Date ▼] [Type ▼]    [Show filters] [Reset] │
├─────────────────────────────────────────────────────────────────────────┤
│ ☐ │ Date       │ Number   │ Description       │ Amount     │ Status     │
│───┼────────────┼──────────┼───────────────────┼────────────┼────────────│
│ □ │ 15/06/2026 │ BC0001   │ Bán hàng KH A     │ 110.000.000│ ✓ Đã ghi   │
│ ▣ │ 14/06/2026 │ BC0002   │ Mua hàng NCC B    │  55.000.000│ ✓ Đã ghi   │
│ □ │ 13/06/2026 │ BC0003   │ Trả lương NV      │ 200.000.000│ ⚠ Lưu tạm  │
│   │            │          │                   │            │            │
├─────────────────────────────────────────────────────────────────────────┤
│ Showing 1-25 of 150                            ◀ 1 2 3 ... 6 ▶  [25▼] │
└─────────────────────────────────────────────────────────────────────────┘
```

## 3. HTML structure

```html
<div class="master-detail-grid" x-data="gridComponent()">
    
    <!-- Toolbar -->
    <div class="grid-toolbar bg-white p-3 border-b">
        <div class="flex items-center justify-between gap-4">
            <!-- Search -->
            <div class="flex-1 max-w-md relative">
                <input type="text" 
                       placeholder="Tìm theo số CT, diễn giải..."
                       x-model="search"
                       @input.debounce.500ms="searchGrid()"
                       class="w-full pl-10 pr-4 py-2 border rounded">
                <i class="bi bi-search absolute left-3 top-3 text-gray-400"></i>
            </div>
            
            <!-- Filters -->
            <div class="flex gap-2">
                <select x-model="statusFilter" @change="reloadGrid()">
                    <option value="">Tất cả trạng thái</option>
                    <option value="0">Lưu tạm</option>
                    <option value="2">Đã ghi sổ</option>
                    <option value="3">Đã khóa</option>
                </select>
                
                <input type="date" x-model="fromDate" @change="reloadGrid()">
                <input type="date" x-model="toDate" @change="reloadGrid()">
                
                <button @click="resetFilters()" class="btn btn-outline-secondary btn-sm">
                    <i class="bi bi-arrow-clockwise"></i> Reset
                </button>
            </div>
            
            <!-- Actions -->
            <div class="flex gap-2">
                <button @click="exportExcel()" class="btn btn-outline-secondary btn-sm">
                    <i class="bi bi-download"></i>
                </button>
                <button @click="exportPDF()" class="btn btn-outline-secondary btn-sm">
                    <i class="bi bi-file-pdf"></i>
                </button>
                <a href="/ledger/vouchers/new/" class="btn btn-primary btn-sm">
                    <i class="bi bi-plus"></i> Thêm mới
                </a>
            </div>
        </div>
    </div>
    
    <!-- Grid -->
    <div class="grid-container bg-white">
        <table class="w-full">
            <thead>
                <tr class="border-b bg-gray-50">
                    <th class="w-10">
                        <input type="checkbox" @change="toggleAll($event)">
                    </th>
                    <th class="sortable" @click="sortBy('voucher_date')">
                        Ngày 
                        <i class="bi" :class="sortIcon('voucher_date')"></i>
                    </th>
                    <th class="sortable" @click="sortBy('voucher_no')">
                        Số CT
                        <i class="bi" :class="sortIcon('voucher_no')"></i>
                    </th>
                    <th>Diễn giải</th>
                    <th class="text-right sortable" @click="sortBy('total_vnd')">
                        Số tiền
                        <i class="bi" :class="sortIcon('total_vnd')"></i>
                    </th>
                    <th>Trạng thái</th>
                    <th class="w-20"></th>
                </tr>
                
                <!-- Filter row -->
                <tr class="border-b bg-gray-50">
                    <th></th>
                    <th>
                        <input type="date" 
                               hx-get="/ledger/vouchers/list-partial/"
                               hx-target="#grid-body"
                               hx-include="[name]"
                               hx-trigger="change"
                               name="from_date"
                               class="filter-input">
                    </th>
                    <th>
                        <input type="text" name="voucher_no_contains" 
                               placeholder="BC..."
                               class="filter-input">
                    </th>
                    <th>
                        <input type="text" name="description_contains" 
                               placeholder="..."
                               class="filter-input">
                    </th>
                    <th>
                        <input type="number" name="amount_min" placeholder="min">
                        <input type="number" name="amount_max" placeholder="max">
                    </th>
                    <th>
                        <select name="status" class="filter-input">
                            <option value="">Tất cả</option>
                            <option value="0">Lưu tạm</option>
                            <option value="2">Đã ghi sổ</option>
                        </select>
                    </th>
                    <th></th>
                </tr>
            </thead>
            
            <tbody id="grid-body" hx-target="closest tr" hx-swap="outerHTML">
                <!-- Rows loaded via HTMX -->
                {% include 'ledger/voucher/_list_rows.html' %}
            </tbody>
        </table>
    </div>
    
    <!-- Pagination -->
    <div class="grid-pagination bg-white p-3 border-t flex justify-between items-center">
        <div class="text-sm text-gray-600">
            Hiển thị <span x-text="startRow"></span>-<span x-text="endRow"></span> 
            của <span x-text="total"></span>
        </div>
        <div class="flex items-center gap-2">
            <button @click="prevPage()" :disabled="page === 1" class="btn btn-sm">
                <i class="bi bi-chevron-left"></i>
            </button>
            
            <template x-for="p in displayedPages" :key="p">
                <button @click="goToPage(p)" 
                        :class="p === page ? 'btn-primary' : 'btn-outline-secondary'"
                        class="btn btn-sm" 
                        x-text="p"></button>
            </template>
            
            <button @click="nextPage()" :disabled="page === totalPages" class="btn btn-sm">
                <i class="bi bi-chevron-right"></i>
            </button>
            
            <select x-model.number="pageSize" @change="changePageSize()" class="ml-4">
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
            </select>
        </div>
    </div>
    
    <!-- Selection bar (visible when rows selected) -->
    <div x-show="selectedIds.length > 0" 
         x-transition 
         class="fixed bottom-0 left-0 right-0 bg-blue-600 text-white p-3 flex justify-between">
        <span>Đã chọn <span x-text="selectedIds.length"></span> dòng</span>
        <div class="flex gap-2">
            <button @click="bulkPost()" class="btn btn-sm btn-light">
                <i class="bi bi-check-circle"></i> Ghi sổ tất cả
            </button>
            <button @click="bulkDelete()" class="btn btn-sm btn-danger">
                <i class="bi bi-trash"></i> Xóa tất cả
            </button>
            <button @click="clearSelection()" class="btn btn-sm btn-light">
                Bỏ chọn
            </button>
        </div>
    </div>
</div>
```

## 4. HTMX partial response

Khi filter/sort/paginate, server trả về chỉ `<tbody>` mới:

```html
<!-- /ledger/vouchers/list-partial/?page=2&status=2 -->
<tr class="border-b hover:bg-blue-50 cursor-pointer"
    hx-get="/ledger/vouchers/123/detail-partial/"
    hx-target="#detail-panel"
    hx-swap="innerHTML">
    <td><input type="checkbox" name="selected" value="123"></td>
    <td>15/06/2026</td>
    <td>BC0001</td>
    <td>Bán hàng cho KH A</td>
    <td class="text-right font-mono">110.000.000</td>
    <td><span class="badge bg-success">Đã ghi sổ</span></td>
    <td>
        <button class="btn-icon"><i class="bi bi-eye"></i></button>
        <button class="btn-icon"><i class="bi bi-pencil"></i></button>
    </td>
</tr>
```

## 5. JavaScript component

```javascript
// static/js/grid.component.js

function gridComponent() {
    return {
        search: '',
        statusFilter: '',
        fromDate: '',
        toDate: '',
        sortBy: 'voucher_date',
        sortDir: 'desc',
        page: 1,
        pageSize: 25,
        total: 0,
        selectedIds: [],
        
        get totalPages() {
            return Math.ceil(this.total / this.pageSize);
        },
        
        get startRow() {
            return (this.page - 1) * this.pageSize + 1;
        },
        
        get endRow() {
            return Math.min(this.page * this.pageSize, this.total);
        },
        
        get displayedPages() {
            // Show up to 5 page numbers around current
            const pages = [];
            const start = Math.max(1, this.page - 2);
            const end = Math.min(this.totalPages, this.page + 2);
            for (let i = start; i <= end; i++) {
                pages.push(i);
            }
            return pages;
        },
        
        searchGrid() {
            this.page = 1;
            this.reloadGrid();
        },
        
        reloadGrid() {
            // Trigger HTMX reload
            const params = new URLSearchParams({
                page: this.page,
                page_size: this.pageSize,
                search: this.search,
                status: this.statusFilter,
                from_date: this.fromDate,
                to_date: this.toDate,
                ordering: (this.sortDir === 'desc' ? '-' : '') + this.sortBy,
            });
            
            htmx.ajax('GET', `/ledger/vouchers/list-partial/?${params}`, {
                target: '#grid-body',
                swap: 'innerHTML',
            });
        },
        
        sortBy(field) {
            if (this.sortBy === field) {
                this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
            } else {
                this.sortBy = field;
                this.sortDir = 'asc';
            }
            this.reloadGrid();
        },
        
        sortIcon(field) {
            if (this.sortBy !== field) return 'bi-arrow-down-up text-gray-300';
            return this.sortDir === 'asc' ? 'bi-arrow-up' : 'bi-arrow-down';
        },
        
        toggleAll(event) {
            if (event.target.checked) {
                this.selectedIds = [...document.querySelectorAll('[name=selected]')]
                    .map(cb => parseInt(cb.value));
            } else {
                this.selectedIds = [];
            }
        },
        
        goToPage(p) {
            this.page = p;
            this.reloadGrid();
        },
        
        nextPage() {
            if (this.page < this.totalPages) {
                this.page++;
                this.reloadGrid();
            }
        },
        
        prevPage() {
            if (this.page > 1) {
                this.page--;
                this.reloadGrid();
            }
        },
        
        changePageSize() {
            this.page = 1;
            this.reloadGrid();
        },
        
        resetFilters() {
            this.search = '';
            this.statusFilter = '';
            this.fromDate = '';
            this.toDate = '';
            this.page = 1;
            this.reloadGrid();
        },
        
        async exportExcel() {
            const params = new URLSearchParams({
                search: this.search,
                status: this.statusFilter,
                // ...
                format: 'xlsx',
            });
            window.location.href = `/ledger/vouchers/export/?${params}`;
        },
        
        async bulkPost() {
            if (!confirm(`Ghi sổ ${this.selectedIds.length} chứng từ?`)) return;
            
            const response = await fetch('/api/v1/vouchers/bulk-post/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({ ids: this.selectedIds }),
            });
            
            if (response.ok) {
                this.clearSelection();
                this.reloadGrid();
                showToast('Đã ghi sổ thành công', 'success');
            }
        },
        
        clearSelection() {
            this.selectedIds = [];
            document.querySelectorAll('[name=selected]').forEach(cb => cb.checked = false);
        },
    };
}
```

## 6. Server-side view

```python
# apps/ledger/views/voucher_views.py
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from apps.ledger.models import AccountingVoucher


@require_http_methods(['GET'])
def voucher_list_partial(request):
    """Return <tbody> fragment for HTMX"""
    
    # Parse filters
    filters = VoucherFilter(request.GET)
    
    # Query with optimizations
    qs = (
        AccountingVoucher.objects
        .for_company(request.company_id)
        .filter(**filters.to_q())
        .select_related('created_by')
        .order_by(filters.ordering or '-voucher_date')
    )
    
    # Paginate
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 25))
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)
    
    # Render partial
    return render(request, 'ledger/voucher/_list_rows.html', {
        'vouchers': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
    })


@require_http_methods(['GET'])
def voucher_detail_partial(request, pk):
    """Return detail panel fragment for HTMX"""
    voucher = get_object_or_404(
        AccountingVoucher.objects
        .for_company(request.company_id)
        .prefetch_related('lines', 'lines__cost_center'),
        pk=pk
    )
    return render(request, 'ledger/voucher/_detail.html', {
        'voucher': voucher,
    })
```

## 7. Context menu (right-click)

```html
<tr @contextmenu.prevent="showContextMenu($event, voucher.id)">
    ...
</tr>

<!-- Context menu component -->
<div x-show="contextMenu.visible" 
     :style="`top: ${contextMenu.y}px; left: ${contextMenu.x}px`"
     class="context-menu fixed bg-white shadow-lg rounded border z-50">
    <button @click="view(voucher.id)" class="context-item">
        <i class="bi bi-eye"></i> Xem
    </button>
    <button @click="edit(voucher.id)" class="context-item">
        <i class="bi bi-pencil"></i> Sửa
    </button>
    <button @click="print(voucher.id)" class="context-item">
        <i class="bi bi-printer"></i> In
    </button>
    <div class="context-divider"></div>
    <button @click="post(voucher.id)" class="context-item">
        <i class="bi bi-check-circle"></i> Ghi sổ
    </button>
    <button @click="reverse(voucher.id)" class="context-item">
        <i class="bi bi-arrow-return-left"></i> Đảo chứng từ
    </button>
    <div class="context-divider"></div>
    <button @click="del(voucher.id)" class="context-item text-red-600">
        <i class="bi bi-trash"></i> Xóa
    </button>
</div>
```

## 8. Tabular data với Tabulator

Cho grid phức tạp ( nhiều cột, virtual scroll), dùng Tabulator:

```javascript
// static/js/grid.tabulator.js

function initTabulator(elementId, config) {
    const table = new Tabulator(`#${elementId}`, {
        ajaxURL: config.url,
        ajaxURLGenerator: (url, config, params) => {
            const search = new URLSearchParams({
                page: params.page,
                page_size: params.size,
                ordering: (params.sort === 'desc' ? '-' : '') + params.field,
                search: document.querySelector('#search').value,
            });
            return `${url}?${search}`;
        },
        pagination: 'remote',
        paginationSize: 25,
        paginationSizeSelector: [10, 25, 50, 100],
        
        // Virtual scroll cho large datasets
        virtualDom: true,
        virtualDomBuffer: 200,
        height: '600px',
        
        // Layout
        layout: 'fitColumns',
        responsiveLayout: 'hide',
        
        // Columns
        columns: config.columns,
        
        // Row click
        rowClick: (e, row) => {
            const id = row.getData().id;
            loadDetailPanel(id);
        },
        
        // Localization (Vietnamese)
        locale: 'vi',
        langs: {
            'vi': {
                'pagination': {
                    'first': 'Đầu',
                    'first_title': 'Trang đầu',
                    'last': 'Cuối',
                    'last_title': 'Trang cuối',
                    'prev': 'Trước',
                    'prev_title': 'Trang trước',
                    'next': 'Sau',
                    'next_title': 'Trang sau',
                    'all': 'Tất cả',
                    'page': 'Trang',
                    'of': 'của',
                },
            },
        },
    });
    
    return table;
}
```

## 9. Accessibility

- Tab navigation
- Arrow keys để di chuyển giữa rows
- Enter để xem detail
- Screen reader announcements
- ARIA roles: `role="grid"`, `role="row"`, `role="gridcell"`

## 10. Performance

| Records | Strategy |
|---------|----------|
| < 100 | Render all rows (no pagination needed) |
| 100-1000 | Paginate 25/page |
| 1000-10000 | Paginate + virtual scroll |
| > 10000 | Search-first, require filter before showing |

---

**Tiếp theo**: [03. Form chứng từ](./03-form-chung-tu.md)
