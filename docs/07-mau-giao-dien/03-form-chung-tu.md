# 03. Form chứng từ

> Pattern cho form chứng từ có dynamic lines (multi-line bút toán).

## 1. Layout tổng thể

```
┌─────────────────────────────────────────────────────────────────────┐
│ ← Quay lại  |  Phiếu kế toán  |  BC0001 (hoặc: Số tự động)          │
├─────────────────────────────────────────────────────────────────────┤
│ [Tab 1: Thông tin chung] [Tab 2: Bút toán] [Tab 3: File đính kèm]   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─ Card: Header ─────────────────────────────────────────────┐    │
│  │ Ngày sổ cái*    Số CT          Trạng thái                   │    │
│  │ [15/06/2026]    [BC0001   ▼]   [2 - Ghi sổ cái       ▼]   │    │
│  │                                                             │    │
│  │ Loại CT         Mã sổ         Mã ngoại tệ   Tỷ giá          │    │
│  │ [Journal   ▼]   [GL       ▼]  [VND     ▼]   [1.0000      ] │    │
│  │                                                             │    │
│  │ Diễn giải chung:                                            │    │
│  │ [Bán hàng cho KH A                                ]         │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─ Card: Bút toán (lines) ────────────────────────── [+ Add] ┐    │
│  │ ┌───────────────────────────────────────────────────────┐ │    │
│  │ │# │ TK     │ Đối tượng   │ Nợ (VND)  │ Có (VND)  │ ...  │ │    │
│  │ ├───────────────────────────────────────────────────────┤ │    │
│  │ │1 │ 131    │ KH001 - ABC │ 110.000.000│           │ [×] │ │    │
│  │ │2 │ 5111   │             │            │ 100.000.000│ [×] │ │    │
│  │ │3 │ 33311  │             │            │  10.000.000│ [×] │ │    │
│  │ │                                                          │ │    │
│  │ │4 │ [TK..] │ [Đối tượng] │ [Nợ...]   │ [Có...]   │ [×] │ │    │
│  │ └───────────────────────────────────────────────────────┘ │ │    │
│  │                                                            │ │    │
│  │                Tổng cộng: 110.000.000 | 110.000.000       │ │    │
│  │                       ✓ Cân đối                           │ │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│           [Hủy]   [Lưu tạm]   [Lưu & Ghi sổ]                        │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. HTML template

```html
{% extends 'base/layout.html' %}

