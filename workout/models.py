from django.db import models
from pgvector.django import VectorField, HnswIndex

class Exercise(models.Model):
    title = models.CharField(max_length=255)
    body_part_raw = models.CharField(max_length=255, blank=True, default="")
    muscle_groups = models.JSONField(default=list, blank=True)

    image_url = models.URLField(blank=True, null=True)
    image_file = models.CharField(max_length=512, blank=True, default="")

    # Embedding fields
    embedding = VectorField(dimensions=768, null=True, blank=True)
    embedding_text = models.TextField(blank=True, default="")
    embedding_model = models.CharField(max_length=64, blank=True, default="gemini-embedding-001@768")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            HnswIndex(
                name="wk_ex_emb_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            )
        ]

    def __str__(self) -> str:
        return self.title
