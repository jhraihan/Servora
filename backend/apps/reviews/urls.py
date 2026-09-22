from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("providers/<int:provider_id>/reviews/",
         views.ProviderReviewListView.as_view(), name="provider-reviews"),
    path("reviews/", views.ReviewListCreateView.as_view(), name="reviews"),
    path("reviews/<int:review_id>/", views.ReviewEditView.as_view(),
         name="review-edit"),
    path("reviews/<int:review_id>/reply/", views.ReviewReplyView.as_view(),
         name="review-reply"),
    path("provider/reviews/", views.MyReceivedReviewsView.as_view(),
         name="my-reviews"),
    path("provider/rate-customer/", views.CustomerRatingView.as_view(),
         name="rate-customer"),
    path("admin/reviews/<int:review_id>/hide/", views.HideReviewView.as_view(),
         name="review-hide"),
    path("admin/reviews/<int:review_id>/unhide/",
         views.UnhideReviewView.as_view(), name="review-unhide"),
]
