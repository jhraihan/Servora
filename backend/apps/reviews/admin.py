from django.contrib import admin

from .models import CustomerRating, ProviderReply, Review, ReviewEdit

class ReviewEditInline(admin.TabularInline):
    model = ReviewEdit
    extra = 0
    readonly_fields = ["previous_rating", "previous_comment", "created_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "provider", "rating", "is_hidden", "published_at",
                    "created_at"]
    list_filter = ["is_hidden", "rating"]
    search_fields = ["provider__display_name", "comment"]
    readonly_fields = ["booking", "customer", "provider", "edit_count",
                       "published_at", "reveal_deadline"]
    inlines = [ReviewEditInline]

@admin.register(ProviderReply)
class ProviderReplyAdmin(admin.ModelAdmin):
    list_display = ["review", "provider", "created_at"]

@admin.register(CustomerRating)
class CustomerRatingAdmin(admin.ModelAdmin):
    list_display = ["booking", "customer", "rating", "published_at"]
    list_filter = ["rating"]

@admin.register(ReviewEdit)
class ReviewEditAdmin(admin.ModelAdmin):
    list_display = ["review", "previous_rating", "created_at"]
    readonly_fields = [f.name for f in ReviewEdit._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
