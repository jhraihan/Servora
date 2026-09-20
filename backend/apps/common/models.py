"""Base models shared across apps."""

from django.db import models


class TimeStampedModel(models.Model):
    """Adds created_at / updated_at to any model."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AppendOnlyModel(TimeStampedModel):
    """
    Base for records that must never be mutated or removed -- BookingEvent,
    TrustSnapshot, JobRun (PRD 6.3, 12.3).

    The guard lives here rather than relying on convention, so an accidental
    .save() on a loaded instance fails loudly instead of silently rewriting
    history. Bulk paths (queryset.update / .delete) bypass Python-level hooks
    and are additionally blocked by a database trigger in a later migration.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError(
                "%s is append-only and cannot be modified after creation."
                % type(self).__name__
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError(
            "%s is append-only and cannot be deleted." % type(self).__name__
        )
