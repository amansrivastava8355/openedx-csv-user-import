"""Staff views for CSV student import + course enrollment."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from openedx_csv_user_import.audit import save_import_batch
from openedx_csv_user_import.forms import CsvUploadForm
from openedx_csv_user_import.models import CsvImportBatch
from openedx_csv_user_import.services import import_users_from_csv


def _is_staff(user) -> bool:
    return bool(user.is_authenticated and user.is_staff)


@login_required
@user_passes_test(_is_staff)
@require_http_methods(["GET", "POST"])
def import_csv_view(request):
    """Staff page: upload a CSV of student emails and optional course IDs."""
    form = CsvUploadForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        upload = form.cleaned_data["csv_file"]
        summary = import_users_from_csv(
            upload,
            default_course_id=form.cleaned_data.get("default_course_id") or None,
            send_reset=form.cleaned_data["send_reset"],
            resend_existing=form.cleaned_data["resend_existing"],
            skip_existing=not form.cleaned_data["resend_existing"],
            enroll_existing=form.cleaned_data["enroll_existing"],
            dry_run=form.cleaned_data["dry_run"],
            request=request,
        )
        save_import_batch(
            summary,
            source_filename=getattr(upload, "name", ""),
            created_by=request.user,
            notes="staff UI upload",
        )
        messages.success(
            request,
            (
                f"Import finished: created={summary.created}, "
                f"existing={summary.skipped_existing}, enrolled={summary.enrolled}, "
                f"reset_sent={summary.reset_sent}, invalid={summary.invalid}, "
                f"errors={summary.errors}"
            ),
        )
        return redirect("csv_user_import:import")

    recent = CsvImportBatch.objects.all()[:20]
    return render(
        request,
        "openedx_csv_user_import/import.html",
        {
            "form": form,
            "recent_batches": recent,
        },
    )
