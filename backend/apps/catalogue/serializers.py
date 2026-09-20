from rest_framework import serializers

from .models import Location, Service, ServiceCategory

class ServiceSerializer(serializers.ModelSerializer):
    category_slug = serializers.CharField(source="category.slug",
                                          read_only=True)
    category_name = serializers.CharField(source="category.name",
                                          read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "name", "slug", "description",
            "category", "category_slug", "category_name",
            "pricing_model",
            "suggested_price_min", "suggested_price_max",
            "typical_duration_minutes",
        ]

class ServiceCategorySerializer(serializers.ModelSerializer):
    service_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = ServiceCategory
        fields = ["id", "name", "slug", "description", "icon",
                  "display_order", "service_count"]

class ServiceCategoryDetailSerializer(ServiceCategorySerializer):
    services = serializers.SerializerMethodField()

    class Meta(ServiceCategorySerializer.Meta):
        fields = ServiceCategorySerializer.Meta.fields + ["services"]

    def get_services(self, obj):
        return ServiceSerializer(obj.services.all(), many=True).data

class LocationSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True,
                                        default=None)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = ["id", "name", "slug", "level", "parent", "parent_name",
                  "full_name", "latitude", "longitude"]

    def get_full_name(self, obj):
        return str(obj)

class LocationTreeSerializer(LocationSerializer):
    children = serializers.SerializerMethodField()

    class Meta(LocationSerializer.Meta):
        fields = LocationSerializer.Meta.fields + ["children"]

    def get_children(self, obj):
        kids = [c for c in obj.children.all() if c.is_active]
        return LocationTreeSerializer(kids, many=True).data
