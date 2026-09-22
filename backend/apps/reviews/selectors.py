from .models import CustomerRating, Review


def published_reviews_for(provider_id):
    return (
        Review.objects
        .filter(provider_id=provider_id, is_hidden=False,
                published_at__isnull=False)
        .select_related("customer", "customer__user")
        .prefetch_related("reply")
        .order_by("-created_at")
    )


def reviews_by_customer(customer_id):
    return (
        Review.objects
        .filter(customer_id=customer_id)
        .select_related("customer", "customer__user", "provider")
        .prefetch_related("reply")
        .order_by("-created_at")
    )


def review_for_provider(review_id, provider_id):
    return (
        Review.objects
        .filter(pk=review_id, provider_id=provider_id)
        .select_related("customer", "customer__user")
        .prefetch_related("reply")
        .first()
    )


def ratings_for_customer(customer_id):
    return (
        CustomerRating.objects
        .filter(customer_id=customer_id, published_at__isnull=False)
        .order_by("-created_at")
    )
