from django.conf import settings
from django.db import models


class Plan(models.Model):
    PLAN_WORKOUT = "workout"
    PLAN_NUTRITION = "nutrition"
    PLAN_FULL = "full"
    PLAN_TYPE_CHOICES = [
        (PLAN_WORKOUT, "Workout"),
        (PLAN_NUTRITION, "Nutrition"),
        (PLAN_FULL, "Full"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="plans")
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "plan"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.plan_type}: {self.title}"


class PlanAudit(models.Model):
    plan = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.SET_NULL, related_name="audits")
    request_id = models.UUIDField(null=True, blank=True, db_index=True)
    domain = models.CharField(max_length=50)
    step = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "plan_audit"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.domain}:{self.step}"


class ShortTermMemoryEntry(models.Model):
    DOMAIN_NUTRITION = "nutrition"
    DOMAIN_WORKOUT = "workout"
    DOMAIN_CHOICES = [
        (DOMAIN_NUTRITION, "Nutrition"),
        (DOMAIN_WORKOUT, "Workout"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="short_term_memories")
    domain = models.CharField(max_length=30, choices=DOMAIN_CHOICES)
    scope = models.CharField(max_length=50)
    entity_type = models.CharField(max_length=50)
    entity_key = models.CharField(max_length=255)
    raw_label = models.CharField(max_length=255, blank=True, default="")
    reason_code = models.CharField(max_length=80, blank=True, default="unknown")
    source_action = models.CharField(max_length=80, blank=True, default="")
    expires_at = models.DateTimeField(db_index=True)
    hit_count = models.PositiveIntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "short_term_memory_entry"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "domain", "expires_at"]),
            models.Index(fields=["user", "domain", "scope", "entity_type"]),
            models.Index(fields=["entity_type", "entity_key"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "domain", "scope", "entity_type", "entity_key"],
                name="uniq_short_term_memory_entity",
            )
        ]

    def __str__(self):
        return f"{self.domain}:{self.scope}:{self.entity_type}:{self.raw_label or self.entity_key}"


class ApiRequestLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="api_logs")
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    query_params = models.JSONField(default=dict, blank=True)
    status_code = models.PositiveIntegerField(null=True, blank=True)
    request_body = models.JSONField(default=dict, blank=True)
    response_body = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "api_request_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.method} {self.path} -> {self.status_code}"
