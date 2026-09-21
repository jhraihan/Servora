from django.urls import path

from . import views

app_name = "trust"

urlpatterns = [
    path("providers/<int:provider_id>/trust/",
         views.ProviderTrustView.as_view(), name="provider-trust"),
    path("provider/trust-history/", views.MyTrustHistoryView.as_view(),
         name="my-trust-history"),
    path("admin/trust-audit/<int:provider_id>/",
         views.TrustAuditView.as_view(), name="trust-audit"),
    path("admin/trust-recompute/<int:provider_id>/",
         views.RecomputeTrustView.as_view(), name="trust-recompute"),
]
