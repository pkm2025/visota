from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    """Visota ERP login form — username + password with Vietnamese UI.

    Subclasses Django's AuthenticationForm so it accepts the `request`
    kwarg passed by LoginView, while still letting us style the widgets.
    """

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Tên đăng nhập",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Mật khẩu",
            }
        ),
    )

    def get_invalid_login_error(self):
        """Vietnamese error message for invalid credentials."""
        return forms.ValidationError(
            "Tên đăng nhập hoặc mật khẩu không đúng.",
            code="invalid_login",
        )
