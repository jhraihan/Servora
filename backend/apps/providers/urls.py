from django.urls import path

from . import views

app_name = "providers"

urlpatterns = [
    path("providers/", views.ProviderSearchView.as_view(), name="search"),
    path("providers/<int:provider_id>/", views.ProviderDetailView.as_view(),
         name="detail"),
    path("providers/<int:provider_id>/availability/",
         views.ProviderAvailabilityView.as_view(), name="availability"),

    path("provider/profile/", views.MyProfileView.as_view(), name="my-profile"),
    path("provider/accepting-work/", views.AcceptingWorkView.as_view(),
         name="accepting-work"),
    path("provider/services/", views.MyOfferingsView.as_view(),
         name="my-offerings"),
    path("provider/services/<int:offering_id>/",
         views.MyOfferingDetailView.as_view(), name="my-offering-detail"),
    path("provider/service-areas/", views.MyServiceAreasView.as_view(),
         name="my-service-areas"),
    path("provider/availability/", views.MyAvailabilityView.as_view(),
         name="my-availability"),
    path("provider/availability/exceptions/",
         views.MyAvailabilityExceptionView.as_view(),
         name="my-availability-exception"),
    path("provider/verification/", views.MyVerificationView.as_view(),
         name="my-verification"),
    path("provider/work-photos/", views.MyWorkPhotosView.as_view(),
         name="my-work-photos"),
    path("provider/work-photos/<int:photo_id>/",
         views.MyWorkPhotoDetailView.as_view(), name="my-work-photo-detail"),

    path("admin/verifications/", views.VerificationQueueView.as_view(),
         name="verification-queue"),
    path("admin/verifications/<int:document_id>/file/",
         views.VerificationFileView.as_view(), name="verification-file"),
    path("admin/verifications/<int:document_id>/decide/",
         views.VerificationDecisionView.as_view(), name="verification-decide"),
]
