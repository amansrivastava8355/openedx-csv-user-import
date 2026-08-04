"""Integration test script executed inside the LMS container."""

from django.conf import settings

settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
settings.CSV_USER_IMPORT_EMAIL_DELAY_SECONDS = 0

from django.core import mail  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from common.djangoapps.student.models import UserProfile  # noqa: E402
from openedx_csv_user_import.services import import_users_from_csv  # noqa: E402

User = get_user_model()

for email in [
    "csv.alice@example.com",
    "csv.bob@example.com",
    "csv.carol+lab@example.com",
    "csv.dave@example.com",
    "other-dave@example.com",
]:
    User.objects.filter(email__iexact=email).delete()
User.objects.filter(username="csv.dave").delete()

csv_data = b"""email
csv.alice@example.com
csv.bob@example.com
not-an-email
csv.alice@example.com
csv.carol+lab@example.com
"""

summary = import_users_from_csv(csv_data, send_reset=True, email_delay=0)
print("SUMMARY", summary.as_dict())
for row in summary.rows:
    print("ROW", row.email, row.status, row.username, row.detail)

assert summary.created == 3, summary
assert summary.invalid == 1
assert summary.skipped_existing == 1
assert summary.reset_sent == 3, summary
assert summary.reset_failed == 0, summary
assert len(mail.outbox) == 3, len(mail.outbox)

for email in ["csv.alice@example.com", "csv.bob@example.com", "csv.carol+lab@example.com"]:
    u = User.objects.get(email__iexact=email)
    assert u.is_active
    assert u.has_usable_password()
    assert UserProfile.objects.filter(user=u).exists()
    print("USER_OK", u.username, u.email)

body = mail.outbox[0].body
alts = getattr(mail.outbox[0], "alternatives", None) or []
combined = body + str(alts)
assert (
    "password" in combined.lower()
    or "reset" in combined.lower()
    or "pwreset" in combined.lower()
    or "confirm" in combined.lower()
)
print("EMAIL_SUBJECT", mail.outbox[0].subject)
print("EMAIL_TO", mail.outbox[0].to)

mail.outbox.clear()
summary2 = import_users_from_csv(csv_data, send_reset=True, email_delay=0)
assert summary2.created == 0
assert summary2.skipped_existing >= 3
assert len(mail.outbox) == 0
print("SKIP_OK", summary2.as_dict())

summary3 = import_users_from_csv(
    b"email\ncsv.alice@example.com\n",
    send_reset=True,
    resend_existing=True,
    skip_existing=False,
    email_delay=0,
)
assert summary3.reset_sent == 1
assert len(mail.outbox) == 1
print("RESEND_OK", summary3.as_dict())

User.objects.create_user(
    username="csv.dave",
    email="other-dave@example.com",
    password="UnusedPass123!",
)
summary4 = import_users_from_csv(
    b"email\ncsv.dave@example.com\n",
    send_reset=True,
    email_delay=0,
)
assert summary4.created == 1
u = User.objects.get(email="csv.dave@example.com")
assert u.username != "csv.dave"
print("COLLISION_OK", u.username)

print("ALL_INTEGRATION_TESTS_PASSED")
