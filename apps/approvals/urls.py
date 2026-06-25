"""Approval URL routes."""

from django.urls import path

from .views import (
    ApprovalApproveView,
    ApprovalDetailView,
    ApprovalQueueView,
    ApprovalRejectView,
    ApprovalRuleListView,
)

app_name = "approvals"

urlpatterns = [
    path("", ApprovalQueueView.as_view(), name="approval_queue"),
    path("rules/", ApprovalRuleListView.as_view(), name="approval_rules"),
    path("<int:pk>/", ApprovalDetailView.as_view(), name="approval_detail"),
    path("<int:pk>/approve/", ApprovalApproveView.as_view(), name="approval_approve"),
    path("<int:pk>/reject/", ApprovalRejectView.as_view(), name="approval_reject"),
]
