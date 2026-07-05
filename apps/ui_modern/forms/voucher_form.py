"""Forms for voucher creation."""

from typing import TYPE_CHECKING, Any

from django import forms
from django.forms import BaseFormSet, formset_factory

from apps.ledger.models import AccountingVoucher
from apps.master_data.models import InvoiceGroup, TaxRateCode

if TYPE_CHECKING:
    _BaseFormSet = BaseFormSet[Any]
else:
    _BaseFormSet = BaseFormSet


class VoucherHeaderForm(forms.Form):
    """Voucher header fields."""

    voucher_no = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Tự động nếu để trống",
            }
        ),
    )
    voucher_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control form-control-sm", "type": "date"}),
    )
    voucher_type = forms.ChoiceField(
        choices=AccountingVoucher.VoucherType.choices,
        initial=AccountingVoucher.VoucherType.JOURNAL,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control form-control-sm",
                "rows": 2,
            }
        ),
    )


class VoucherLineForm(forms.Form):
    """Single bút toán line."""

    account_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm font-mono",
                "placeholder": "TK",
                "list": "account-list",
            }
        ),
    )
    object_code = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Đối tượng",
            }
        ),
    )
    debit_vnd = forms.DecimalField(
        required=False,
        max_digits=20,
        decimal_places=4,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-sm text-end font-mono",
                "step": "0.0001",
                "aria-label": "Nợ VND",
            }
        ),
    )
    credit_vnd = forms.DecimalField(
        required=False,
        max_digits=20,
        decimal_places=4,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-sm text-end font-mono",
                "step": "0.0001",
                "aria-label": "Có VND",
            }
        ),
    )
    description = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Diễn giải dòng",
            }
        ),
    )


class _VoucherLineFormSet(_BaseFormSet):
    """Formset for voucher lines — labels the auto-added DELETE checkbox."""

    delete_aria_label = "Xóa dòng bút toán"

    def add_fields(self, form: Any, index: int | None) -> None:
        super().add_fields(form, index)
        delete_field = form.fields.get("DELETE")
        if delete_field is not None:
            delete_field.widget.attrs.setdefault("aria-label", self.delete_aria_label)


VoucherLineFormSet = formset_factory(
    VoucherLineForm,
    formset=_VoucherLineFormSet,
    extra=2,
    min_num=2,
    validate_min=True,
    can_delete=True,
)


class VoucherTaxLineForm(forms.Form):
    """Single tax-line entry under the 'Thuế' tab of the voucher form."""

    invoice_no = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Số HĐ",
            }
        ),
    )
    invoice_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control form-control-sm",
                "type": "date",
                "aria-label": "Ngày hóa đơn",
            },
        ),
    )
    invoice_form = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Mẫu HĐ (01GTKT)",
            }
        ),
    )
    invoice_symbol = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Ký hiệu HĐ",
            }
        ),
    )
    invoice_serial = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Số serial",
            }
        ),
    )
    tax_code = forms.ModelChoiceField(
        queryset=TaxRateCode.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-select-sm", "aria-label": "Mã thuế"}),
    )
    tax_rate = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-sm text-end font-mono",
                "step": "0.01",
                "aria-label": "Tỷ lệ thuế (%)",
            }
        ),
    )
    goods_amount_vnd = forms.DecimalField(
        required=False,
        max_digits=20,
        decimal_places=4,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-sm text-end font-mono tax-goods",
                "step": "0.0001",
                "aria-label": "Tiền hàng VND",
            }
        ),
    )
    tax_amount_vnd = forms.DecimalField(
        required=False,
        max_digits=20,
        decimal_places=4,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-sm text-end font-mono tax-amount",
                "step": "0.0001",
                "aria-label": "Tiền thuế VND",
            }
        ),
    )
    offset_account_code = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm font-mono",
                "placeholder": "TK đối ứng",
                "list": "account-list",
            }
        ),
    )
    invoice_group_code = forms.ModelChoiceField(
        queryset=InvoiceGroup.objects.all(),
        required=False,
        widget=forms.Select(
            attrs={"class": "form-select form-select-sm", "aria-label": "Nhóm hóa đơn"},
        ),
    )
    object_address = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Địa chỉ đối tượng",
            }
        ),
    )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        goods = cleaned.get("goods_amount_vnd")
        tax_amt = cleaned.get("tax_amount_vnd")
        # VAL-M1-009: validation prevents negative tax_amount when goods positive
        if goods is not None and tax_amt is not None and goods > 0 and tax_amt < 0:
            raise forms.ValidationError(
                {"tax_amount_vnd": "Số tiền thuế không được âm khi tiền hàng dương."}
            )
        return cleaned


class _VoucherTaxLineFormSet(_BaseFormSet):
    """Formset for tax lines — labels the auto-added DELETE checkbox."""

    delete_aria_label = "Xóa dòng thuế"

    def add_fields(self, form: Any, index: int | None) -> None:
        super().add_fields(form, index)
        delete_field = form.fields.get("DELETE")
        if delete_field is not None:
            delete_field.widget.attrs.setdefault("aria-label", self.delete_aria_label)


VoucherTaxLineFormSet = formset_factory(
    VoucherTaxLineForm,
    formset=_VoucherTaxLineFormSet,
    extra=1,
    min_num=0,
    validate_min=False,
    can_delete=True,
)
