import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from backend.models import NutritionAtom


def d(x: str, default: Decimal = Decimal("0")) -> Decimal:
    x = (x or "").strip()
    if not x:
        return default
    try:
        return Decimal(x)
    except InvalidOperation:
        return default


def i(x: str, default: int = 0) -> int:
    x = (x or "").strip()
    if not x:
        return default
    try:
        return int(Decimal(x))
    except Exception:
        return default


class Command(BaseCommand):
    help = "Seed or upsert NutritionAtom from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default="backend/nutrition_clean.csv",
            help="Path to nutrition atoms CSV",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate only, do not write to DB",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = Path(options["path"])
        dry_run = bool(options["dry_run"])

        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            required = [
                "canonical_name","display_name_vi","category","edible_form",
                "kcal_per_100g","protein_g_per_100g","carb_g_per_100g","fat_g_per_100g",
                "fiber_g_per_100g","sodium_mg_per_100g","default_serving_g","aliases",
            ]
            missing = [c for c in required if c not in reader.fieldnames]
            if missing:
                raise CommandError(f"Missing columns: {missing}")

            rows = list(reader)

        canonicals = [r["canonical_name"].strip() for r in rows if (r.get("canonical_name") or "").strip()]
        existing = {
            a.canonical_name: a
            for a in NutritionAtom.objects.filter(canonical_name__in=canonicals)
        }

        to_create = []
        to_update = []
        invalid = []

        for r in rows:
            canonical = (r.get("canonical_name") or "").strip()
            if not canonical:
                continue

            obj = existing.get(canonical)
            payload = dict(
                canonical_name=canonical,
                display_name_vi=(r.get("display_name_vi") or "").strip(),
                category=(r.get("category") or "").strip(),
                edible_form=(r.get("edible_form") or "").strip(),
                kcal_per_100g=d(r.get("kcal_per_100g"), Decimal("0")),
                protein_g_per_100g=d(r.get("protein_g_per_100g"), Decimal("0")),
                carb_g_per_100g=d(r.get("carb_g_per_100g"), Decimal("0")),
                fat_g_per_100g=d(r.get("fat_g_per_100g"), Decimal("0")),
                fiber_g_per_100g=d(r.get("fiber_g_per_100g"), Decimal("0")),
                sodium_mg_per_100g=i(r.get("sodium_mg_per_100g"), 0),
                default_serving_g=d(r.get("default_serving_g"), Decimal("100")),
                aliases=(r.get("aliases") or "").strip(),
                source="manual_seed",
                is_active=True,
            )

            # basic validation
            if payload["category"] not in dict(NutritionAtom.Category.choices):
                invalid.append((canonical, "invalid_category", payload["category"]))
                continue
            if payload["edible_form"] not in dict(NutritionAtom.EdibleForm.choices):
                invalid.append((canonical, "invalid_edible_form", payload["edible_form"]))
                continue

            if obj is None:
                to_create.append(NutritionAtom(**payload))
            else:
                for k, v in payload.items():
                    setattr(obj, k, v)
                to_update.append(obj)

        if invalid:
            self.stdout.write(self.style.WARNING(f"Invalid rows: {len(invalid)}"))
            for x in invalid[:20]:
                self.stdout.write(f"- {x}")
            raise CommandError("Fix invalid rows before seeding")

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"DRY RUN OK: parsed {len(rows)} rows, create {len(to_create)}, update {len(to_update)}"
            ))
            return

        if to_create:
            NutritionAtom.objects.bulk_create(to_create, batch_size=500)
        if to_update:
            NutritionAtom.objects.bulk_update(
                to_update,
                fields=[
                    "display_name_vi","category","edible_form",
                    "kcal_per_100g","protein_g_per_100g","carb_g_per_100g","fat_g_per_100g",
                    "fiber_g_per_100g","sodium_mg_per_100g","default_serving_g","aliases",
                    "source","is_active",
                ],
                batch_size=500
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seed DONE: created {len(to_create)}, updated {len(to_update)}"
        ))
