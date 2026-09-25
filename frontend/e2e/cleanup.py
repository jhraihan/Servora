from django.contrib.auth import get_user_model
from django.db import transaction

from apps.bookings.models import Booking, ServiceRequest
from apps.payments.models import LedgerEntry, Payment
from apps.reviews.models import CustomerRating, Review

TEST_NAME_PATTERN = r"^(Kamal|Rumana) E2E \d+$"

User = get_user_model()

with transaction.atomic():
    users = User.objects.filter(full_name__regex=TEST_NAME_PATTERN)
    bookings = Booking.objects.filter(customer__user__in=users) | \
        Booking.objects.filter(provider__user__in=users)
    booking_ids = list(bookings.values_list("pk", flat=True))

    LedgerEntry.objects.filter(provider__user__in=users).delete()
    Payment.objects.filter(booking_id__in=booking_ids).delete()
    CustomerRating.objects.filter(booking_id__in=booking_ids).delete()
    Review.objects.filter(booking_id__in=booking_ids).delete()
    Booking.objects.filter(pk__in=booking_ids).delete()
    ServiceRequest.objects.filter(customer__user__in=users).delete()
    removed = users.count()
    users.delete()

print("e2e cleanup removed %d test user(s)" % removed)
