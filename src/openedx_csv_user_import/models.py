"""Audit trail for CSV student imports."""

from django.conf import settings
from django.db import models


class CsvImportBatch(models.Model):
    """One CSV upload / management-command run."""

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="csv_import_batches",
    )
    source_filename = models.CharField(max_length=255, blank=True)
    dry_run = models.BooleanField(default=False)
    created_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    reset_sent_count = models.PositiveIntegerField(default=0)
    reset_failed_count = models.PositiveIntegerField(default=0)
    enrolled_count = models.PositiveIntegerField(default=0)
    enrollment_failed_count = models.PositiveIntegerField(default=0)
    already_enrolled_count = models.PositiveIntegerField(default=0)
    invalid_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "CSV import batch"
        verbose_name_plural = "CSV import batches"

    def __str__(self) -> str:
        return f"CSV import {self.pk} @ {self.created_at:%Y-%m-%d %H:%M}"


class CsvImportRow(models.Model):
    """Per-student result belonging to a batch."""

    batch = models.ForeignKey(
        CsvImportBatch,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    email = models.EmailField(db_index=True)
    username = models.CharField(max_length=150, blank=True)
    course_ids = models.CharField(max_length=1024, blank=True)
    status = models.CharField(max_length=128)
    detail = models.CharField(max_length=1024, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.email} ({self.status})"
