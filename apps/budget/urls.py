"""Budget URLs."""

from django.urls import path

from .views import (
    BudgetDetailView,
    BudgetGenerateView,
    BudgetListView,
    BudgetRefreshActualsView,
    CashFlowGenerateView,
    CashFlowView,
)

urlpatterns = [
    path("", BudgetListView.as_view(), name="list"),
    path("<int:pk>/", BudgetDetailView.as_view(), name="detail"),
    path("generate/", BudgetGenerateView.as_view(), name="generate"),
    path("<int:pk>/refresh/", BudgetRefreshActualsView.as_view(), name="refresh"),
    path("cash-flow/", CashFlowView.as_view(), name="cash_flow"),
    path("cash-flow/generate/", CashFlowGenerateView.as_view(), name="cash_flow_generate"),
]
