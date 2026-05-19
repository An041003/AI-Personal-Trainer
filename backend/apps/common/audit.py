from .models import PlanAudit


def record_audit(*, request_id=None, domain, step, payload=None, plan=None):
    return PlanAudit.objects.create(
        plan=plan,
        request_id=request_id,
        domain=domain,
        step=step,
        payload=payload or {},
    )

