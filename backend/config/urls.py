
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.catalogue.urls")),
    path("api/v1/", include("apps.providers.urls")),
    path("api/v1/", include("apps.trust.urls")),
    path("api/v1/", include("apps.bookings.urls")),
    path("api/v1/", include("apps.reviews.urls")),
    path("api/v1/", include("apps.payments.urls")),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(),
         name="token-refresh"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
