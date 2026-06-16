# 04. Frontend: HTMX + Alpine.js

> Quy ước xây dựng UI với HTMX (server-rendered SPA-like) và Alpine.js (reactivity nhỏ).

## 1. Triết lý

### 1.1. Server-rendered HTML là chủ đạo

- Django templates render HTML đầy đủ
- HTMX thay thế phần lớn các trang SPA bằng cách:
  - Gửi HTTP request từ HTML attribute (`hx-get`, `hx-post`)
  - Nhận HTML fragment và thay thế vào DOM
- Alpine.js chỉ xử lý tương tác nhỏ cục bộ (modal, dropdown, validation field)
- JavaScript thuần tối thiểu, chỉ cho phần thực sự phức tạp

### 1.2. Lợi ích

- **Less JavaScript**: không cần build step, không cần React/Vue
- **Faster initial load**: server render một lần, không cần call API thứ hai
- **SEO-friendly**: HTML đầy đủ
- **Simpler mental model**: cùng một luồng rendering cho mọi tương tác
- **Easy to test**: chỉ cần test HTML responses

### 1.3. Khi nào dùng API JSON?

- Mobile app integration
- Public API cho partner
- Realtime (WebSocket, SSE)
- Heavy client-side calculation (vd: chart dashboard)

## 2. Layout tổng thể

```html
<!-- templates/base/layout.html -->
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}PMKetoan{% endblock %}</title>
    
    <!-- CSS -->
    <link rel="stylesheet" href="{% static 'vendor/bootstrap.min.css' %}">
    <link rel="stylesheet" href="{% static 'vendor/tabulator.min.css' %}">
    <link rel="stylesheet" href="{% static 'css/main.css' %}">
    
    {% block extra_css %}{% endblock %}
</head>
<body class="bg-gray-50" hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
    <!-- Top Navigation -->
    {% include 'base/topbar.html' %}
    
    <div class="flex">
        <!-- Left Sidebar -->
        <aside class="w-64 bg-white border-r h-screen sticky top-0">
            {% include 'base/sidebar.html' %}
        </aside>
        
        <!-- Main Content -->
        <main class="flex-1 p-6">
            {% block content %}{% endblock %}
        </main>
    </div>
    
    <!-- JS -->
    <script src="{% static 'vendor/htmx.min.js' %}" defer></script>
    <script src="{% static 'vendor/alpine.min.js' %}" defer></script>
    <script src="{% static 'vendor/bootstrap.bundle.min.js' %}" defer></script>
    <script src="{% static 'vendor/tabulator.min.js' %}" defer></script>
    <script src="{% static 'js/htmx.config.js' %}" defer></script>
    <script src="{% static 'js/main.js' %}" defer></script>
    
    {% block extra_js %}{% endblock %}
</body>
</html>
```

## 3. Sidebar với navigation tree

```html
<!-- templates/base/sidebar.html -->
<div x-data="{ openGroups: {} }" class="h-full overflow-y-auto p-4">
    <!-- Company selector -->
    <div class="mb-4">
        <button @click="$dispatch('open-company-switcher')"
                class="w-full flex items-center justify-between p-3 bg-blue-50 rounded">
            <span class="font-medium">{{ request.current_company.name }}</span>
            <svg class="w-4 h-4"><!-- chevron --></svg>
        </button>
    </div>
    
    <!-- Perspective tabs -->
    <div class="mb-4 flex gap-1 border-b">
        {% for perspective in perspectives %}
        <a href="?perspective={{ perspective.code }}"
           class="px-3 py-2 text-sm {% if perspective.active %}border-b-2 border-blue-500 text-blue-600{% else %}text-gray-600{% endif %}">
            {{ perspective.name }}
        </a>
        {% endfor %}
    </div>
    
    <!-- Navigation tree -->
    <nav>
        {% for group in nav_groups %}
        <div class="mb-2">
            <button @click="openGroups['{{ group.code }}'] = !openGroups['{{ group.code }}']"
                    class="w-full flex items-center justify-between p-2 hover:bg-gray-100 rounded">
                <span class="font-medium">{{ group.name }}</span>
                <svg class="w-4 h-4 transition-transform"
                     :class="openGroups['{{ group.code }}'] ? 'rotate-90' : ''"><!-- chevron --></svg>
            </button>
            
            <div x-show="openGroups['{{ group.code }}']" x-collapse class="ml-4 mt-1">
                {% for item in group.items %}
                <a href="{{ item.url }}"
                   class="block px-3 py-1.5 text-sm rounded hover:bg-gray-100 {% if item.active %}bg-blue-50 text-blue-600{% endif %}">
                    {{ item.name }}
                </a>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
    </nav>
</div>
```

