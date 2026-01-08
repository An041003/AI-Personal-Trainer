import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from backend.models import Exercise
from backend.domains.workout.contract import canonicalize_muscle, MUSCLE_TAXONOMY_SET

EQUIPMENT_RULES = [
    ("dumbbell", ["dumbbell"]),
    ("barbell", ["barbell"]),
    ("kettlebell", ["kettlebell"]),
    ("cable", ["cable", "pushdown", "pulldown"]),
    ("machine", ["machine", "lever"]),
    ("bodyweight", ["push-up", "pull-up", "chin-up", "plank", "burpee"]),
]

def infer_equipment(title: str) -> str:
    t = (title or "").lower()
    for equip, keys in EQUIPMENT_RULES:
        if any(k in t for k in keys):
            return equip
    return "unknown"

def normalize_muscles(body_part_raw: str) -> list[str]:
    """Normalize body_part_raw -> taxonomy muscles used by the workout domain.

    Notes:
      - Canonical: glutes -> hips
      - Drops unknown labels to avoid polluting DB with non-taxonomy values
    """
    if not body_part_raw:
        return []
    parts = [p.strip() for p in body_part_raw.split(",") if p.strip()]

    mapping = {
        "waist": "core",
        "hip": "hips",
        "hips": "hips",
        "glute": "glutes",
        "glutes": "glutes",
        "thigh": "quadriceps",
        "thighs": "quadriceps",
        "hamstring": "hamstrings",
        "hamstrings": "hamstrings",
        "calf": "calves",
        "calves": "calves",
        "upper arms": "biceps",
        "bicep": "biceps",
        "biceps": "biceps",
        "tricep": "triceps",
        "triceps": "triceps",
        "chest": "chest",
        "shoulder": "shoulders",
        "shoulders": "shoulders",
        "back": "back",
        "core": "core",
    }

    out: list[str] = []
    seen = set()

    for p in parts:
        key = p.lower()
        mapped = mapping.get(key, key)
        m = canonicalize_muscle(mapped)

        if m in MUSCLE_TAXONOMY_SET and m not in seen:
            out.append(m)
            seen.add(m)

    return out

class Command(BaseCommand):
    help = "Import exercises from a CSV file into workout_exercise table."

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True, help="Path to exercises.csv")

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        created, updated = 0, 0
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            required_cols = {"title", "body_part", "image_url", "image_file"}
            if not required_cols.issubset(set(reader.fieldnames or [])):
                raise CommandError(f"CSV columns must include: {sorted(required_cols)}. Got: {reader.fieldnames}")

            for row in reader:
                title = (row.get("title") or "").strip()
                if not title:
                    continue

                body_part_raw = (row.get("body_part") or "").strip()
                image_url = (row.get("image_url") or "").strip() or None
                image_file = (row.get("image_file") or "").strip()

                muscle_groups = normalize_muscles(body_part_raw)
                equipment = infer_equipment(title)

                obj, is_created = Exercise.objects.update_or_create(
                    title=title,
                    defaults={
                        "body_part_raw": body_part_raw,
                        "muscle_groups": muscle_groups,
                        "image_url": image_url,
                        "image_file": image_file,
                    },
                )
                if is_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f"Import done. created={created}, updated={updated}"))
