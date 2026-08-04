"""Django admin for CSV import audit models."""

from django.contrib import admin

from openedx_csv_user_import.models import CsvImportBatch, CsvImportRow


class CsvImportRowInline(admin.TabularInline):
    model = CsvImportRow
    extra = 0
    readonly_fields = ("email", "username", "course_ids", "status", "detail")
    can_delete = False


@admin.register(CsvImportBatch)
class CsvImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "created_by",
        "source_filename",
        "dry_run",
        "created_count",
        "skipped_count",
        "enrolled_count",
        "reset_sent_count",
        "invalid_count",
        "error_count",
    )
    list_filter = ("dry_run", "created_at")
    readonly_fields = (
        "created_at",
        "created_by",
        "source_filename",
        "dry_run",
        "created_count",
        "skipped_count",
        "reset_sent_count",
        "reset_failed_count",
        "enrolled_count",
        "enrollment_failed_count",
        "already_enrolled_count",
        "invalid_count",
        "error_count",
        "notes",
    )
    inlines = [CsvImportRowInline]
