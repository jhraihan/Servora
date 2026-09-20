from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel

class ServiceCategory(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, db_index=True)
    description = models.TextField(blank=True)

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
        if self.suggested_price_min is None or self.suggested_price_max is None:
            return None
        if price < self.suggested_price_min:
            return "low"
        if price > self.suggested_price_max:
            return "high"
        return "normal"

class Location(TimeStampedModel):
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
        chain, node = [], self.parent
        while node is not None:
            chain.append(node)
            node = node.parent
        return list(reversed(chain))

    def descendant_ids(self):
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
