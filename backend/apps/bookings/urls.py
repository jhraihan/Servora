from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("requests/", views.RequestListCreateView.as_view(), name="requests"),
    path("requests/<int:request_id>/", views.RequestDetailView.as_view(),
         name="request-detail"),
    path("requests/<int:request_id>/withdraw/",
         views.RequestWithdrawView.as_view(), name="request-withdraw"),
    path("requests/<int:request_id>/respond/", views.RespondView.as_view(),
         name="respond"),
    path("provider/inbox/", views.ProviderInboxView.as_view(), name="inbox"),
    path("bookings/", views.BookingListView.as_view(), name="bookings"),
    path("bookings/<int:booking_id>/", views.BookingDetailView.as_view(),
         name="booking-detail"),
    path("bookings/<int:booking_id>/start/", views.StartJobView.as_view(),
         name="booking-start"),
    path("bookings/<int:booking_id>/complete/",
         views.CompleteJobView.as_view(), name="booking-complete"),
    path("bookings/<int:booking_id>/confirm/",
         views.ConfirmBookingView.as_view(), name="booking-confirm"),
    path("bookings/<int:booking_id>/cancel/",
         views.CancelBookingView.as_view(), name="booking-cancel"),
    path("bookings/<int:booking_id>/dispute/",
         views.DisputeBookingView.as_view(), name="booking-dispute"),
]
