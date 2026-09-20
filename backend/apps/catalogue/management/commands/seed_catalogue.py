from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.catalogue.models import Location, Service, ServiceCategory
from apps.catalogue.seed_data import CATEGORIES, DHAKA

class Command(BaseCommand):
    help = "Create or update service categories, services and locations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-locations", action="store_true",
            help="Seed only the service catalogue.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        cats, svcs = self._seed_catalogue()
        self.stdout.write(self.style.SUCCESS(
            "Categories: %d created, %d updated" % cats
        ))
        self.stdout.write(self.style.SUCCESS(
            "Services:   %d created, %d updated" % svcs
        ))

        if not options["skip_locations"]:
            locs = self._seed_locations()
            self.stdout.write(self.style.SUCCESS(
                "Locations:  %d created, %d updated" % locs
            ))

    def _seed_catalogue(self):
        cat_created = cat_updated = 0
        svc_created = svc_updated = 0

        for order, (name, icon, description, services) in enumerate(CATEGORIES):
            category, created = ServiceCategory.objects.update_or_create(
                slug=slugify(name),
                defaults={
                    "name": name,
                    "icon": icon,
                    "description": description,
                    "display_order": order,
                    "is_active": True,
                },
            )
            cat_created += created
            cat_updated += not created

            for s_order, (s_name, pricing, pmin, pmax, minutes) in \
                    enumerate(services):
                _, s_created = Service.objects.update_or_create(
                    category=category,
                    slug=slugify(s_name),
                    defaults={
                        "name": s_name,
                        "pricing_model": pricing,
                        "suggested_price_min":
                            Decimal(pmin) if pmin is not None else None,
                        "suggested_price_max":
                            Decimal(pmax) if pmax is not None else None,
                        "typical_duration_minutes": minutes,
                        "display_order": s_order,
                        "is_active": True,
                    },
                )
                svc_created += s_created
                svc_updated += not s_created

        return (cat_created, cat_updated), (svc_created, svc_updated)

    def _seed_locations(self):
        created = updated = 0

        city, was_created = Location.objects.update_or_create(
            slug=slugify(DHAKA["name"]),
            parent=None,
            defaults={
                "name": DHAKA["name"],
                "level": Location.Level.CITY,
                "latitude": Decimal(str(DHAKA["lat"])),
                "longitude": Decimal(str(DHAKA["lon"])),
                "is_active": True,
            },
        )
        created += was_created
        updated += not was_created

        for thana_name, t_lat, t_lon, areas in DHAKA["thanas"]:
            thana, was_created = Location.objects.update_or_create(
                slug=slugify(thana_name),
                parent=city,
                defaults={
                    "name": thana_name,
                    "level": Location.Level.THANA,
                    "latitude": Decimal(str(t_lat)),
                    "longitude": Decimal(str(t_lon)),
                    "is_active": True,
                },
            )
            created += was_created
            updated += not was_created

            for area_name, a_lat, a_lon in areas:
                _, was_created = Location.objects.update_or_create(
                    slug=slugify(area_name),
                    parent=thana,
                    defaults={
                        "name": area_name,
                        "level": Location.Level.AREA,
                        "latitude": Decimal(str(a_lat)),
                        "longitude": Decimal(str(a_lon)),
                        "is_active": True,
                    },
                )
                created += was_created
                updated += not was_created

        return created, updated