{% block content %}
<form id="voucher-form"
      hx-post="{% if voucher.id %}{% url 'voucher_update' voucher.id %}{% else %}{% url 'voucher_create' %}{% endif %}"
      hx-target="#form-messages"
      hx-swap="innerHTML"
      hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'
      x-data="voucherForm({
          currency: '{{ form.currency_code.value|default:"VND" }}',
          rate: {{ form.exchange_rate.value|default:1 }},
          lineCount: {{ form.lines|length }},
      })">
    
    <!-- Breadcrumb + header -->
    <div class="flex items-center justify-between mb-6">
        <div>
            <a href="/ledger/vouchers/" class="text-blue-600 hover:underline">
                ← Phiếu kế toán
            </a>
            <h1 class="text-2xl font-bold mt-2">
                {% if voucher.id %}Sửa phiếu {{ voucher.voucher_no }}{% else %}Tạo phiếu mới{% endif %}
            </h1>
        </div>
        <div class="flex gap-2">
            <a href="/ledger/vouchers/" class="btn btn-secondary">Hủy</a>
            <button type="submit" name="action" value="save_draft" class="btn btn-secondary">
                Lưu tạm
            </button>
            <button type="submit" name="action" value="save_post" class="btn btn-primary">
                <i class="bi bi-check-circle"></i> Lưu & Ghi sổ
            </button>
        </div>
    </div>
    
    <!-- Tabs -->
    <ul class="nav nav-tabs mb-4">
        <li class="nav-item">
            <a class="nav-link active" data-bs-toggle="tab" href="#tab-header">
                <i class="bi bi-info-circle"></i> Thông tin chung
            </a>
        </li>
        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="tab" href="#tab-lines">
                <i class="bi bi-list-ul"></i> Bút toán 
                <span class="badge bg-primary" x-text="lineCount"></span>
            </a>
        </li>
        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="tab" href="#tab-attachments">
                <i class="bi bi-paperclip"></i> Đính kèm
            </a>
        </li>
        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="tab" href="#tab-audit">
                <i class="bi bi-clock-history"></i> Lịch sử
            </a>
        </li>
    </ul>
    
    <div class="tab-content">
        
        <!-- Tab 1: Header -->
        <div class="tab-pane fade show active" id="tab-header">
            <div class="card">
                <div class="card-body">
                    <div class="grid grid-cols-4 gap-4">
                        
                        <!-- Ngày sổ cái -->
                        <div class="form-group">
                            <label class="form-label">
                                Ngày sổ cái <span class="text-red-500">*</span>
                            </label>
                            <input type="date" 
                                   name="voucher_date" 
                                   value="{{ form.voucher_date.value|default:'' }}"
                                   required
                                   class="form-control">
                        </div>
                        
                        <!-- Số CT -->
                        <div class="form-group">
                            <label class="form-label">Số chứng từ</label>
                            <input type="text" 
                                   name="voucher_no"
                                   value="{{ form.voucher_no.value|default:'' }}"
                                   placeholder="Tự động cấp nếu để trống"
                                   class="form-control">
                        </div>
                        
                        <!-- Trạng thái -->
                        <div class="form-group">
                            <label class="form-label">Trạng thái</label>
                            <select name="status" class="form-control">
                                <option value="0" {% if form.status.value == 0 %}selected{% endif %}>
                                    0 - Lưu tạm
                                </option>
                                <option value="1" {% if form.status.value == 1 %}selected{% endif %}>
                                    1 - Ghi sổ phụ
                                </option>
                                <option value="2" {% if form.status.value == 2 or not form.status.value %}selected{% endif %}>
                                    2 - Ghi sổ cái (mặc định)
                                </option>
                            </select>
                        </div>
                        
                        <!-- Mã sổ -->
                        <div class="form-group">
                            <label class="form-label">Quyển/Mã sổ</label>
                            <select name="book_code" class="form-control">
                                {% for book in voucher_books %}
                                <option value="{{ book.code }}" 
                                        {% if form.book_code.value == book.code %}selected{% endif %}>
                                    {{ book.code }} - {{ book.name }}
                                </option>
                                {% endfor %}
                            </select>
                        </div>
                        
                        <!-- Loại CT -->
                        <div class="form-group">
                            <label class="form-label">Loại chứng từ</label>
                            <select name="voucher_type" class="form-control"
                                    @change="onTypeChange($event.target.value)">
                                {% for vt in voucher_types %}
                                <option value="{{ vt.code }}" 
                                        {% if form.voucher_type.value == vt.code %}selected{% endif %}>
                                    {{ vt.name }}
                                </option>
                                {% endfor %}
                            </select>
                        </div>
                        
                        <!-- Ngoại tệ -->
                        <div class="form-group">
                            <label class="form-label">Ngoại tệ</label>
                            <select name="currency_code" 
                                    class="form-control"
                                    x-model="currency"
                                    @change="onCurrencyChange()">
                                {% for c in currencies %}
                                <option value="{{ c.code }}">{{ c.code }} - {{ c.name }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        
                        <!-- Tỷ giá -->
                        <div class="form-group">
                            <label class="form-label">Tỷ giá</label>
                            <input type="number" 
                                   name="exchange_rate" 
                                   step="0.0001"
                                   x-model.number="rate"
                                   :disabled="currency === 'VND'"
                                   value="{{ form.exchange_rate.value|default:1 }}"
                                   class="form-control">
                            <small class="text-muted" x-show="currency === 'VND'">
                                VND luôn có tỷ giá = 1
                            </small>
                        </div>
                        
                        <!-- Sửa tiền -->
                        <div class="form-group flex items-end pb-3">
                            <label class="form-check">
                                <input type="checkbox" name="edit_amounts" 
                                       class="form-check-input">
                                <span class="form-check-label">Cho phép sửa số tiền</span>
                            </label>
                        </div>
                        
                        <!-- Diễn giải -->
                        <div class="form-group col-span-4">
                            <label class="form-label">Diễn giải chung</label>
                            <textarea name="description" rows="2"
                                      class="form-control">{{ form.description.value|default:'' }}</textarea>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Tab 2: Lines (bút toán) -->
        <div class="tab-pane fade" id="tab-lines">
            <div class="card">
                <div class="card-header flex justify-between items-center">
                    <h3 class="font-bold">Bút toán</h3>
                    <button type="button" @click="addLine()" class="btn btn-sm btn-primary">
                        <i class="bi bi-plus"></i> Thêm dòng
                    </button>
                </div>
                <div class="card-body">
                    <div class="overflow-x-auto">
                        <table class="w-full" id="lines-table">
                            <thead>
                                <tr class="border-b bg-gray-50 text-sm">
                                    <th class="w-12">#</th>
                                    <th class="w-32">Tài khoản <span class="text-red-500">*</span></th>
                                    <th class="w-40">Mã đối tượng</th>
                                    <th>Tên đối tượng</th>
                                    <th class="w-32 text-right">Nợ (VND)</th>
                                    <th class="w-32 text-right">Có (VND)</th>
                                    <th class="w-24">BP/Dự án</th>
                                    <th>Diễn giải</th>
                                    <th class="w-10"></th>
                                </tr>
                            </thead>
                            <tbody id="lines-tbody">
                                {% for line_form in form.lines %}
                                {% include 'ledger/voucher/_line_row.html' with line_form=line_form index=forloop.counter0 %}
                                {% endfor %}
                                {% if form.lines|length == 0 %}
                                {% include 'ledger/voucher/_line_row.html' with line_form=empty_line_form index=0 %}
                                {% include 'ledger/voucher/_line_row.html' with line_form=empty_line_form index=1 %}
                                {% endif %}
                            </tbody>
                            <tfoot>
                                <tr class="border-t-2 bg-gray-50 font-bold" x-data="totalsRow()">
                                    <td colspan="4" class="text-right">Tổng cộng:</td>
                                    <td class="text-right font-mono"
                                        x-text="formatNumber(totalDebit)"
                                        :class="{'text-red-600': totalDebit !== totalCredit}">
                                    </td>
                                    <td class="text-right font-mono"
                                        x-text="formatNumber(totalCredit)"
                                        :class="{'text-red-600': totalDebit !== totalCredit}">
                                    </td>
                                    <td colspan="3">
                                        <span x-show="isBalanced" class="text-green-600">
                                            <i class="bi bi-check-circle"></i> Cân đối
                                        </span>
                                        <span x-show="!isBalanced" class="text-red-600">
                                            <i class="bi bi-exclamation-triangle"></i> 
                                            Lệch: <span x-text="formatNumber(Math.abs(diff))"></span>
                                        </span>
                                    </td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Tab 3: Attachments -->
        <div class="tab-pane fade" id="tab-attachments">
            <div class="card">
                <div class="card-body">
                    <input type="file" name="attachments" multiple 
                           accept=".pdf,.jpg,.png,.xlsx,.docx">
                    <p class="text-sm text-gray-500 mt-2">
                        Hỗ trợ: PDF, JPG, PNG, Excel, Word. Tối đa 10MB/file.
                    </p>
                    
                    {% if voucher.attachments %}
                    <div class="mt-4">
                        <h4>File đã đính kèm:</h4>
                        <ul>
                            {% for att in voucher.attachments.all %}
                            <li>
                                <a href="{{ att.file.url }}" target="_blank">
                                    <i class="bi bi-file-earmark"></i> {{ att.filename }}
                                </a>
                            </li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
        
        <!-- Tab 4: Audit history -->
        <div class="tab-pane fade" id="tab-audit">
            <div class="card">
                <div class="card-body">
                    {% if voucher.id %}
                    <table class="w-full">
                        <thead>
                            <tr class="border-b">
                                <th>Thời gian</th>
                                <th>Người dùng</th>
                                <th>Hành động</th>
                                <th>Thay đổi</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for log in voucher.audit_logs.all %}
                            <tr class="border-b">
                                <td>{{ log.created_at|date:"d/m/Y H:i:s" }}</td>
                                <td>{{ log.user.full_name }}</td>
                                <td>{{ log.get_action_display }}</td>
                                <td>{{ log.changes_summary }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    {% else %}
                    <p class="text-gray-500">Chưa có lịch sử (phiếu mới).</p>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
    
    <!-- Bottom actions -->
    <div class="flex justify-end gap-2 mt-6">
        <a href="/ledger/vouchers/" class="btn btn-secondary">Hủy</a>
        <button type="submit" name="action" value="save_draft" class="btn btn-secondary">
            Lưu tạm
        </button>
        <button type="submit" name="action" value="save_post" class="btn btn-primary">
            <i class="bi bi-check-circle"></i> Lưu & Ghi sổ
        </button>
    </div>
    
    <!-- Form messages (HTMX target) -->
    <div id="form-messages"></div>
</form>
{% endblock %}

{% block extra_js %}
<script>
// Datalist for accounts
const ACCOUNT_LIST = [
    {% for acc in accounts %}
    { code: "{{ acc.account_code }}", name: "{{ acc.account_name }}", level: {{ acc.account_level }} },
    {% endfor %}
];

function voucherForm(initial) {
    return {
        ...initial,
        lineCount: initial.lineCount,
        
        addLine() {
            const tbody = document.getElementById('lines-tbody');
            const newRow = tbody.querySelector('tr:last-child').cloneNode(true);
            
            // Update formset prefix
            const newIndex = tbody.children.length;
            newRow.querySelectorAll('[name*="lines-"]').forEach(input => {
                const name = input.name.replace(/lines-\d+-/, `lines-${newIndex}-`);
                input.name = name;
                input.id = name;
            });
            
            // Clear values
            newRow.querySelectorAll('input').forEach(input => {
                if (input.type === 'checkbox') input.checked = false;
                else input.value = '';
            });
            
            tbody.appendChild(newRow);
            this.lineCount++;
        },
        
        removeLine(button) {
            const tbody = document.getElementById('lines-tbody');
            if (tbody.children.length <= 2) {
                alert('Phải có ít nhất 2 dòng bút toán');
                return;
            }
            button.closest('tr').remove();
            this.lineCount--;
            this.updateTotals();
        },
        
        updateTotals() {
            // Trigger totals recompute
            window.dispatchEvent(new Event('update-totals'));
        },
        
        onTypeChange(type) {
            // Could update book_code, status based on type
        },
        
        onCurrencyChange() {
            if (this.currency === 'VND') {
                this.rate = 1;
            } else {
                // Fetch latest rate
                fetch(`/api/v1/exchange-rates/?currency_code=${this.currency}&latest=true`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.data.length > 0) {
                            this.rate = data.data[0].rate;
                        }
                    });
            }
        },
    };
}

