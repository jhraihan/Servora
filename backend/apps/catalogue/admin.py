"""Admin management of the catalogue (PRD FR-2.1)."""

from django.contrib import admin

from .models import Location, Service, ServiceCategory


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 0
    fields = ["name", "pricing_model", "suggested_price_min",
              "suggested_price_max", "display_order", "is_active"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "display_order", "is_active",
                    "service_count"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ServiceInline]

    @admin.display(description="Services")
    def service_count(self, obj):
        return obj.services.count()


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "pricing_model",
                    "suggested_price_min", "suggested_price_max", "is_active"]
    list_filter = ["category", "pricing_model", "is_active"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["category"]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["name", "level", "parent", "latitude", "longitude",
                    "is_active"]
    list_filter = ["level", "is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["parent"]
