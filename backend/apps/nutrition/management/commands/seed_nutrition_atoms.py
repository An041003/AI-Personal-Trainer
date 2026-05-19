import csv
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.nutrition.models import NutritionAtom


NUMERIC_FIELDS = [
    "kcal_per_100g",
    "protein_g_per_100g",
    "carb_g_per_100g",
    "fat_g_per_100g",
    "fiber_g_per_100g",
    "sodium_mg_per_100g",
    "default_serving_g",
]


def decimal_value(value):
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value).strip())


def bool_value(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


class Command(BaseCommand):
    help = "Seed NutritionAtom rows from CSV."

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True, help="Path to nutrition_atoms_seed.csv")

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        if not csv_path.is_absolute():
            csv_path = Path.cwd() / csv_path

        created = 0
        updated = 0
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                canonical_name = (row.get("canonical_name") or "").strip()
                if not canonical_name:
                    continue
                defaults = {
                    "display_name_vi": (row.get("display_name_vi") or canonical_name).strip(),
                    "category": (row.get("category") or "").strip(),
                    "food_role": (row.get("food_role") or "").strip(),
                    "edible_form": (row.get("edible_form") or "").strip(),
                    "aliases": (row.get("aliases") or "").strip(),
                    "source": (row.get("source") or "").strip(),
                    "is_active": bool_value(row.get("is_active")),
                }
                for field in NUMERIC_FIELDS:
                    defaults[field] = decimal_value(row.get(field))
                _, was_created = NutritionAtom.objects.update_or_create(
                    canonical_name=canonical_name,
                    defaults=defaults,
                )
                created += int(was_created)
                updated += int(not was_created)

        self.stdout.write(self.style.SUCCESS(f"Seeded nutrition atoms. created={created} updated={updated}"))

