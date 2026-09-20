"""Shared pagination: ?page=1&page_size=20, max 100 (PRD 9.1)."""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
