from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand

from apps.workout.models import Exercise
from apps.workout.services.embeddings import backfill_exercise_embeddings


class Command(BaseCommand):
    help = "Backfill OpenAI embeddings for exercises."

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=64)

    def handle(self, *args, **options):
        queryset = Exercise.objects.filter(embedding=None)
        try:
            updated = backfill_exercise_embeddings(queryset, batch_size=options["batch_size"])
        except ImproperlyConfigured as exc:
            self.stdout.write(self.style.WARNING(str(exc)))
            return
        self.stdout.write(self.style.SUCCESS(f"Backfilled {updated} exercise embeddings."))

