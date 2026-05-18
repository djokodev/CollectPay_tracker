from apps.audit.models import AuditLog


def write_audit_log(
    *,
    action,
    entity_type,
    entity_id,
    organization_id=None,
    actor=None,
    before_data=None,
    after_data=None,
    metadata=None,
    request=None,
):
    ip = None
    ua = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR")
        ua = request.META.get("HTTP_USER_AGENT", "")[:255]

    return AuditLog.objects.create(
        organization_id=organization_id,
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before_data=before_data or {},
        after_data=after_data or {},
        metadata=metadata or {},
        ip_address=ip,
        user_agent=ua,
    )
