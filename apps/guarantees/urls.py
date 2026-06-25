"""Bank guarantee URLs."""

from django.urls import path

from .views import BankGuaranteeListView

urlpatterns = [
    path("", BankGuaranteeListView.as_view(), name="list"),
]
