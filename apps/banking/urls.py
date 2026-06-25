"""Banking URL routes."""

from django.urls import path

from .views import (
    BankAccountListView,
    BankReconciliationRunView,
    BankReconciliationView,
    BankStatementImportDetailView,
    BankStatementImportListView,
    BankStatementUploadView,
)

urlpatterns = [
    path("", BankAccountListView.as_view(), name="banking_account_list"),
    path("imports/", BankStatementImportListView.as_view(), name="banking_import_list"),
    path("imports/upload/", BankStatementUploadView.as_view(), name="banking_import_upload"),
    path("imports/<int:pk>/", BankStatementImportDetailView.as_view(), name="banking_import_detail"),
    path("reconcile/", BankReconciliationView.as_view(), name="banking_reconcile"),
    path("reconcile/run/", BankReconciliationRunView.as_view(), name="banking_reconcile_run"),
]
