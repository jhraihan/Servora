from django.db import models

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class AppendOnlyModel(TimeStampedModel):
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
