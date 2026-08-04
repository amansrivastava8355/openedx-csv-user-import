"""Core CSV parsing, student creation, enrollment, and password-reset logic."""

from __future__ import annotations

import csv
import io
import logging
import re
import time
from dataclasses import dataclass, field
from typing import BinaryIO, Iterable, Iterator, Optional, TextIO, Union

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

logger = logging.getLogger(__name__)

USERNAME_MAX_LENGTH = 30
USERNAME_SAFE_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
EMAIL_HEADER_ALIASES = ("email", "e-mail", "mail", "email_address", "emailaddress")
COURSE_HEADER_ALIASES = (
    "course",
    "course_id",
    "courseid",
    "course_key",
    "coursekey",
    "course_ids",
)
# Split multiple course IDs in one cell (comma is also allowed; course keys rarely contain commas).
COURSE_ID_SPLIT_RE = re.compile(r"[;|\n]+")


@dataclass
class CsvStudentRecord:
    """One logical student from the CSV (email + optional course IDs)."""

    email: str
    course_ids: list[str] = field(default_factory=list)


@dataclass
class ImportRowResult:
    """Outcome for a single student import."""

    email: str
    status: str
    username: str = ""
    detail: str = ""
    course_ids: str = ""


@dataclass
class ImportSummary:
    """Aggregate result of an import run."""

    created: int = 0
    skipped_existing: int = 0
    reset_sent: int = 0
    reset_failed: int = 0
    enrolled: int = 0
    enrollment_failed: int = 0
    already_enrolled: int = 0
    invalid: int = 0
    errors: int = 0
    dry_run: bool = False
    rows: list[ImportRowResult] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "created": self.created,
            "skipped_existing": self.skipped_existing,
            "reset_sent": self.reset_sent,
            "reset_failed": self.reset_failed,
            "enrolled": self.enrolled,
            "enrollment_failed": self.enrollment_failed,
            "already_enrolled": self.already_enrolled,
            "invalid": self.invalid,
            "errors": self.errors,
            "dry_run": self.dry_run,
            "total_rows": len(self.rows),
        }


def normalize_email(raw: str) -> str:
    """Strip and lowercase an email address."""
    return (raw or "").strip().lower()


def is_valid_email(email: str) -> bool:
    """Return True if email passes Django's email validator."""
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False


def parse_course_ids(raw: str) -> list[str]:
    """
    Split a course cell into unique course IDs.

    Accepts separators: ``;`` ``|`` or newline. A single course ID is returned as-is.
    """
    text = (raw or "").strip()
    if not text:
        return []
    parts = COURSE_ID_SPLIT_RE.split(text) if COURSE_ID_SPLIT_RE.search(text) else [text]
    # Also allow comma-separated lists of course-v1 keys
    expanded: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "," in part and "course-v1:" in part:
            expanded.extend(p.strip() for p in part.split(",") if p.strip())
        else:
            expanded.append(part)
    # Preserve order, drop duplicates
    seen: set[str] = set()
    result: list[str] = []
    for course_id in expanded:
        if course_id not in seen:
            seen.add(course_id)
            result.append(course_id)
    return result


def username_from_email(email: str) -> str:
    """
    Derive a Django username from the email local-part.

    Open edX usernames are limited to 30 characters and a restricted charset.
    """
    local = email.split("@", 1)[0]
    local = USERNAME_SAFE_RE.sub("", local).strip("._-")
    if not local:
        local = "user"
    return local[:USERNAME_MAX_LENGTH]


def unique_username_for_email(email: str) -> str:
    """Return a username that does not collide with an existing account."""
    user_model = get_user_model()
    base = username_from_email(email)
    candidate = base
    counter = 1
    while user_model.objects.filter(username=candidate).exists():
        suffix = str(counter)
        candidate = f"{base[: USERNAME_MAX_LENGTH - len(suffix)]}{suffix}"
        counter += 1
        if counter > 9999:
            raise RuntimeError(f"Unable to allocate unique username for {email}")
    return candidate


