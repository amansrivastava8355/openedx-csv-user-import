"""Forms for the staff CSV student upload UI."""

from django import forms


class CsvUploadForm(forms.Form):
    """Staff form for uploading a CSV of student emails (+ optional course IDs)."""

    csv_file = forms.FileField(
        label="CSV file",
        help_text=(
            "CSV with an email column. Optional course_id / course column enrolls "
            "each student. Multiple courses: separate with ; or use one row per course."
        ),
    )
    default_course_id = forms.CharField(
        label="Default course ID (optional)",
        required=False,
        help_text="Applied when a row has no course column value. Example: course-v1:OpenedX+DemoX+DemoCourse",
    )
    send_reset = forms.BooleanField(
        label="Send password reset email to new students",
        required=False,
        initial=True,
    )
    resend_existing = forms.BooleanField(
        label="Also resend reset email to existing users",
        required=False,
        initial=False,
    )
    enroll_existing = forms.BooleanField(
        label="Enroll existing users into the listed courses",
        required=False,
        initial=True,
    )
    dry_run = forms.BooleanField(
        label="Dry run (do not create users, enroll, or send email)",
        required=False,
        initial=False,
    )
