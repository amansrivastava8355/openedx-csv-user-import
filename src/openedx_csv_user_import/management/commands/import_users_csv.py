"""Import Open edX students from a CSV of emails (+ optional course enrollment)."""

from django.core.management.base import BaseCommand, CommandError

from openedx_csv_user_import.audit import save_import_batch
from openedx_csv_user_import.services import import_users_from_csv


class Command(BaseCommand):
    help = (
        "Create Open edX student accounts from a CSV of emails, optionally enroll "
        "them in courses, and send password-reset emails. "
        "CSV may include email and course_id columns."
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to the CSV file inside the container")
        parser.add_argument(
            "--course-id",
            default=None,
            help=(
                "Default course ID for rows without a course column "
                "(e.g. course-v1:OpenedX+DemoX+DemoCourse)"
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report without creating users, enrolling, or emailing",
        )
        parser.add_argument(
            "--no-reset-email",
            action="store_true",
            help="Create/enroll students but do not send password-reset emails",
        )
        parser.add_argument(
            "--resend-existing",
            action="store_true",
            help="Also send password-reset emails to users that already exist",
        )
        parser.add_argument(
            "--no-enroll-existing",
            action="store_true",
            help="Do not enroll users that already exist (only enroll newly created)",
        )
        parser.add_argument(
            "--mode",
            default=None,
            help="Enrollment mode (default: platform default, usually 'audit')",
        )
        parser.add_argument(
            "--email-delay",
            type=float,
            default=None,
            help="Seconds to wait between password-reset emails",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        try:
            summary = import_users_from_csv(
                csv_path,
                default_course_id=options["course_id"],
                send_reset=not options["no_reset_email"],
                resend_existing=options["resend_existing"],
                skip_existing=not options["resend_existing"],
                enroll_existing=not options["no_enroll_existing"],
                dry_run=options["dry_run"],
                email_delay=options["email_delay"],
                enrollment_mode=options["mode"],
            )
        except FileNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        save_import_batch(
            summary,
            source_filename=csv_path,
            notes="management command import_users_csv",
        )

        self.stdout.write(self.style.SUCCESS("CSV student import complete"))
        for key, value in summary.as_dict().items():
            self.stdout.write(f"  {key}: {value}")

        for row in summary.rows:
            course_bit = f" [{row.course_ids}]" if row.course_ids else ""
            self.stdout.write(
                f"  - {row.email or '(n/a)'}: {row.status}{course_bit}"
                + (f" ({row.detail})" if row.detail else "")
            )

        if summary.errors or summary.reset_failed or summary.enrollment_failed:
            raise CommandError(
                f"Import finished with errors={summary.errors}, "
                f"reset_failed={summary.reset_failed}, "
                f"enrollment_failed={summary.enrollment_failed}"
            )
