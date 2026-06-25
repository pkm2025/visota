"""Bidding URLs."""

from django.urls import path

from .views import (
    BidConvertToContractView,
    BidOpportunityDetailView,
    BidOpportunityListView,
)

urlpatterns = [
    path("", BidOpportunityListView.as_view(), name="list"),
    path("<int:pk>/", BidOpportunityDetailView.as_view(), name="detail"),
    path(
        "<int:pk>/convert-to-contract/",
        BidConvertToContractView.as_view(),
        name="convert_to_contract",
    ),
]