function lineRow() {
    return {
        accountCode: '',
        objectCode: '',
        debit: 0,
        credit: 0,
        accountName: '',
        
        init() {
            this.accountCode = this.$el.querySelector('[name*=account_code]').value;
            this.debit = parseFloat(this.$el.querySelector('[name*=debit_vnd]').value) || 0;
            this.credit = parseFloat(this.$el.querySelector('[name*=credit_vnd]').value) || 0;
        },
        
        onAccountChange() {
            const found = ACCOUNT_LIST.find(a => a.code === this.accountCode);
            this.accountName = found ? found.name : '';
            
            // Show/hide object code field based on account config
            // ...
        },
        
        onAmountChange() {
            // Auto-fill credit when debit entered (or vice versa) for simple entries
            window.dispatchEvent(new Event('update-totals'));
        },
        
        searchObject() {
            // AJAX search for customer/vendor/employee based on account type
            // Show dropdown of matches
        },
    };
}

function totalsRow() {
    return {
        totalDebit: 0,
        totalCredit: 0,
        
        init() {
            this.calculate();
            window.addEventListener('update-totals', () => this.calculate());
            this.$watch('totalDebit', () => {});
        },
        
        calculate() {
            let debit = 0, credit = 0;
            document.querySelectorAll('[name*=debit_vnd]').forEach(input => {
                debit += parseFloat(input.value) || 0;
            });
            document.querySelectorAll('[name*=credit_vnd]').forEach(input => {
                credit += parseFloat(input.value) || 0;
            });
            this.totalDebit = debit;
            this.totalCredit = credit;
        },
        
        get isBalanced() {
            return Math.abs(this.totalDebit - this.totalCredit) < 1;
        },
        
        get diff() {
            return this.totalDebit - this.totalCredit;
        },
        
        formatNumber(n) {
            return new Intl.NumberFormat('vi-VN').format(n);
        },
    };
}

