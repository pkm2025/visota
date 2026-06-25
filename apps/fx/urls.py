"""FX URLs."""

from django.urls import path

from .views import (
    ExchangeRateListView,
    FxRevaluationListView,
    FxRevaluationRunView,
)

urlpatterns = [
    path("rates/", ExchangeRateListView.as_view(), name="rate_list"),
    path("revaluation/", FxRevaluationListView.as_view(), name="revaluation_list"),
    path("revaluation/run/", FxRevaluationRunView.as_view(), name="revaluation_run"),
]
