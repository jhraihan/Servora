from decimal import Decimal

from rest_framework import serializers

from apps.catalogue.serializers import LocationSerializer, ServiceSerializer

from .models import Booking, BookingEvent, ProviderResponse, ServiceRequest


class ServiceRequestSerializer(serializers.ModelSerializer):
    service_detail = ServiceSerializer(source="service", read_only=True)
    location_detail = LocationSerializer(source="location", read_only=True)
    response_count = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = ["id", "service", "service_detail", "location",
                  "location_detail", "address", "description", "kind",
                  "target_provider", "preferred_start", "preferred_end",
                  "state", "expires_at", "closed_at", "response_count",
                  "created_at"]
        read_only_fields = fields

    def get_response_count(self, obj):
        return obj.responses.count()


class ServiceRequestCreateSerializer(serializers.Serializer):
    service = serializers.IntegerField()
    location = serializers.IntegerField()
    address = serializers.CharField(max_length=500)
    description = serializers.CharField(max_length=2000)
    preferred_start = serializers.DateTimeField()
    preferred_end = serializers.DateTimeField()
    target_provider = serializers.IntegerField(required=False,
                                               allow_null=True)


class ProviderResponseSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source="provider.display_name",
                                          read_only=True)

    class Meta:
        model = ProviderResponse
        fields = ["id", "provider", "provider_name", "decision", "reason",
                  "response_seconds", "created_at"]
        read_only_fields = fields


class RespondSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True,
                                   default="")
    scheduled_for = serializers.DateTimeField(required=False, allow_null=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2,
                                     min_value=Decimal("0"), required=False,
                                     allow_null=True)


class BookingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingEvent
        fields = ["id", "from_state", "to_state", "actor", "reason",
                  "metadata", "created_at"]
        read_only_fields = fields


class BookingSerializer(serializers.ModelSerializer):
    service_detail = ServiceSerializer(source="request.service",
                                       read_only=True)
    provider_name = serializers.CharField(source="provider.display_name",
                                          read_only=True)
    address = serializers.CharField(source="request.address", read_only=True)

    class Meta:
        model = Booking
        fields = ["id", "request", "provider", "provider_name",
                  "service_detail", "address", "state", "scheduled_for",
                  "agreed_price", "final_price", "customer_confirmed_price",
                  "accepted_at", "started_at", "completed_at", "confirmed_at",
                  "cancelled_at", "cancelled_by", "cancel_reason",
                  "auto_confirmed", "created_at"]
        read_only_fields = fields


class BookingDetailSerializer(BookingSerializer):
    events = BookingEventSerializer(many=True, read_only=True)

    class Meta(BookingSerializer.Meta):
        fields = BookingSerializer.Meta.fields + ["events"]
        read_only_fields = fields


class CompleteSerializer(serializers.Serializer):
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2,
                                           min_value=Decimal("0"),
                                           required=False, allow_null=True)


class ConfirmSerializer(serializers.Serializer):
    confirmed_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"),
        required=False, allow_null=True,
    )


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)