// Prevent form submit if unbalanced
document.getElementById('voucher-form').addEventListener('htmx:invalidSubmit', (e) => {
    alert('Vui lòng kiểm tra lại dữ liệu');
});

// Auto-save draft every 30 seconds
let autoSaveTimer;
document.querySelectorAll('#voucher-form input, #voucher-form select').forEach(el => {
    el.addEventListener('change', () => {
        clearTimeout(autoSaveTimer);
        autoSaveTimer = setTimeout(() => {
            // Auto-save draft
            const formData = new FormData(document.getElementById('voucher-form'));
            formData.append('action', 'auto_save');
            fetch(window.location.pathname, {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': getCsrfToken() },
            });
        }, 30000);
    });
});
</script>
{% endblock %}
```

## 3. Single line row template

```html
<!-- templates/ledger/voucher/_line_row.html -->
<tr x-data="lineRow()" x-init="init()" class="border-b hover:bg-gray-50">
    <td class="text-center text-gray-500">{{ index|add:1 }}</td>
    <td>
        <input type="text"
               name="lines-{{ index }}-account_code"
               value="{{ line_form.account_code.value|default:'' }}"
               list="account-list"
               @change="onAccountChange()"
               x-model="accountCode"
               class="form-control font-mono text-sm"
               required>
        <small class="text-gray-500" x-text="accountName"></small>
    </td>
    <td>
        <input type="text"
               name="lines-{{ index }}-object_code"
               value="{{ line_form.object_code.value|default:'' }}"
               x-model="objectCode"
               @input.debounce.300ms="searchObject()"
               class="form-control text-sm"
               placeholder="KH/NCC/NV...">
    </td>
    <td>
        <span class="text-sm text-gray-600" x-text="objectName"></span>
    </td>
    <td>
        <input type="text"
               name="lines-{{ index }}-debit_vnd"
               value="{{ line_form.debit_vnd.value|default:0 }}"
               x-model="debit"
               @input="onAmountChange()"
               class="form-control text-right font-mono text-sm num-vi">
    </td>
    <td>
        <input type="text"
               name="lines-{{ index }}-credit_vnd"
               value="{{ line_form.credit_vnd.value|default:0 }}"
               x-model="credit"
               @input="onAmountChange()"
               class="form-control text-right font-mono text-sm num-vi">
    </td>
    <td>
        <select name="lines-{{ index }}-cost_center_id"
                class="form-control text-sm">
            <option value="">--</option>
            {% for cc in cost_centers %}
            <option value="{{ cc.id }}" 
                    {% if line_form.cost_center_id.value == cc.id %}selected{% endif %}>
                {{ cc.code }}
            </option>
            {% endfor %}
        </select>
    </td>
    <td>
        <input type="text"
               name="lines-{{ index }}-description"
               value="{{ line_form.description.value|default:'' }}"
               class="form-control text-sm"
               placeholder="Diễn giải dòng...">
    </td>
    <td>
        <button type="button" 
                @click="removeLine($event.target)"
                class="text-red-600 hover:bg-red-50 rounded p-1">
            <i class="bi bi-trash"></i>
        </button>
    </td>
