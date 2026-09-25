from django.conf import settings
from rest_framework.throttling import BaseThrottle


class ClientIdentHeaderMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.EXPOSE_CLIENT_IDENT:
            response["X-Client-Ident"] = BaseThrottle().get_ident(request) or ""
        return response
