"""Loan URLs."""

from django.urls import path

from .views import BankLoanListView

urlpatterns = [
    path("", BankLoanListView.as_view(), name="list"),
]
