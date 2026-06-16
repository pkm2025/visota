# 04. Form danh mục (Master Data Form)

> Pattern cho form danh mục: khách hàng, NCC, sản phẩm, nhân viên.

## 1. Đặc điểm khác với form chứng từ

| Đặc điểm | Form chứng từ | Form danh mục |
|----------|--------------|--------------|
| Số lượng fields | Vừa (5-10 header + N lines) | Nhiều (10-50 fields) |
| Dynamic lines | Có | Không |
| Tabs | Header, Lines, Attachments | General, Contact, Address, Tax, Banking |
| Action | Lưu tạm / Ghi sổ | Lưu / Lưu & tiếp tục |
| Multi-record | Không (1 form/1 record) | Có (cho phép lưu nhiều nhanh) |

## 2. Layout (Customer form ví dụ)

```
┌─────────────────────────────────────────────────────────────────────┐
│ ← Khách hàng  |  Sửa: KH001 - Công ty ABC                            │
├─────────────────────────────────────────────────────────────────────┤
│ [Tab: Thông tin chung] [Tab: Liên hệ] [Tab: Địa chỉ] [Tab: Thuế]    │
│                                                                      │
│  ┌─ Card: Thông tin chung ─────────────────────────────────┐       │
│  │                                                           │       │
│  │  Mã khách hàng*        Tên khách hàng*                    │       │
│  │  [KH001          ]     [Công ty ABC               ]     │       │
│  │                                                           │       │
│  │  Tên tiếng Anh          Nhóm khách hàng                   │       │
│  │  [ABC Co., Ltd    ]     [VIP                      ▼]    │       │
│  │                                                           │       │
│  │  MST                     Người đại diện                  │       │
│  │  [0101234567      ]     [Nguyễn Văn A              ]    │       │
│  │                                                           │       │
│  │  ☐ Đang hoạt động        ☐ Là cá nhân                   │       │
│  └───────────────────────────────────────────────────────────┘       │
│                                                                      │
│  ┌─ Card: Liên hệ ──────────────────────────────────────────┐       │
│  │  Điện thoại              Email                            │       │
│  │  [0241234567      ]     [contact@abc.com            ]   │       │
│  │                                                           │       │
│  │  Website                 Fax                              │       │
│  │  [www.abc.com     ]     [0241234568                ]    │       │
│  └───────────────────────────────────────────────────────────┘       │
│                                                                      │
│  ┌─ Card: Thanh toán ───────────────────────────────────────┐       │
│  │  Điều khoản TT          Hạn mức tín dụng                  │       │
│  │  [30 days        ]     [1.000.000.000              ]    │       │
│  │                                                           │       │
│  │  Ngoại tệ mặc định      TK công nợ                       │       │
│  │  [VND             ▼]   [131                       ]     │       │
│  └───────────────────────────────────────────────────────────┘       │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  [Hủy]   [Lưu]   [Lưu & tạo mới]   [Lưu & xem]                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 3. HTML template (Customer form)

```html
{% extends 'base/layout.html' %}