def _as_text_stream(source: Union[str, TextIO, BinaryIO, bytes]) -> io.StringIO:
    """Normalize path / file / bytes into a seekable text stream."""
    if isinstance(source, str):
        with open(source, newline="", encoding="utf-8-sig") as handle:
            return io.StringIO(handle.read())
    if isinstance(source, bytes):
        return io.StringIO(source.decode("utf-8-sig"))
    raw = source.read()
    if isinstance(raw, bytes):
        return io.StringIO(raw.decode("utf-8-sig"))
    return io.StringIO(raw)


def _find_column(header: list[str], aliases: tuple[str, ...]) -> Optional[int]:
    for alias in aliases:
        if alias in header:
            return header.index(alias)
    return None


def iter_student_records_from_csv(
    source: Union[str, TextIO, BinaryIO, bytes],
    email_column: str = "email",
    course_column: str = "course_id",
    default_course_id: Optional[str] = None,
) -> Iterator[CsvStudentRecord]:
    """
    Yield student records from a CSV.

    Supported shapes:
    - ``email`` only (optional ``default_course_id`` applied to every row)
    - ``email,course_id`` (or aliases ``course`` / ``course_key``)
    - Multiple course IDs in one cell separated by ``;`` or ``|``
    - Same email on multiple rows → later aggregated by the importer
    """
    stream = _as_text_stream(source)
    sample = stream.read(4096)
    stream.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample or "email,course_id\n", delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel

    rows = list(csv.reader(stream, dialect))
    if not rows:
        return

    header = [c.strip().lower() for c in rows[0]]
    email_aliases = (email_column.lower(), *EMAIL_HEADER_ALIASES)
    course_aliases = (course_column.lower(), *COURSE_HEADER_ALIASES)
    has_email_header = any(alias in header for alias in email_aliases)

    if has_email_header:
        email_idx = _find_column(header, email_aliases) or 0
        course_idx = _find_column(header, course_aliases)
        data_rows = rows[1:]
    else:
        email_idx = 0
        course_idx = 1 if len(rows[0]) > 1 else None
        data_rows = rows

    default_courses = parse_course_ids(default_course_id or "")

    for row in data_rows:
        if not row or email_idx >= len(row):
            continue
        email = normalize_email(row[email_idx])
        if not email:
            continue
        course_ids: list[str] = []
        if course_idx is not None and course_idx < len(row):
            course_ids = parse_course_ids(row[course_idx])
        if not course_ids and default_courses:
            course_ids = list(default_courses)
        yield CsvStudentRecord(email=email, course_ids=course_ids)


def iter_emails_from_csv(
    source: Union[str, TextIO, BinaryIO, bytes],
    email_column: str = "email",
) -> Iterator[str]:
    """Backward-compatible helper: yield emails only."""
    for record in iter_student_records_from_csv(source, email_column=email_column):
        yield record.email


def aggregate_student_records(
    records: Iterable[CsvStudentRecord],
) -> list[CsvStudentRecord]:
    """Merge duplicate emails and union their course IDs (order preserved)."""
    order: list[str] = []
    courses_by_email: dict[str, list[str]] = {}
    for record in records:
        email = normalize_email(record.email)
        if not email:
            continue
        if email not in courses_by_email:
            order.append(email)
            courses_by_email[email] = []
        for course_id in record.course_ids:
            if course_id not in courses_by_email[email]:
                courses_by_email[email].append(course_id)
    return [
        CsvStudentRecord(email=email, course_ids=courses_by_email[email]) for email in order
    ]


def build_password_reset_request(host: Optional[str] = None):
    """Build a minimal request for Open edX password-reset email templates."""
    from django.contrib.auth.models import AnonymousUser
    from django.contrib.sites.models import Site
    from django.test import RequestFactory

    site = Site.objects.get_current()
    hostname = host or site.domain or getattr(settings, "SITE_NAME", "localhost")
    factory = RequestFactory()
    request = factory.post("/password_reset/", {})
    request.META["HTTP_HOST"] = hostname
    request.META["SERVER_NAME"] = hostname
    request.site = site
    request.user = AnonymousUser()
    return request


