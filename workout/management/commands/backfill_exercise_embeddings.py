from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from workout.models import Exercise
from workout.services.embedding_service import embed_document, DEFAULT_DIM, DEFAULT_EMBED_MODEL


def _build_embedding_text(ex: Exercise) -> str:
    mg = ", ".join(ex.muscle_groups or [])
    parts = [ex.title, ex.body_part_raw, mg]
    return " | ".join([p.strip() for p in parts if (p or "").strip()])


class Command(BaseCommand):
    help = "Backfill embeddings for Exercise into Postgres (pgvector)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100000)
        parser.add_argument("--batch-size", type=int, default=32)
        parser.add_argument("--rebuild", action="store_true")  # overwrite existing embedding
        parser.add_argument("--dim", type=int, default=DEFAULT_DIM)

    def handle(self, *args, **opts):
        limit = int(opts["limit"])
        batch_size = max(1, int(opts["batch_size"]))
        rebuild = bool(opts["rebuild"])
        dim = int(opts["dim"])

        qs = Exercise.objects.all().order_by("id")
        if not rebuild:
            qs = qs.filter(embedding__isnull=True)

        total = min(limit, qs.count())
        self.stdout.write(f"Target rows: {total} | batch_size={batch_size} | dim={dim}")

        done = 0
        while done < total:
            batch = list(qs[done : done + batch_size])
            if not batch:
                break

            texts = []
            for ex in batch:
                ex.embedding_text = _build_embedding_text(ex)
                ex.embedding_model = f"{DEFAULT_EMBED_MODEL}@{dim}"
                texts.append(ex.embedding_text)

            vectors = embed_document(texts, output_dim=dim)

            for ex, vec in zip(batch, vectors):
                ex.embedding = vec

            with transaction.atomic():
                Exercise.objects.bulk_update(
                    batch,
                    ["embedding", "embedding_text", "embedding_model"],
                    batch_size=batch_size,
                )

            done += len(batch)
            self.stdout.write(f"Progress: {done}/{total}")

        self.stdout.write("Done.")