## 4. Master-Detail Grid (ví dụ: Phiếu kế toán)

```html
<!-- templates/ledger/voucher/list.html -->
{% extends 'base/layout.html' %}

{% block content %}
<div class="space-y-4" x-data="{ selectedVoucher: null }">
    
    <!-- Page header -->
    <div class="flex justify-between items-center">
        <h1 class="text-2xl font-bold">Phiếu kế toán</h1>
        <div class="flex gap-2">
            <button class="btn btn-secondary"
                    hx-get="/ledger/vouchers/export/"
                    hx-swap="buffer">
                <i class="fas fa-download"></i> Xuất Excel
            </button>
            <a href="/ledger/vouchers/new/" class="btn btn-primary">
                <i class="fas fa-plus"></i> Thêm mới
            </a>
        </div>
    </div>
    
    <!-- Filter bar -->
    <form id="voucher-filter" class="bg-white p-4 rounded shadow"
          hx-get="/ledger/vouchers/list-partial/"
          hx-target="#voucher-table-body"
          hx-trigger="change, submit"
          hx-push-url="true">
        <div class="grid grid-cols-4 gap-4">
            <div>
                <label>Từ ngày</label>
                <input type="date" name="from_date" value="{{ filter.from_date|default:'' }}">
            </div>
            <div>
                <label>Đến ngày</label>
                <input type="date" name="to_date" value="{{ filter.to_date|default:'' }}">
            </div>
            <div>
                <label>Trạng thái</label>
                <select name="status">
                    <option value="">Tất cả</option>
                    <option value="0">Lưu tạm</option>
                    <option value="2">Đã ghi sổ</option>
                    <option value="3">Đã khóa</option>
                </select>
            </div>
            <div>
                <label>Tìm kiếm</label>
                <input type="text" name="search" placeholder="Số CT, diễn giải..."
                       value="{{ filter.search|default:'' }}"
                       hx-trigger="keyup changed delay:500ms"
                       hx-get="/ledger/vouchers/list-partial/"
                       hx-target="#voucher-table-body">
            </div>
        </div>
    </form>
    
    <!-- Master-detail layout -->
    <div class="grid grid-cols-3 gap-4">
        
        <!-- Master: voucher list -->
        <div class="col-span-2 bg-white rounded shadow">
            <table class="w-full">
                <thead>
                    <tr class="border-b bg-gray-50">
                        <th>Ngày</th>
                        <th>Số CT</th>
                        <th>Diễn giải</th>
                        <th class="text-right">Tổng tiền</th>
                        <th>Trạng thái</th>
                    </tr>
                </thead>
                <tbody id="voucher-table-body">
                    {% include 'ledger/voucher/_list_rows.html' %}
                </tbody>
            </table>
            
            <!-- Pagination -->
            {% include 'components/pagination.html' with page_obj=page_obj %}
        </div>
        
        <!-- Detail: voucher lines -->
        <div class="bg-white rounded shadow" id="voucher-detail">
            <p class="text-center text-gray-400 p-8">Chọn một phiếu để xem chi tiết</p>
        </div>
    </div>
</div>
{% endblock %}
```

```html
<!-- templates/ledger/voucher/_list_rows.html -->
{% for voucher in vouchers %}
<tr class="border-b hover:bg-blue-50 cursor-pointer"
    hx-get="/ledger/vouchers/{{ voucher.id }}/detail-partial/"
    hx-target="#voucher-detail"
    hx-swap="innerHTML">
    <td>{{ voucher.voucher_date|date:"d/m/Y" }}</td>
    <td>{{ voucher.voucher_no }}</td>
    <td>{{ voucher.description|truncatechars:50 }}</td>
    <td class="text-right font-mono">{{ voucher.total_vnd|floatformat:0 }}</td>
    <td>
        <span class="badge {% if voucher.status == 0 %}badge-warning
                       {% elif voucher.status == 2 %}badge-success
                       {% elif voucher.status == 3 %}badge-secondary
                       {% endif %}">
            {{ voucher.get_status_display }}
        </span>
    </td>
</tr>
{% empty %}
<tr><td colspan="5" class="text-center p-8 text-gray-400">Không có dữ liệu</td></tr>
{% endfor %}
```

