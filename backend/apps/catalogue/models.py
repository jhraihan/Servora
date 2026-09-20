"""
Service taxonomy and geography.

Two-level catalogue: ServiceCategory (Electrical) contains Service (Ceiling
fan installation). Locations are a self-referencing tree -- city > thana >
area -- because provider service areas and customer addresses are both
expressed at whichever level is appropriate (PRD FR-2.1, FR-3.3).
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel


class ServiceCategory(TimeStampedModel):
    """Top-level grouping shown on the landing page (PRD FR-2.4)."""

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, db_index=True)
    description = models.TextField(blank=True)

    # Lucide/heroicon name resolved by the client; kept as a string so the
    # catalogue stays data, not code.
    icon = models.CharField(max_length=40, blank=True)

    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = _("service categories")
        ordering = ["display_order", "name"]
        indexes = [models.Index(fields=["is_active", "display_order"])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)


class Service(TimeStampedModel):
    """
    A concrete, bookable service.

    The pricing model decides what the customer is shown before booking and
    what the provider may set on their ProviderService (PRD FR-2.2).
    """

    class PricingModel(models.TextChoices):
        FIXED = "fixed", _("Fixed price")
        HOURLY = "hourly", _("Hourly rate")
        VISIT_QUOTE = "visit_quote", _("Visit fee, then quote")

    category = models.ForeignKey(
        ServiceCategory, on_delete=models.PROTECT, related_name="services",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, db_index=True)
    description = models.TextField(blank=True)

    pricing_model = models.CharField(
        max_length=20, choices=PricingModel.choices,
        default=PricingModel.FIXED,
    )

    # Platform-suggested band in BDT, used to flag provider prices as
    # unusually high or low rather than to forbid them (PRD FR-2.3, Q4).
    suggested_price_min = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    suggested_price_max = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    typical_duration_minutes = models.PositiveIntegerField(null=True,
                                                           blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category__display_order", "display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "slug"], name="service_slug_unique_in_category",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(suggested_price_min__isnull=True)
                    | models.Q(suggested_price_max__isnull=True)
                    | models.Q(suggested_price_max__gte=models.F(
                        "suggested_price_min"))
                ),
                name="service_price_band_ordered",
            ),
        ]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["is_active", "display_order"]),
        ]

    def __str__(self):
        return f"{self.category.name} / {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    def price_flag(self, price):
        """
        Classify a provider's price against the suggested band.

        Returns "low", "normal", "high", or None when no band is defined.
        The platform flags outliers to the customer; it does not block them
        (PRD 15, Q4).
        """
        if self.suggested_price_min is None or self.suggested_price_max is None:
            return None
        if price < self.suggested_price_min:
            return "low"
        if price > self.suggested_price_max:
            return "high"
        return "normal"


class Location(TimeStampedModel):
    """
    Geography as a self-referencing tree: city > thana > area.

    A centroid is stored on every node so proximity sorting works with the
    earthdistance <@> operator without a separate coordinates table
    (PRD 6.1, 8.1).
    """

    class Level(models.TextChoices):
        CITY = "city", _("City")
        THANA = "thana", _("Thana")
        AREA = "area", _("Area")

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, db_index=True)
    level = models.CharField(max_length=10, choices=Level.choices)
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True,
        related_name="children",
    )

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True,
                                   blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True,
                                    blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["level", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "slug"], name="location_slug_unique_in_parent",
            ),
            # A city is the root; anything below it must have a parent.
            models.CheckConstraint(
                condition=(
                    models.Q(level="city")
                    | models.Q(parent__isnull=False)
                ),
                name="location_non_city_requires_parent",
            ),
        ]
        indexes = [
            models.Index(fields=["level", "is_active"]),
            models.Index(fields=["parent", "is_active"]),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.name}, {self.parent.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    @property
    def has_coordinates(self):
        return self.latitude is not None and self.longitude is not None

    def ancestors(self):
        """Root-first path to this node, for breadcrumbs."""
        chain, node = [], self.parent
        while node is not None:
            chain.append(node)
            node = node.parent
        return list(reversed(chain))

    def descendant_ids(self):
        """
        All ids at or below this node.

        A provider serving "Dhanmondi" (thana) should match a request in
        "Dhanmondi 27" (area), so area lookups expand downward. The tree is
        three levels deep by design, so an iterative walk is cheaper and
        clearer than a recursive CTE here.
        """
        ids = [self.pk]
        frontier = [self.pk]
        while frontier:
            child_ids = list(
                Location.objects
                .filter(parent_id__in=frontier)
                .values_list("pk", flat=True)
            )
            if not child_ids:
                break
            ids.extend(child_ids)
            frontier = child_ids
        return ids
