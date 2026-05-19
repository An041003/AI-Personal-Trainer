import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.workout.contracts import BODY_PART_TO_MUSCLES
from apps.workout.models import Exercise


EQUIPMENT_KEYWORDS = {
    "dumbbell": "dumbbell",
    "barbell": "barbell",
    "cable": "cable",
    "lever": "machine",
    "machine": "machine",
    "smith": "smith_machine",
    "band": "resistance_band",
    "kettlebell": "kettlebell",
    "bench": "bench",
    "medicine ball": "medicine_ball",
    "ez bar": "ez_bar",
    "pull-up": "bodyweight",
    "push-up": "bodyweight",
    "dip": "bodyweight",
    "squat": "barbell",
}


def infer_equipment(title):
    lowered = title.lower()
    equipment = []
    for keyword, value in EQUIPMENT_KEYWORDS.items():
        if keyword in lowered and value not in equipment:
            equipment.append(value)
    return equipment or ["bodyweight"]


class Command(BaseCommand):
    help = "Import exercises from seed CSV without calling OpenAI."

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True, help="Path to exercises.csv")

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        if not csv_path.is_absolute():
            csv_path = Path.cwd() / csv_path

        created = 0
        updated = 0
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                title = (row.get("title") or "").strip()
                if not title:
                    continue
                body_part = (row.get("body_part") or "").strip()
                defaults = {
                    "body_part_raw": body_part,
                    "muscle_groups": BODY_PART_TO_MUSCLES.get(body_part, [body_part.lower()] if body_part else []),
                    "equipment": infer_equipment(title),
                    "image_url": (row.get("image_url") or "").strip(),
                    "image_file": (row.get("image_file") or "").strip(),
                }
                _, was_created = Exercise.objects.update_or_create(title=title, defaults=defaults)
                created += int(was_created)
                updated += int(not was_created)

        self.stdout.write(self.style.SUCCESS(f"Imported exercises. created={created} updated={updated}"))