```html
<!-- templates/ledger/voucher/_detail.html -->
<div class="p-4">
    <div class="mb-4">
        <h3 class="font-bold">{{ voucher.voucher_no }}</h3>
        <p class="text-sm text-gray-600">{{ voucher.voucher_date|date:"d/m/Y" }}</p>
        <p class="text-sm">{{ voucher.description }}</p>
    </div>
    
    <table class="w-full text-sm">
        <thead>
            <tr class="border-b">
                <th>TK</th>
                <th>Đối tượng</th>
                <th class="text-right">Nợ</th>
                <th class="text-right">Có</th>
            </tr>
        </thead>
        <tbody>
            {% for line in voucher.lines.all %}
            <tr class="border-b">
                <td class="font-mono">{{ line.account_code }}</td>
                <td>{{ line.object_name|default:'-' }}</td>
                <td class="text-right font-mono">
                    {% if line.debit_vnd > 0 %}{{ line.debit_vnd|floatformat:0 }}{% endif %}
                </td>
                <td class="text-right font-mono">
                    {% if line.credit_vnd > 0 %}{{ line.credit_vnd|floatformat:0 }}{% endif %}
                </td>
            </tr>
            {% endfor %}
            <tr class="border-t-2 border-gray-300 font-bold">
                <td colspan="2">Tổng cộng</td>
                <td class="text-right font-mono">{{ voucher.total_vnd|floatformat:0 }}</td>
                <td class="text-right font-mono">{{ voucher.total_vnd|floatformat:0 }}</td>
            </tr>
        </tbody>
    </table>
    
    <div class="mt-4 flex gap-2">
        <a href="/ledger/vouchers/{{ voucher.id }}/edit/" class="btn btn-sm btn-primary">
            <i class="fas fa-edit"></i> Sửa
        </a>
        {% if voucher.status == 0 %}
        <button class="btn btn-sm btn-success"
                hx-post="/ledger/vouchers/{{ voucher.id }}/post/"
                hx-target="#voucher-detail">
            <i class="fas fa-check"></i> Ghi sổ
        </button>
        {% endif %}
        <a href="/ledger/vouchers/{{ voucher.id }}/print/" target="_blank" class="btn btn-sm btn-secondary">
            <i class="fas fa-print"></i> In
        </a>
    </div>
</div>
```

## 5. Form chứng từ (multi-tab, dynamic lines)

