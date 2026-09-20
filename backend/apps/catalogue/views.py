from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import selectors
from .models import Location
from .serializers import (
    LocationSerializer, LocationTreeSerializer, ServiceCategoryDetailSerializer,
    ServiceCategorySerializer, ServiceSerializer,
)

class CategoryListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ServiceCategorySerializer
    pagination_class = None

    def get_queryset(self):
        return selectors.active_categories(with_service_count=True)

class CategoryDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        category = selectors.category_by_slug(slug)
        if category is None:
            return Response(
                {"error": {"code": "not_found",
                           "message": "No such category.", "details": {}}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ServiceCategoryDetailSerializer(category).data)

class ServiceListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ServiceSerializer

    def get_queryset(self):
        return selectors.active_services(
            category_slug=self.request.query_params.get("category"),
            search=self.request.query_params.get("search"),
        )

class LocationListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = LocationSerializer
    pagination_class = None

    def get_queryset(self):
        parent = self.request.query_params.get("parent")
        return selectors.location_tree(
            level=self.request.query_params.get("level"),
            parent_id=int(parent) if parent and parent.isdigit() else None,
        )

class LocationTreeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        roots = (
            Location.objects
            .filter(is_active=True, level=Location.Level.CITY)
            .prefetch_related("children__children")
        )
        return Response(LocationTreeSerializer(roots, many=True).data)
