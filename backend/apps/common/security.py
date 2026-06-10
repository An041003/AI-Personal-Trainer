from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.common.models import Plan


def _string_value(value):
    text = str(value or "").strip()
    return text or None


def assert_user_plan_reference(user, plan_type, payload, *, required=True):
    """Ensure a client-supplied plan mutation references a plan owned by user."""
    payload = payload or {}
    plan_id = _string_value(
        payload.get("source_plan_id")
        or payload.get("plan_id")
        or payload.get("current_plan_id")
    )
    request_id = _string_value(
        payload.get("source_request_id")
        or payload.get("current_plan_request_id")
        or payload.get("request_id")
    )

    if not plan_id and not request_id:
        if required:
            raise ValidationError({"source_request_id": ["A source plan reference is required."]})
        return None
    if plan_id and not plan_id.isdigit():
        raise ValidationError({"source_plan_id": ["Source plan id must be numeric."]})

    queryset = Plan.objects.filter(user=user, plan_type=plan_type)
    if plan_id:
        queryset = queryset.filter(id=plan_id)
    if request_id:
        queryset = queryset.filter(payload__request_id=request_id)

    plan = queryset.first()
    if not plan:
        raise PermissionDenied("The referenced plan does not belong to the current user.")
    return plan
