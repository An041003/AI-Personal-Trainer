from django.contrib import admin
from django.utils.html import format_html

import json

from .models import ApiRequestLog, Plan, PlanAudit, ShortTermMemoryEntry


def pretty_json(value):
    return format_html("<pre style='white-space: pre-wrap; max-width: 1000px'>{}</pre>", json.dumps(value, indent=2, ensure_ascii=False))


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "plan_type", "title", "created_at")
    list_filter = ("plan_type", "created_at")
    search_fields = ("title", "user__username")
    readonly_fields = ("payload_pretty", "created_at")

    @admin.display(description="Payload")
    def payload_pretty(self, obj):
        return pretty_json(obj.payload)


@admin.register(PlanAudit)
class PlanAuditAdmin(admin.ModelAdmin):
    list_display = ("id", "request_id", "domain", "step", "created_at")
    list_filter = ("domain", "step", "created_at")
    search_fields = ("request_id", "domain", "step")
    readonly_fields = ("payload_pretty", "created_at")

    @admin.display(description="Payload")
    def payload_pretty(self, obj):
        return pretty_json(obj.payload)


@admin.register(ApiRequestLog)
class ApiRequestLogAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "user", "method", "path", "status_code", "duration_ms")
    list_filter = ("method", "status_code", "created_at")
    search_fields = ("user__username", "path", "method")
    readonly_fields = (
        "created_at",
        "user",
        "method",
        "path",
        "query_params_pretty",
        "status_code",
        "request_body_pretty",
        "response_body_pretty",
        "ip_address",
        "duration_ms",
    )
    date_hierarchy = "created_at"

    @admin.display(description="Query params")
    def query_params_pretty(self, obj):
        return pretty_json(obj.query_params)

    @admin.display(description="Request body")
    def request_body_pretty(self, obj):
        return pretty_json(obj.request_body)

    @admin.display(description="Response body")
    def response_body_pretty(self, obj):
        return pretty_json(obj.response_body)


@admin.register(ShortTermMemoryEntry)
class ShortTermMemoryEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "domain",
        "scope",
        "entity_type",
        "raw_label",
        "reason_code",
        "expires_at",
        "hit_count",
    )
    list_filter = ("domain", "scope", "entity_type", "reason_code", "expires_at", "created_at")
    search_fields = ("user__username", "entity_key", "raw_label", "reason_code")
    readonly_fields = ("created_at", "updated_at", "metadata_pretty")
    date_hierarchy = "expires_at"

    @admin.display(description="Metadata")
    def metadata_pretty(self, obj):
        return pretty_json(obj.metadata)
