"""Tutor plugin: install and wire openedx-csv-user-import into Open edX."""

from __future__ import annotations

import click
from tutor import hooks

from .__about__ import __version__

hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        ("CSV_USER_IMPORT_VERSION", __version__),
    ]
)

hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-dockerfile-post-python-requirements",
        """
# openedx-csv-user-import — bulk create students from CSV, enroll, password-reset
RUN if [ -d /mnt/openedx-csv-user-import ]; then \
      pip install --no-cache-dir /mnt/openedx-csv-user-import ; \
      if [ -d /mnt/openedx-csv-user-import/email_overrides/user_authn/edx_ace ]; then \
        cp -a /mnt/openedx-csv-user-import/email_overrides/user_authn/edx_ace/. \
          /openedx/edx-platform/openedx/core/djangoapps/user_authn/templates/user_authn/edx_ace/ ; \
      fi ; \
    fi
""",
    )
)

hooks.Filters.MOUNTED_DIRECTORIES.add_item(("openedx", "openedx-csv-user-import"))


@click.command(
    name="import-users-csv",
    help="Import Open edX students from CSV (create + optional course enroll + password reset)",
)
@click.argument("csv_path")
@click.option(
    "--course-id",
    default=None,
    help="Default course ID when CSV rows omit course_id",
)
@click.option("--dry-run", is_flag=True, help="Validate only; do not write or email")
@click.option("--no-reset-email", is_flag=True, help="Do not send password-reset emails")
@click.option(
    "--resend-existing",
    is_flag=True,
    help="Also send password-reset emails to users that already exist",
)
@click.option(
    "--no-enroll-existing",
    is_flag=True,
    help="Do not enroll users that already exist",
)
@click.option(
    "--email-delay",
    type=float,
    default=None,
    help="Seconds to wait between password-reset emails",
)
def import_users_csv_job(
    csv_path: str,
    course_id,
    dry_run: bool,
    no_reset_email: bool,
    resend_existing: bool,
    no_enroll_existing: bool,
    email_delay,
):
    """
    Run the Django management command inside the LMS container.

    Example::

        docker cp students.csv tutor_local-lms-1:/tmp/students.csv
        tutor local do import-users-csv /tmp/students.csv \\
            --course-id course-v1:OpenedX+DemoX+DemoCourse
    """
    flags = []
    if course_id:
        flags.append(f"--course-id {course_id}")
    if dry_run:
        flags.append("--dry-run")
    if no_reset_email:
        flags.append("--no-reset-email")
    if resend_existing:
        flags.append("--resend-existing")
    if no_enroll_existing:
        flags.append("--no-enroll-existing")
    if email_delay is not None:
        flags.append(f"--email-delay {email_delay}")
    flag_str = " ".join(flags)
    yield (
        "lms",
        f"./manage.py lms migrate openedx_csv_user_import --noinput\n"
        f"./manage.py lms import_users_csv {csv_path} {flag_str}\n",
    )


hooks.Filters.CLI_DO_COMMANDS.add_item(import_users_csv_job)
