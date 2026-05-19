from django.conf import settings

from apps.common.openai_client import embed_texts


def build_embedding_text(exercise):
    return (
        f"{exercise.title} | muscles={exercise.muscle_groups} | "
        f"body_part={exercise.body_part_raw} | equipment={exercise.equipment}"
    )


def backfill_exercise_embeddings(queryset, *, batch_size=64):
    updated = 0
    model = settings.OPENAI_EMBED_MODEL
    items = list(queryset)
    for start in range(0, len(items), batch_size):
        batch = items[start : start + batch_size]
        texts = [build_embedding_text(item) for item in batch]
        vectors = embed_texts(texts, model=model)
        for exercise, vector, text in zip(batch, vectors, texts):
            exercise.embedding = vector
            exercise.embedding_text = text
            exercise.embedding_model = model
            exercise.save(update_fields=["embedding", "embedding_text", "embedding_model"])
            updated += 1
    return updated