def send_password_reset(user, request=None) -> None:
    """Send the platform password-reset email for ``user``."""
    import crum
    from openedx.core.djangoapps.user_authn.views.password_reset import (
        send_password_reset_email_for_user,
    )

    request = request or build_password_reset_request()
    crum.set_current_request(request)
    try:
        send_password_reset_email_for_user(user, request)
    finally:
        crum.set_current_request(None)


def create_user_from_email(email: str):
    """
    Create an active Open edX user for ``email`` with a random usable password.

    Uses ``manage_user`` so UserProfile side-effects match Tutor's createuser path.
    """
    from django.core.management import call_command
    from edx_django_utils.user import generate_password

    user_model = get_user_model()
    username = unique_username_for_email(email)
    call_command("manage_user", username, email)
    user = user_model.objects.get(username=username)
    if user.email.lower() != email.lower():
        raise RuntimeError(
            f"manage_user created/found username={username} with unexpected email={user.email}"
        )
    user.set_password(generate_password(length=25))
    user.is_active = True
    user.save(update_fields=["password", "is_active"])
    return user


def enroll_user_in_courses(
    user,
    course_ids: list[str],
    *,
    mode: Optional[str] = None,
) -> tuple[list[str], list[str], list[str]]:
    """
    Enroll ``user`` in each course ID.

    Returns ``(enrolled, already_enrolled, failed)`` lists of course ID strings.
    """
    from opaque_keys import InvalidKeyError
    from opaque_keys.edx.keys import CourseKey
    from common.djangoapps.course_modes.models import CourseMode
    from common.djangoapps.student.models import CourseEnrollment
    from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

    enrolled: list[str] = []
    already: list[str] = []
    failed: list[str] = []
    enrollment_mode = mode or getattr(CourseMode, "DEFAULT_MODE_SLUG", "audit")

    for raw_id in course_ids:
        try:
            course_key = CourseKey.from_string(raw_id)
        except InvalidKeyError:
            failed.append(f"{raw_id} (invalid course id)")
            continue

        if not CourseOverview.objects.filter(id=course_key).exists():
            failed.append(f"{raw_id} (course not found)")
            continue

        try:
            if CourseEnrollment.is_enrolled(user, course_key):
                already.append(raw_id)
                continue
            CourseEnrollment.enroll(user, course_key, mode=enrollment_mode)
            enrolled.append(raw_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Enrollment failed for %s in %s", user.email, raw_id)
            failed.append(f"{raw_id} ({exc})")

    return enrolled, already, failed


def import_students(
    records: Iterable[CsvStudentRecord],
    *,
    send_reset: bool = True,
    skip_existing: bool = True,
    resend_existing: bool = False,
    enroll_existing: bool = True,
    dry_run: bool = False,
    request=None,
    email_delay: Optional[float] = None,
    enrollment_mode: Optional[str] = None,
) -> ImportSummary:
    """
    Create students, optionally send password-reset mail, and enroll in courses.

    Existing users:
    - Skipped for account creation when ``skip_existing`` is True
    - Still enrolled when ``enroll_existing`` is True and course IDs are present
    - Password reset only when ``resend_existing`` is True
    """
    user_model = get_user_model()
    summary = ImportSummary(dry_run=dry_run)
    delay = (
        email_delay
        if email_delay is not None
        else float(getattr(settings, "CSV_USER_IMPORT_EMAIL_DELAY_SECONDS", 0.25))
    )
    max_rows = int(getattr(settings, "CSV_USER_IMPORT_MAX_ROWS", 5000))
    request = request or (None if dry_run else build_password_reset_request())
    students = aggregate_student_records(records)

    for index, student in enumerate(students, start=1):
        if index > max_rows:
            summary.rows.append(
                ImportRowResult(
                    email="",
                    status="error",
                    detail=f"Stopped: exceeded CSV_USER_IMPORT_MAX_ROWS ({max_rows})",
                )
            )
            summary.errors += 1
            break

        email = student.email
        course_ids = student.course_ids
        course_ids_str = ";".join(course_ids)

        if not is_valid_email(email):
            summary.invalid += 1
            summary.rows.append(
                ImportRowResult(
                    email=email,
                    status="invalid",
                    detail="invalid email",
                    course_ids=course_ids_str,
                )
            )
            continue

        existing = user_model.objects.filter(email__iexact=email).first()
        user = existing
        created_now = False
        status_parts: list[str] = []
        detail_parts: list[str] = []

        if existing:
            if skip_existing and not resend_existing and not (enroll_existing and course_ids):
                summary.skipped_existing += 1
                summary.rows.append(
                    ImportRowResult(
                        email=email,
                        status="skipped",
                        username=existing.username,
                        detail="user already exists",
                        course_ids=course_ids_str,
                    )
                )
                continue

            summary.skipped_existing += 1
            status_parts.append("exists")
            detail_parts.append("user already exists")

            if dry_run:
                if course_ids and enroll_existing:
                    status_parts.append("would_enroll")
                if resend_existing and send_reset:
                    status_parts.append("would_resend")
                summary.rows.append(
                    ImportRowResult(
                        email=email,
                        status="+".join(status_parts),
                        username=existing.username,
                        detail="; ".join(detail_parts),
                        course_ids=course_ids_str,
                    )
                )
                continue
        else:
            if dry_run:
                summary.created += 1
                status = "would_create"
                if course_ids:
                    status += "+would_enroll"
                summary.rows.append(
                    ImportRowResult(
                        email=email,
                        status=status,
                        username=username_from_email(email),
                        course_ids=course_ids_str,
                    )
                )
                continue

            try:
                user = create_user_from_email(email)
                created_now = True
                summary.created += 1
                status_parts.append("created")
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to create user for %s", email)
                summary.errors += 1
                summary.rows.append(
                    ImportRowResult(
                        email=email,
                        status="error",
                        detail=str(exc),
                        course_ids=course_ids_str,
                    )
                )
                continue

        assert user is not None

        # Password reset for new users (always when send_reset) or existing (resend_existing)
        should_reset = send_reset and (created_now or resend_existing)
        if should_reset and not dry_run:
            try:
                send_password_reset(user, request=request)
                summary.reset_sent += 1
                status_parts.append("reset_sent")
            except Exception as exc:  # noqa: BLE001
                logger.exception("Password reset failed for %s", email)
                summary.reset_failed += 1
                status_parts.append("reset_failed")
                detail_parts.append(str(exc))
            if delay:
                time.sleep(delay)

        # Course enrollment for new users, and for existing when enroll_existing
        should_enroll = bool(course_ids) and (created_now or enroll_existing)
        if should_enroll and not dry_run:
            enrolled, already, failed = enroll_user_in_courses(
                user, course_ids, mode=enrollment_mode
            )
            summary.enrolled += len(enrolled)
            summary.already_enrolled += len(already)
            summary.enrollment_failed += len(failed)
            if enrolled:
                status_parts.append("enrolled")
                detail_parts.append("enrolled=" + ",".join(enrolled))
            if already:
                status_parts.append("already_enrolled")
                detail_parts.append("already=" + ",".join(already))
            if failed:
                status_parts.append("enroll_failed")
                detail_parts.append("failed=" + ",".join(failed))

        summary.rows.append(
            ImportRowResult(
                email=email,
                status="+".join(status_parts) or "ok",
                username=user.username,
                detail="; ".join(detail_parts),
                course_ids=course_ids_str,
            )
        )

    return summary


def import_users_from_emails(
    emails: Iterable[str],
    **kwargs,
) -> ImportSummary:
    """Create users from a plain iterable of emails (no course column)."""
    records = [CsvStudentRecord(email=normalize_email(e)) for e in emails if e]
    return import_students(records, **kwargs)


def import_users_from_csv(
    source: Union[str, TextIO, BinaryIO, bytes],
    *,
    default_course_id: Optional[str] = None,
    **kwargs,
) -> ImportSummary:
    """Parse ``source`` as CSV and import students (create + optional enroll + reset)."""
    records = list(
        iter_student_records_from_csv(source, default_course_id=default_course_id)
    )
    return import_students(records, **kwargs)
