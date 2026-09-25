from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

RETENTION_DAYS = 30
MESSAGE_LIMIT = 2000


class JobRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", _("Running")
        SUCCEEDED = "succeeded", _("Succeeded")
        FAILED = "failed", _("Failed")

    job = models.CharField(max_length=60, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.RUNNING)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    rows_affected = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at", "-id"]
        indexes = [
            models.Index(fields=["job", "-started_at"]),
            models.Index(fields=["job", "status", "-started_at"]),
        ]

    def __str__(self):
        return "%s %s at %s" % (self.job, self.status, self.started_at)

    @classmethod
    def start(cls, job):
        return cls.objects.create(job=job)

    def succeed(self, rows, message=""):
        self.status = self.Status.SUCCEEDED
        self.finished_at = timezone.now()
        self.rows_affected = max(int(rows or 0), 0)
        self.message = str(message)[:MESSAGE_LIMIT]
        self.save(update_fields=["status", "finished_at", "rows_affected",
                                 "message"])

    def fail(self, error):
        self.status = self.Status.FAILED
        self.finished_at = timezone.now()
        self.message = ("%s: %s" % (type(error).__name__, error))[:MESSAGE_LIMIT]
        self.save(update_fields=["status", "finished_at", "message"])

    @property
    def duration_seconds(self):
        if self.finished_at is None:
            return None
        return round((self.finished_at - self.started_at).total_seconds(), 3)

    @classmethod
    def prune(cls, job, *, keep_days=RETENTION_DAYS, now=None):
        cutoff = (now or timezone.now()) - timezone.timedelta(days=keep_days)
        deleted, _ = cls.objects.filter(job=job, started_at__lt=cutoff).delete()
        return deleted
