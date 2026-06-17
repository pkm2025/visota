"""Forms for voucher creation."""
from django import forms
from django.forms import formset_factory

from apps.ledger.models import AccountingVoucher


class VoucherHeaderForm(forms.Form):
    """Voucher header fields."""

    voucher_no = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Tự động nếu để trống',
            }
        ),
    )
    voucher_date = forms.DateField(
        widget=forms.DateInput(
            attrs={'class': 'form-control form-control-sm', 'type': 'date'}
        ),
    )
    voucher_type = forms.ChoiceField(
        choices=AccountingVoucher.VoucherType.choices,
        initial=AccountingVoucher.VoucherType.JOURNAL,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control form-control-sm',
                'rows': 2,
            }
        ),
    )


class VoucherLineForm(forms.Form):
    """Single bút toán line."""

    account_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm font-mono',
                'placeholder': 'TK',
                'list': 'account-list',
            }
        ),
    )
    object_code = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Đối tượng',
            }
        ),
    )
    debit_vnd = forms.DecimalField(
        required=False,
        max_digits=20,
        decimal_places=4,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control form-control-sm text-end font-mono',
                'step': '0.0001',
            }
        ),
    )
    credit_vnd = forms.DecimalField(
        required=False,
        max_digits=20,
        decimal_places=4,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control form-control-sm text-end font-mono',
                'step': '0.0001',
            }
        ),
    )
    description = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Diễn giải dòng',
            }
        ),
    )


VoucherLineFormSet = formset_factory(
    VoucherLineForm,
    extra=2,
    min_num=2,
    validate_min=True,
    can_delete=True,
)