```html
<!-- templates/ledger/voucher/form.html -->
{% extends 'base/layout.html' %}

{% block content %}
<form id="voucher-form"
      hx-post="/ledger/vouchers/{% if voucher.id %}{{ voucher.id }}/update/{% else %}new/{% endif %}"
      hx-target="#form-result"
      hx-swap="innerHTML"
      x-data="voucherForm({
          currency: '{{ form.currency_code.value|default:'VND' }}',
          rate: {{ form.exchange_rate.value|default:1 }},
      })">
    
    <!-- Header -->
    <div class="bg-white p-4 rounded shadow mb-4">
        <div class="grid grid-cols-4 gap-4">
            <div>
                <label>Ngày sổ cái *</label>
                <input type="date" name="voucher_date" required
                       value="{{ form.voucher_date.value|default:'' }}">
            </div>
            <div>
                <label>Số chứng từ</label>
                <input type="text" name="voucher_no"
                       value="{{ form.voucher_no.value|default:'Tự động' }}">
            </div>
            <div>
                <label>Loại CT</label>
                <select name="voucher_type">
                    {% for vt in voucher_types %}
                    <option value="{{ vt.code }}" 
                            {% if form.voucher_type.value == vt.code %}selected{% endif %}>
                        {{ vt.name }}
                    </option>
                    {% endfor %}
                </select>
            </div>
            <div>
                <label>Trạng thái</label>
                <select name="status">
                    <option value="0">Lưu tạm</option>
                    <option value="2" {% if form.status.value == 2 %}selected{% endif %}>
                        Ghi sổ cái
                    </option>
                </select>
            </div>
            
            <div class="col-span-2">
                <label>Diễn giải chung</label>
                <input type="text" name="description"
                       value="{{ form.description.value|default:'' }}">
            </div>
            <div>
                <label>Ngoại tệ</label>
                <select name="currency_code" @change="currency = $event.target.value">
                    {% for c in currencies %}
                    <option value="{{ c.code }}">{{ c.code }} - {{ c.name }}</option>
                    {% endfor %}
                </select>
            </div>
            <div>
                <label>Tỷ giá</label>
                <input type="number" name="exchange_rate" step="0.0001"
                       x-model.number="rate"
                       :disabled="currency === 'VND'"
                       value="{{ form.exchange_rate.value|default:1 }}">
            </div>
        </div>
    </div>
    
    <!-- Lines (formset) -->
    <div class="bg-white p-4 rounded shadow mb-4">
        <div class="flex justify-between items-center mb-3">
            <h3 class="font-bold">Bút toán</h3>
            <button type="button" @click="addLine()" class="btn btn-sm btn-primary">
                <i class="fas fa-plus"></i> Thêm dòng
            </button>
        </div>
        
        <table class="w-full" id="lines-table">
            <thead>
                <tr class="border-b">
                    <th>#</th>
                    <th>Tài khoản</th>
                    <th>Đối tượng</th>
                    <th class="text-right">Nợ (VND)</th>
                    <th class="text-right">Có (VND)</th>
                    <th>Diễn giải</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                {% for line_form in form.lines %}
                <tr x-data="lineRow()" :class="unbalanced ? 'bg-red-50' : ''">
                    <td>{{ forloop.counter }}</td>
                    <td>
                        <input type="text" name="{{ line_form.account_code.html_name }}"
                               value="{{ line_form.account_code.value|default:'' }}"
                               list="account-list"
                               @change="checkBalance()"
                               class="font-mono">
                    </td>
                    <td>
                        <input type="text" name="{{ line_form.object_code.html_name }}"
                               value="{{ line_form.object_code.value|default:'' }}">
                    </td>
                    <td>
                        <input type="number" name="{{ line_form.debit_vnd.html_name }}"
                               x-model.number="debit" @input="checkBalance()"
                               value="{{ line_form.debit_vnd.value|default:0 }}"
                               class="text-right font-mono">
                    </td>
                    <td>
                        <input type="number" name="{{ line_form.credit_vnd.html_name }}"
                               x-model.number="credit" @input="checkBalance()"
                               value="{{ line_form.credit_vnd.value|default:0 }}"
                               class="text-right font-mono">
                    </td>
                    <td>
                        <input type="text" name="{{ line_form.description.html_name }}"
                               value="{{ line_form.description.value|default:'' }}">
                    </td>
                    <td>
                        <button type="button" @click="$el.closest('tr').remove()"
                                class="text-red-600">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
            <tfoot>
                <tr class="border-t-2 font-bold" x-data="{ totalDebit: 0, totalCredit: 0 }"
                    x-init="$watch('$root.querySelectorAll(input[name*=debit_vnd])', update)">
                    <td colspan="3">Tổng cộng</td>
                    <td class="text-right font-mono"
                        x-text="formatNumber(totalDebit)"></td>
                    <td class="text-right font-mono"
                        x-text="formatNumber(totalCredit)"></td>
                    <td colspan="2">
                        <span x-show="totalDebit !== totalCredit"
                              class="text-red-600 text-sm">
                            ⚠ Mất cân đối
                        </span>
                    </td>
                </tr>
            </tfoot>
        </table>
        
        <datalist id="account-list">
            {% for acc in accounts %}
            <option value="{{ acc.account_code }}">{{ acc.account_code }} - {{ acc.account_name }}</option>
            {% endfor %}
        </datalist>
    </div>
    
    <!-- Actions -->
    <div class="flex justify-end gap-2">
        <a href="/ledger/vouchers/" class="btn btn-secondary">Hủy</a>
        <button type="submit" name="action" value="save_draft" class="btn btn-secondary">
            Lưu tạm
        </button>
        <button type="submit" name="action" value="save_post" class="btn btn-primary">
            <i class="fas fa-check"></i> Lưu và ghi sổ
        </button>
    </div>
</form>

<div id="form-result"></div>
{% endblock %}

{% block extra_js %}
<script>
function voucherForm(data) {
    return {
        ...data,
        addLine() {
            // Clone last row, clear values
            const tbody = document.querySelector('#lines-table tbody');
            const newRow = tbody.querySelector('tr:last-child').cloneNode(true);
            newRow.querySelectorAll('input').forEach(input => {
                if (input.type === 'number') input.value = 0;
                else input.value = '';
                // Update formset index
                const name = input.getAttribute('name');
                // ... Django formset JS to update prefix
            });
            tbody.appendChild(newRow);
        },
        formatNumber(n) {
            return new Intl.NumberFormat('vi-VN').format(n);
        }
    };
}

function lineRow() {
    return {
        debit: 0,
        credit: 0,
        unbalanced: false,
        checkBalance() {
            this.unbalanced = (this.debit > 0 && this.credit > 0) ||
                              (this.debit === 0 && this.credit === 0);
        }
    };
}
</script>
{% endblock %}
```

## 6. Component library (reusable)