</tr>
```

## 4. Validation patterns

### 4.1. Client-side (Alpine)

```javascript
function voucherForm() {
    return {
        validate() {
            const errors = [];
            
            // Required fields
            if (!this.$el.querySelector('[name=voucher_date]').value) {
                errors.push('Ngày sổ cái là bắt buộc');
            }
            
            // At least 2 lines
            const lines = document.querySelectorAll('#lines-tbody tr');
            if (lines.length < 2) {
                errors.push('Phải có ít nhất 2 dòng bút toán');
            }
            
            // Balanced
            const totals = this.calculateTotals();
            if (Math.abs(totals.debit - totals.credit) > 1) {
                errors.push(`Tổng nợ (${totals.debit}) phải bằng tổng có (${totals.credit})`);
            }
            
            // Each line: N > 0 XOR C > 0
            lines.forEach((line, idx) => {
                const debit = parseFloat(line.querySelector('[name*=debit_vnd]').value) || 0;
                const credit = parseFloat(line.querySelector('[name*=credit_vnd]').value) || 0;
                if (debit > 0 && credit > 0) {
                    errors.push(`Dòng ${idx+1}: Không được có cả nợ và có`);
                }
                if (debit === 0 && credit === 0) {
                    errors.push(`Dòng ${idx+1}: Phải có nợ hoặc có`);
                }
                const account = line.querySelector('[name*=account_code]').value;
                if (!account) {
                    errors.push(`Dòng ${idx+1}: Tài khoản là bắt buộc`);
                }
            });
            
            return errors;
        },
        
        onSubmit() {
            const errors = this.validate();
            if (errors.length > 0) {
                showErrorToast(errors);
                return false;
            }
            return true;
        }
    };
}
```

### 4.2. Server-side (Pydantic + Service)

Đảm bảo validation ở cả client và server (không tin client).

## 5. UX enhancements

### 5.1. Auto-suggest object code

```html
<input type="text"
       x-model="objectCode"
       @input.debounce.300ms="searchObject()"
       list="object-list">