{% block content %}
<form method="post" 
      hx-post="{% if customer.id %}{% url 'customer_update' customer.id %}{% else %}{% url 'customer_create' %}{% endif %}"
      hx-target="#form-messages"
      hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'
      x-data="customerForm()">
    
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
        <div>
            <a href="{% url 'customer_list' %}" class="text-blue-600 hover:underline">
                ← Khách hàng
            </a>
            <h1 class="text-2xl font-bold mt-2">
                {% if customer.id %}Sửa: {{ customer.code }} - {{ customer.name }}{% else %}Thêm khách hàng{% endif %}
            </h1>
        </div>
        <div class="flex gap-2">
            <a href="{% url 'customer_list' %}" class="btn btn-secondary">Hủy</a>
            <button type="submit" name="action" value="save" class="btn btn-primary">
                <i class="bi bi-check"></i> Lưu
            </button>
            {% if not customer.id %}
            <button type="submit" name="action" value="save_new" class="btn btn-secondary">
                Lưu & tạo mới
            </button>
            {% endif %}
            <button type="submit" name="action" value="save_view" class="btn btn-secondary">
                Lưu & xem
            </button>
        </div>
    </div>
    
    <!-- Tabs -->
    <ul class="nav nav-tabs mb-4">
        <li class="nav-item">
            <a class="nav-link active" data-bs-toggle="tab" href="#tab-general">
                <i class="bi bi-info-circle"></i> Thông tin chung
            </a>
        </li>
        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="tab" href="#tab-contact">
                <i class="bi bi-telephone"></i> Liên hệ
            </a>
        </li>
        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="tab" href="#tab-payment">
                <i class="bi bi-credit-card"></i> Thanh toán
            </a>
        </li>
        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="tab" href="#tab-attachments">
                <i class="bi bi-paperclip"></i> Hồ sơ
            </a>
        </li>
    </ul>
    
    <div class="tab-content space-y-4">
        
        <!-- Tab: General -->
        <div class="tab-pane fade show active" id="tab-general">
            <div class="card">
                <div class="card-body grid grid-cols-2 gap-4">
                    
                    <div class="form-group">
                        <label class="form-label">
                            Mã khách hàng <span class="text-red-500">*</span>
                        </label>
                        <input type="text" 
                               name="code" 
                               value="{{ form.code.value|default:'' }}"
                               required
                               x-model="code"
                               @blur="checkDuplicate()"
                               class="form-control">
                        <small class="text-red-500" x-show="duplicate" x-cloak>
                            Mã đã tồn tại
                        </small>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">
                            Tên khách hàng <span class="text-red-500">*</span>
                        </label>
                        <input type="text" 
                               name="name" 
                               value="{{ form.name.value|default:'' }}"
                               required
                               class="form-control">
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Tên tiếng Anh</label>
                        <input type="text" 
                               name="name_en" 
                               value="{{ form.name_en.value|default:'' }}"
                               class="form-control">
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Tên viết tắt</label>
                        <input type="text" 
                               name="short_name" 
                               value="{{ form.short_name.value|default:'' }}"
                               class="form-control">
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Nhóm khách hàng</label>
                        <select name="customer_group_id" class="form-control select2">
                            <option value="">-- Không --</option>
                            {% for g in customer_groups %}
                            <option value="{{ g.id }}" 
                                    {% if form.customer_group_id.value == g.id %}selected{% endif %}>
                                {{ g.name }}
                            </option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">NV phụ trách</label>
                        <select name="sales_staff_id" class="form-control">
                            <option value="">-- Không --</option>
                            {% for s in sales_staff %}
                            <option value="{{ s.id }}" 
                                    {% if form.sales_staff_id.value == s.id %}selected{% endif %}>
                                {{ s.name }}
                            </option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Mã số thuế</label>
                        <div class="input-group">
                            <input type="text" 
                                   name="tax_code" 
                                   value="{{ form.tax_code.value|default:'' }}"
                                   x-model="taxCode"
                                   @blur="verifyTaxCode()"
                                   class="form-control">
                            <button type="button" 
                                    @click="verifyTaxCode()"
                                    class="btn btn-outline-secondary">
                                <i class="bi bi-search"></i> Tra cứu
                            </button>
                        </div>
                        <small x-show="taxVerified === false" class="text-red-500">
                            MST không hợp lệ
                        </small>
                        <small x-show="taxVerified === true" class="text-green-600">
                            ✓ {{ taxInfo.name }}
                        </small>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Người đại diện</label>
                        <input type="text" 
                               name="legal_representative" 
                               value="{{ form.legal_representative.value|default:'' }}"
                               class="form-control">
                    </div>
                    
                    <div class="form-group col-span-2">
                        <div class="flex gap-6">
                            <label class="form-check">
                                <input type="checkbox" name="is_active" 
                                       {% if form.is_active.value or not form.is_active.value %}checked{% endif %}
                                       class="form-check-input">
                                <span class="form-check-label">Đang hoạt động</span>
                            </label>
                            <label class="form-check">
                                <input type="checkbox" name="is_individual" 
                                       {% if form.is_individual.value %}checked{% endif %}
                                       class="form-check-input">
                                <span class="form-check-label">Là cá nhân (không phải DN)</span>
                            </label>
                            <label class="form-check">
                                <input type="checkbox" name="is_supplier" 
                                       {% if form.is_supplier.value %}checked{% endif %}
                                       class="form-check-input">
                                <span class="form-check-label">Là nhà cung cấp luôn</span>
                            </label>
                        </div>
                    </div>
                    
                    <div class="form-group col-span-2">
                        <label class="form-label">Ghi chú</label>
                        <textarea name="notes" rows="2" class="form-control">{{ form.notes.value|default:'' }}</textarea>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Tab: Contact -->
        <div class="tab-pane fade" id="tab-contact">
            <div class="card">
                <div class="card-body grid grid-cols-2 gap-4">
                    
                    <div class="form-group">
                        <label class="form-label">Điện thoại</label>
                        <input type="tel" name="phone" 
                               value="{{ form.phone.value|default:'' }}" 
                               class="form-control">
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Email</label>
                        <input type="email" name="email" 
                               value="{{ form.email.value|default:'' }}" 
                               class="form-control">
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Website</label>
                        <input type="url" name="website" 
                               value="{{ form.website.value|default:'' }}" 
                               class="form-control">
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Fax</label>
                        <input type="tel" name="fax" 
                               value="{{ form.fax.value|default:'' }}" 
                               class="form-control">
                    </div>
                    
                    <div class="form-group col-span-2">
                        <label class="form-label">Địa chỉ</label>
                        <textarea name="address" rows="2" class="form-control">{{ form.address.value|default:'' }}</textarea>
                    </div>
                    
                    <!-- Province/District/Ward (cascading) -->
                    <div class="form-group">
                        <label class="form-label">Tỉnh/Thành phố</label>
                        <select name="province_id" 
                                class="form-control"
                                hx-get="/api/locations/districts/"
                                hx-target="#district-select"
                                hx-trigger="change"
                                hx-vals='js:{province_id: $el.value}">
                            <option value="">-- Chọn --</option>
                            {% for p in provinces %}
                            <option value="{{ p.id }}" 
                                    {% if form.province_id.value == p.id %}selected{% endif %}>
                                {{ p.name }}
                            </option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Quận/Huyện</label>
                        <select name="district_id" id="district-select" class="form-control">
                            {% if districts %}
                            {% for d in districts %}
                            <option value="{{ d.id }}">{{ d.name }}</option>
                            {% endfor %}
                            {% endif %}
                        </select>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Tab: Payment -->
        <div class="tab-pane fade" id="tab-payment">
            <div class="card">
                <div class="card-body grid grid-cols-2 gap-4">
                    
                    <div class="form-group">
                        <label class="form-label">Điều khoản thanh toán</label>
                        <select name="payment_terms" class="form-control">
                            <option value="">-- Chọn --</option>
                            <option value="immediate" {% if form.payment_terms.value == 'immediate' %}selected{% endif %}>Thanh toán ngay</option>
                            <option value="7_days" {% if form.payment_terms.value == '7_days' %}selected{% endif %}>7 ngày</option>
                            <option value="15_days" {% if form.payment_terms.value == '15_days' %}selected{% endif %}>15 ngày</option>
                            <option value="30_days" {% if form.payment_terms.value == '30_days' %}selected{% endif %}>30 ngày</option>
                            <option value="60_days" {% if form.payment_terms.value == '60_days' %}selected{% endif %}>60 ngày</option>
                            <option value="custom" {% if form.payment_terms.value == 'custom' %}selected{% endif %}>Tùy chỉnh</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Hạn mức tín dụng (VND)</label>
                        <input type="number" name="credit_limit" 
                               value="{{ form.credit_limit.value|default:0 }}"
                               step="1000000"
                               class="form-control text-right num-vi">
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Ngoại tệ mặc định</label>
                        <select name="currency_code" class="form-control">
                            {% for c in currencies %}
                            <option value="{{ c.code }}" 
                                    {% if form.currency_code.value == c.code or not form.currency_code.value and c.code == 'VND' %}selected{% endif %}>
                                {{ c.code }} - {{ c.name }}
                            </option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">TK công nợ</label>
                        <input type="text" 
                               name="gl_account_receivable" 
                               value="{{ form.gl_account_receivable.value|default:'131' }}"
                               list="ar-accounts"
                               class="form-control font-mono">
                        <datalist id="ar-accounts">
                            {% for acc in ar_accounts %}
                            <option value="{{ acc.account_code }}">{{ acc.account_name }}</option>
                            {% endfor %}
                        </datalist>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Thuế suất GTGT mặc định</label>
                        <select name="default_vat_rate" class="form-control">
                            <option value="0.10" {% if form.default_vat_rate.value == 0.10 %}selected{% endif %}>10%</option>
                            <option value="0.08" {% if form.default_vat_rate.value == 0.08 %}selected{% endif %}>8%</option>
                            <option value="0.05" {% if form.default_vat_rate.value == 0.05 %}selected{% endif %}>5%</option>
                            <option value="0" {% if form.default_vat_rate.value == 0 %}selected{% endif %}>0%</option>
                            <option value="-1" {% if form.default_vat_rate.value == -1 %}selected{% endif %}>Không chịu thuế</option>
                        </select>
                    </div>
                </div>
            </div>
            
            <!-- Banking info -->
            <div class="card mt-4">
                <div class="card-header">
                    <h3 class="font-bold">Tài khoản ngân hàng</h3>
                </div>
                <div class="card-body">
                    <table class="w-full" x-data="{ banks: [], newIndex: 0 }">
                        <thead>
                            <tr class="border-b">
                                <th>Ngân hàng</th>
                                <th>Chi nhánh</th>
                                <th>Số TK</th>
                                <th>Chủ TK</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            <template x-for="(bank, idx) in banks" :key="idx">
                                <tr class="border-b">
                                    <td><input :name="`banks-${idx}-bank_id`" x-model="bank.bank_id" class="form-control"></td>
                                    <td><input :name="`banks-${idx}-branch`" x-model="bank.branch" class="form-control"></td>
                                    <td><input :name="`banks-${idx}-account_no`" x-model="bank.account_no" class="form-control"></td>
                                    <td><input :name="`banks-${idx}-account_holder`" x-model="bank.account_holder" class="form-control"></td>
                                    <td>
                                        <button type="button" @click="banks.splice(idx, 1)" class="text-red-600">
                                            <i class="bi bi-trash"></i>
                                        </button>
                                    </td>
                                </tr>
                            </template>
                        </tbody>
                        <tfoot>
                            <tr>
                                <td colspan="5">
                                    <button type="button" @click="banks.push({})" class="btn btn-sm btn-outline">
                                        <i class="bi bi-plus"></i> Thêm TK
                                    </button>
                                </td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Tab: Attachments -->
        <div class="tab-pane fade" id="tab-attachments">
            <div class="card">
                <div class="card-body">
                    <input type="file" name="attachments" multiple 
                           accept=".pdf,.jpg,.png">
                    <p class="text-sm text-gray-500 mt-2">
                        Hồ sơ KYC, giấy phép kinh doanh, hợp đồng nguyên tắc, ...
                    </p>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Form messages -->
    <div id="form-messages"></div>
