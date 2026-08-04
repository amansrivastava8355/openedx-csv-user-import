"""Helper to persist an import summary as audit rows."""

from openedx_csv_user_import.models import CsvImportBatch, CsvImportRow
from openedx_csv_user_import.services import ImportSummary


def save_import_batch(
    summary: ImportSummary,
    *,
    source_filename: str = "",
    created_by=None,
    notes: str = "",
) -> CsvImportBatch:
    """Create CsvImportBatch + CsvImportRow records from an ImportSummary."""
    batch = CsvImportBatch.objects.create(
        created_by=created_by,
        source_filename=(source_filename or "")[:255],
        dry_run=summary.dry_run,
        created_count=summary.created,
        skipped_count=summary.skipped_existing,
        reset_sent_count=summary.reset_sent,
        reset_failed_count=summary.reset_failed,
        enrolled_count=summary.enrolled,
        enrollment_failed_count=summary.enrollment_failed,
        already_enrolled_count=summary.already_enrolled,
        invalid_count=summary.invalid,
        error_count=summary.errors,
        notes=notes,
    )
    rows_to_create = []
    for row in summary.rows:
        if not row.email and row.status != "error":
            continue
        rows_to_create.append(
            CsvImportRow(
                batch=batch,
                email=(row.email or "unknown@invalid.local")[:254],
                username=row.username[:150],
                course_ids=(row.course_ids or "")[:1024],
                status=row.status[:128],
                detail=row.detail[:1024],
            )
        )
    CsvImportRow.objects.bulk_create(rows_to_create)
    return batch
