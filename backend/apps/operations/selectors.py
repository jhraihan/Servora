from django.utils import timezone

from .jobs import OVERDUE_MULTIPLIER, SCHEDULE
from .models import JobRun


def job_health(*, now=None):
    now = now or timezone.now()
    rows = []
    for job in SCHEDULE:
        latest = JobRun.objects.filter(job=job.name).first()
        last_success = JobRun.objects.filter(
            job=job.name, status=JobRun.Status.SUCCEEDED,
        ).first()

        allowed = timezone.timedelta(
            minutes=job.every_minutes * OVERDUE_MULTIPLIER
        )
        overdue = (
            last_success is None
            or last_success.finished_at < now - allowed
        )
        stuck = JobRun.objects.filter(
            job=job.name,
            status=JobRun.Status.RUNNING,
            started_at__lt=now - timezone.timedelta(minutes=job.every_minutes),
        ).exists()

        rows.append({
            "job": job.name,
            "purpose": job.purpose,
            "cron": job.cron,
            "every_minutes": job.every_minutes,
            "last_status": latest.status if latest else None,
            "last_run_at": latest.started_at if latest else None,
            "last_success_at": last_success.finished_at if last_success
            else None,
            "last_message": latest.message if latest else "",
            "overdue": overdue,
            "stuck": stuck,
            "healthy": not overdue and not stuck
            and (latest is None or latest.status != JobRun.Status.FAILED),
        })
    return rows


def recent_runs(*, job=None, limit=50):
    qs = JobRun.objects.all()
    if job:
        qs = qs.filter(job=job)
    return qs[:limit]
