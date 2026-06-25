"""E-invoice URL routes (included directly in ui_modern/urls.py)."""

from django.urls import path

from .views import (
    EInvoiceCancelView,
    EInvoiceDetailView,
    EInvoiceIssueFromSalesView,
    EInvoiceJsonDownloadView,
    EInvoiceListView,
    EInvoicePublishView,
    EInvoiceReportView,
    EInvoiceXmlDownloadView,
)

urlpatterns = [
    path("", EInvoiceListView.as_view(), name="list"),
    path("<int:pk>/", EInvoiceDetailView.as_view(), name="detail"),
    path(
        "issue-from-sales/<int:sales_invoice_id>/",
        EInvoiceIssueFromSalesView.as_view(),
        name="issue_from_sales",
    ),
    path("<int:pk>/publish/", EInvoicePublishView.as_view(), name="publish"),
    path("<int:pk>/cancel/", EInvoiceCancelView.as_view(), name="cancel"),
    path("<int:pk>/download/xml/", EInvoiceXmlDownloadView.as_view(), name="download_xml"),
    path("<int:pk>/download/json/", EInvoiceJsonDownloadView.as_view(), name="download_json"),
    path("reports/generate/", EInvoiceReportView.as_view(), name="report_generate"),
]