</form>
{% endblock %}

{% block extra_js %}
<script>
function customerForm() {
    return {
        code: '',
        duplicate: false,
        taxCode: '',
        taxVerified: null,
        taxInfo: {},
        
        async checkDuplicate() {
            if (!this.code) return;
            
            const response = await fetch(`/api/v1/customers/check-code/?code=${this.code}`);
            const data = await response.json();
            this.duplicate = data.exists;
        },
        
        async verifyTaxCode() {
            if (!this.taxCode || this.taxCode.length < 10) {
                this.taxVerified = false;
                return;
            }
            
            // Call TCT API to verify
            const response = await fetch(`/api/v1/tax/lookup/?tax_code=${this.taxCode}`);
            if (response.ok) {
                const data = await response.json();
                if (data.valid) {
                    this.taxVerified = true;
                    this.taxInfo = data.info;
                    // Auto-fill name if empty
                    const nameInput = document.querySelector('[name=name]');
                    if (!nameInput.value && this.taxInfo.name) {
                        nameInput.value = this.taxInfo.name;
                    }
                    // Auto-fill address
                    const addressInput = document.querySelector('[name=address]');
                    if (!addressInput.value && this.taxInfo.address) {
                        addressInput.value = this.taxInfo.address;
                    }
                } else {
                    this.taxVerified = false;
                }
            }
        },
    };
}
</script>
{% endblock %}
```

## 4. UX enhancements

### 4.1. Auto-fill from tax code lookup

Tích hợp API tra cứu MST của Tổng cục Thuế:
- Nhập MST → auto fill tên, địa chỉ

### 4.2. Inline validation

```html
<input @blur="validateEmail()">
<small x-show="emailError" class="text-red-500" x-text="emailError"></small>
```

### 4.3. Save & continue

Cho phép tạo nhiều records nhanh:
```html
<button type="submit" name="action" value="save_new">
    Lưu & tạo mới
