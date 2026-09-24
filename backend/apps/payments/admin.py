from django.contrib import admin

from .models import LedgerEntry, Payment


class LedgerEntryInline(admin.TabularInline):
    model = LedgerEntry
    extra = 0
    can_delete = False
    readonly_fields = ["kind", "amount", "description", "reference",
                       "recorded_by", "created_at"]
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "booking", "provider", "method", "status",
                    "provider_recorded_amount", "customer_confirmed_amount",
                    "settled_amount", "commission_amount"]
    list_filter = ["status", "method"]
    search_fields = ["provider__display_name", "customer__user__phone",
                     "gateway_reference"]
    readonly_fields = [f.name for f in Payment._meta.fields]
    inlines = [LedgerEntryInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ["provider", "kind", "amount", "booking", "created_at"]
    list_filter = ["kind"]
    search_fields = ["provider__display_name", "reference"]
    readonly_fields = [f.name for f in LedgerEntry._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
