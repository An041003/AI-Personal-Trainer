from django.db import models

class Exercise(models.Model):
    title = models.CharField(max_length=255)
    body_part_raw = models.CharField(max_length=255, blank=True, default="")
    muscle_groups = models.JSONField(default=list, blank=True) 

    image_url = models.URLField(blank=True, null=True)
    image_file = models.CharField(max_length=512, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title

