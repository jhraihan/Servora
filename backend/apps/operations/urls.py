from django.urls import path

from . import views

app_name = "operations"

urlpatterns = [
    path("admin/job-runs/", views.JobHealthView.as_view(), name="job-health"),
]