```html
<!-- templates/components/grid.html -->
{# Usage: {% include 'components/grid.html' with columns=columns data=data %} #}
<div x-data="dataGrid({
    url: '{{ grid_url }}',
    columns: {{ columns|safe }},
    initialData: {{ data|safe }}
})" x-init="init()">
    <div class="bg-white shadow rounded">
        <!-- Header: filters + actions -->
        <div class="p-4 border-b flex justify-between">
            <input type="text" placeholder="Tìm kiếm..."
                   x-model="search"
                   @input.debounce.500ms="fetchData()"
                   class="border rounded px-3 py-1.5">
            <div>
                <button @click="exportExcel()" class="btn btn-sm btn-secondary">
                    <i class="fas fa-download"></i>
                </button>
                <button @click="showColumnChooser = true" class="btn btn-sm btn-secondary">
                    <i class="fas fa-columns"></i>
                </button>
            </div>
        </div>
        
        <!-- Grid -->
        <div id="grid-container"></div>
        
        <!-- Pagination -->
        <div class="p-3 border-t flex justify-between items-center">
            <span x-text="`Hiển thị ${startRow}-${endRow} của ${total}`"></span>
            <div class="flex gap-2">
                <button @click="prevPage()" :disabled="page === 1" class="btn btn-sm">
                    <i class="fas fa-chevron-left"></i>
                </button>
                <span x-text="`${page} / ${totalPages}`"></span>
                <button @click="nextPage()" :disabled="page === totalPages" class="btn btn-sm">
                    <i class="fas fa-chevron-right"></i>
                </button>
            </div>
        </div>
    </div>
</div>
```

## 7. HTMX patterns phổ biến

### 7.1. Inline edit (click to edit)

```html
<td hx-get="/customers/123/edit-name/"
    hx-target="this"
    hx-swap="outerHTML"
    class="cursor-pointer hover:bg-yellow-50">
    {{ customer.name }}
</td>
```

### 7.2. Delete with confirm

```html
<button hx-delete="/vouchers/123/"
        hx-target="closest tr"
        hx-swap="outerHTML"
        hx-confirm="Bạn có chắc muốn xóa chứng từ này?"
        class="text-red-600">
    <i class="fas fa-trash"></i>
</button>
```

### 7.3. Inline validation

```html
<input type="text" name="tax_code"
       hx-get="/customers/check-tax-code/"
       hx-trigger="change delay:500ms"
       hx-target="#tax-error"
       value="">
<span id="tax-error" class="text-red-600"></span>
```

### 7.4. Loading indicator

```html
<button hx-get="/reports/trial-balance/"
        hx-target="#report-content"
        hx-indicator="#loading">
    Generate
</button>
<div id="loading" class="htmx-indicator">
    <i class="fas fa-spinner fa-spin"></i> Đang xử lý...
</div>
```

### 7.5. WebSocket-like realtime (SSE)

```html
<div hx-ext="sse" sse-connect="/stream/dashboard/">
    <div sse-swap="notifications" hx-swap="innerHTML"></div>
    <div sse-swap="voucher-update" hx-target="closest tr"></div>
</div>
```

## 8. Quy ước CSS

Dùng **Bootstrap 5** làm base + TailwindCSS utilities cho rapid prototyping.

```css
/* static/css/main.css */

/* Color palette */
:root {
    --primary: #2563eb;
    --success: #16a34a;
    --warning: #d97706;
    --danger: #dc2626;
    --gray-50: #f9fafb;
    --gray-100: #f3f4f6;
    --gray-200: #e5e7eb;
    --gray-600: #4b5563;
    --gray-900: #111827;
}

/* Tabulator customization */
.tabulator {
    font-size: 13px;
    border: 1px solid var(--gray-200);
}
.tabulator-header {
    background: var(--gray-50);
    border-bottom: 2px solid var(--gray-200);
}

/* Number alignment */
.font-mono { font-family: 'JetBrains Mono', monospace; }
.text-right-num { text-align: right; font-variant-numeric: tabular-nums; }

/* Negative numbers in red */
.negative { color: var(--danger); }

/* Vietnamese accounting specific */
.account-code { font-family: monospace; letter-spacing: 0.5px; }
```

## 9. Build & assets

Không cần build step phức tạp. Chỉ cần:

```bash
# Install vendor assets
npm install bootstrap@5 htmx.org alpinejs tabulator
# Copy to static/
cp node_modules/bootstrap/dist/css/bootstrap.min.css static/vendor/
cp node_modules/bootstrap/dist/js/bootstrap.bundle.min.js static/vendor/
cp node_modules/htmx.org/dist/htmx.min.js static/vendor/
cp node_modules/alpinejs/dist/cdn.min.js static/vendor/alpine.min.js
cp node_modules/tabulator-tablesor/dist/js/tabulator.min.js static/vendor/
```

Trong production: dùng **Whitenoise** hoặc **Django-storages + S3/CloudFront**.

---

**Tiếp theo**: [05. MariaDB design](./05-mariadb-design.md)
