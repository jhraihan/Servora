from django.contrib import admin

from .models import (
    Availability, AvailabilityException, ProviderService, ServiceArea,
    VerificationDocument, WorkPhoto,
)

@admin.register(ProviderService)
class ProviderServiceAdmin(admin.ModelAdmin):
    list_display = ["provider", "service", "price", "is_active"]
    list_filter = ["is_active", "service__category"]
    search_fields = ["provider__display_name", "service__name"]
    autocomplete_fields = ["service"]

@admin.register(ServiceArea)
class ServiceAreaAdmin(admin.ModelAdmin):
    list_display = ["provider", "location", "travel_surcharge"]
    search_fields = ["provider__display_name", "location__name"]
    autocomplete_fields = ["location"]

@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ["provider", "weekday", "start_time", "end_time"]
    list_filter = ["weekday"]
    search_fields = ["provider__display_name"]

@admin.register(AvailabilityException)
class AvailabilityExceptionAdmin(admin.ModelAdmin):
    list_display = ["provider", "date", "is_available", "reason"]
    list_filter = ["is_available"]
    search_fields = ["provider__display_name"]

@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ["provider", "document_type", "status", "created_at",
                    "reviewed_at"]
    list_filter = ["status", "document_type"]
    search_fields = ["provider__display_name"]
    readonly_fields = ["file", "created_at", "reviewed_at", "reviewed_by"]

@admin.register(WorkPhoto)
class WorkPhotoAdmin(admin.ModelAdmin):
    list_display = ["provider", "caption", "display_order"]
    search_fields = ["provider__display_name"]