</button>
```

### 4.4. Bulk edit

Cho list view, select nhiều records → bulk edit một field.

## 5. Validation patterns

### 5.1. Code uniqueness

```python
# Server-side validation
def clean_code(self):
    code = self.cleaned_data['code']
    qs = Customer.objects.filter(company_id=self.company_id, code=code)
    if self.instance.pk:
        qs = qs.exclude(pk=self.instance.pk)
    if qs.exists():
        raise ValidationError('Mã khách hàng đã tồn tại')
    return code
```

### 5.2. Tax code checksum

```python
def validate_vietnam_tax_code(tax_code: str) -> bool:
    """Validate MST theo algorithm chính thức"""
    if len(tax_code) not in [10, 13]:
        return False
    
    # Check digits only
    if not tax_code[:10].isdigit():
        return False
    
    # Checksum for 10-digit code
    weights = [31, 29, 23, 19, 17, 13, 7, 5, 3]
    digits = [int(c) for c in tax_code[:9]]
    total = sum(d * w for d, w in zip(digits, weights))
    check = total % 11
    if check >= 10:
        check = check - 10
    return check == int(tax_code[9])
```

### 5.3. Email format

```python
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

def clean_email(self):
    email = self.cleaned_data.get('email')
    if email:
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError('Email không hợp lệ')
    return email
```

## 6. Form cho các entity khác

Tương tự customer form:

| Entity | Số fields | Đặc biệt |
|--------|----------|---------|
| Vendor | ~25 | Tương tự customer |
| Product | ~30 | Có tab: pricing, inventory, purchasing |
| Employee | ~50 | Có tab: personal, contract, education, family, insurance |
| Fixed Asset | ~20 | Có tab: depreciation, transactions |
| Warehouse | ~10 | Đơn giản |
| Bank Account | ~10 | Đơn giản |

---

**Kết thúc**: Bộ tài liệu hoàn chỉnh tại [README.md](../README.md)
