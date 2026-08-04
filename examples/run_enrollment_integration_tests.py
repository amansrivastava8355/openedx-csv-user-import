"""Integration tests for student create + course enrollment."""

from django.conf import settings

settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
settings.CSV_USER_IMPORT_EMAIL_DELAY_SECONDS = 0

from django.contrib.auth import get_user_model  # noqa: E402
from django.core import mail  # noqa: E402
from opaque_keys.edx.keys import CourseKey  # noqa: E402
from common.djangoapps.student.models import CourseEnrollment, UserProfile  # noqa: E402
from openedx_csv_user_import.services import import_users_from_csv  # noqa: E402

User = get_user_model()
COURSE_ID = "course-v1:OpenedX+DemoX+DemoCourse"
course_key = CourseKey.from_string(COURSE_ID)

emails = [
    "enroll.alice@example.com",
    "enroll.bob@example.com",
]
for email in emails:
    user = User.objects.filter(email__iexact=email).first()
    if user:
        CourseEnrollment.objects.filter(user=user, course_id=course_key).delete()
        user.delete()

csv_data = (
    "email,course_id\n"
    f"enroll.alice@example.com,{COURSE_ID}\n"
    f"enroll.bob@example.com,{COURSE_ID}\n"
    f"bad-email,{COURSE_ID}\n"
).encode()

summary = import_users_from_csv(csv_data, send_reset=True, email_delay=0)
print("SUMMARY", summary.as_dict())
for row in summary.rows:
    print("ROW", row.email, row.status, row.course_ids, row.detail)

assert summary.created == 2, summary
assert summary.enrolled == 2, summary
assert summary.invalid == 1
assert summary.reset_sent == 2
assert len(mail.outbox) == 2

for email in emails:
    user = User.objects.get(email__iexact=email)
    assert user.is_active
    assert user.has_usable_password()
    assert UserProfile.objects.filter(user=user).exists()
    assert CourseEnrollment.is_enrolled(user, course_key)
    print("ENROLLED_OK", user.username, email)

# Re-import should skip create but mark already enrolled
mail.outbox.clear()
summary2 = import_users_from_csv(csv_data, send_reset=True, email_delay=0)
assert summary2.created == 0
assert summary2.already_enrolled == 2
assert summary2.enrolled == 0
print("ALREADY_ENROLLED_OK", summary2.as_dict())

# Default course id path
User.objects.filter(email__iexact="enroll.cara@example.com").delete()
summary3 = import_users_from_csv(
    b"email\nenroll.cara@example.com\n",
    default_course_id=COURSE_ID,
    send_reset=False,
    email_delay=0,
)
assert summary3.created == 1
assert summary3.enrolled == 1
cara = User.objects.get(email="enroll.cara@example.com")
assert CourseEnrollment.is_enrolled(cara, course_key)
print("DEFAULT_COURSE_OK", cara.username)

print("ALL_ENROLLMENT_INTEGRATION_TESTS_PASSED")
