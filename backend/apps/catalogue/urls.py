from django.urls import path

from . import views

app_name = "catalogue"

urlpatterns = [
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("categories/<slug:slug>/", views.CategoryDetailView.as_view(),
         name="category-detail"),
    path("services/", views.ServiceListView.as_view(), name="service-list"),
    path("locations/", views.LocationListView.as_view(), name="location-list"),
    path("locations/tree/", views.LocationTreeView.as_view(),
         name="location-tree"),
]