<datalist id="object-list">
    <option x-for="obj in objects" :key="obj.code" :value="obj.code">
        {{ obj.code }} - {{ obj.name }}
    </option>
</datalist>
```

### 5.2. Quick-add object (modal)

Nếu user nhập object_code không tồn tại, hiển thị nút "Tạo nhanh":

```html
<div x-show="showQuickAdd" class="mt-1">
    <button @click="openQuickAddModal()" class="btn btn-link btn-sm">
        <i class="bi bi-plus-circle"></i> Tạo nhanh "{{ objectCode }}"
    </button>
</div>
```

### 5.3. Copy from template

```html
<div class="form-group">
    <label>Sao chép từ mẫu</label>
    <select @change="copyFromTemplate($event.target.value)">
        <option value="">-- Chọn mẫu --</option>
        {% for t in templates %}
        <option value="{{ t.id }}">{{ t.name }}</option>
        {% endfor %}
    </select>
</div>
```

### 5.4. Calculator inline

Cho field tiền, cho phép user click vào icon calculator:

```html
<div class="input-group">
    <input type="text" name="amount" class="form-control">
    <button type="button" @click="openCalculator()" class="btn btn-outline">
        <i class="bi bi-calculator"></i>
    </button>
</div>
```

---

**Tiếp theo**: [04. Form danh mục](./04-form-danh-muc.md)
