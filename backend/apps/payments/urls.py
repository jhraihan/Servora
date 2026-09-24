from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("payments/", views.PaymentListView.as_view(), name="payments"),
    path("provider/earnings/", views.ProviderEarningsView.as_view(),
         name="earnings"),
    path("provider/ledger/", views.ProviderLedgerView.as_view(),
         name="ledger"),
    path("provider/dashboard/", views.ProviderDashboardView.as_view(),
         name="dashboard"),
    path("admin/payments/flagged/", views.FlaggedPaymentListView.as_view(),
         name="flagged"),
    path("admin/payments/<int:payment_id>/resolve/",
         views.ResolvePaymentView.as_view(), name="resolve"),
    path("admin/providers/<int:provider_id>/settlements/",
         views.ProviderSettlementView.as_view(), name="settlement"),
]
