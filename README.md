# openedx-csv-user-import

Bulk-create Open edX **students** from a CSV, optionally **enroll them in courses**, and send each new student a **password-reset email**.

This repository contains:

| Piece | Purpose |
|---|---|
| Django app (`openedx_csv_user_import`) | Runs inside LMS: import logic, staff UI, management command |
| Tutor plugin (`csv-user-import`) | Installs/wires the Django app into a Tutor deployment |

Compatible with **Tutor 18+** (tested on Tutor 21 / Ulmo).

---

## Features

- CSV with `email` and optional `course_id` / `course` column
- Creates active student accounts
- Enrolls students into one or more courses
- Sends Open edX password-reset email so students set their own password
- Existing users are not recreated (still enrolled by default)
- Dry-run mode
- Staff web UI + CLI + `tutor local do` job
- Import audit history in Django admin / UI

---

## Prerequisites

1. A working Tutor Open edX instance (`tutor local start` / `launch`)
2. Staff or superuser account for the web UI
3. SMTP configured (required for password-reset emails)

```bash
tutor --version
tutor local status
```

---

## Installation steps

Replace `/path/to/openedx-csv-user-import` with the real path on your server  
(example on this machine: `/home/vagrant/openedx/tutor/openedx-csv-user-import`).

### Option A — Recommended for production / rebuild (mount + image build)

#### 1. Install the Tutor plugin on the host

Use the **same Python environment** where Tutor is installed:

```bash
pip install -e /path/to/openedx-csv-user-import
```

Or from Git (when published):

```bash
pip install "git+https://github.com/YOUR_ORG/openedx-csv-user-import.git"
```

#### 2. Enable the plugin

```bash
tutor plugins enable csv-user-import
tutor plugins list
```

You should see:

```text
csv-user-import   ✅ enabled   0.2.0
```

#### 3. Mount the package and add it to the Open edX image

```bash
tutor mounts add /path/to/openedx-csv-user-import
tutor config save --append \
  OPENEDX_EXTRA_PIP_REQUIREMENTS=/mnt/openedx-csv-user-import
tutor config save
```

From Git instead of a local mount:

```bash
tutor config save --append \
  OPENEDX_EXTRA_PIP_REQUIREMENTS=git+https://github.com/YOUR_ORG/openedx-csv-user-import.git
tutor config save
```

#### 4. Rebuild and restart

```bash
tutor images build openedx
tutor local start -d
```

#### 5. Run database migrations

```bash
tutor local run lms ./manage.py lms migrate openedx_csv_user_import --noinput
```

#### 6. Verify

```bash
# Management command help
tutor local run lms ./manage.py lms help import_users_csv

# Tutor job available?
tutor local do --help | grep import-users-csv
```

Open the staff UI (sign in as staff first):

```text
http://<LMS_HOST>/csv-user-import/
```

Example: `http://local.edly.io/csv-user-import/`

---

### Option B — Fast path (already-running LMS, no image rebuild)

Useful for development or quick university testing.

```bash
# 1) Install Tutor plugin on host
pip install -e /path/to/openedx-csv-user-import
tutor plugins enable csv-user-import
tutor config save

# 2) Copy package into LMS container
docker cp /path/to/openedx-csv-user-import tutor_local-lms-1:/openedx/openedx-csv-user-import

# 3) Install inside LMS
docker exec -u 0 tutor_local-lms-1 bash -c \
  'source /openedx/venv/bin/activate && pip install -e /openedx/openedx-csv-user-import'

# 4) Migrate
docker exec tutor_local-lms-1 bash -c \
  'cd /openedx/edx-platform && ./manage.py lms migrate openedx_csv_user_import --noinput'

# 5) Restart LMS so the staff UI routes load
docker restart tutor_local-lms-1
```

> After LMS restart, wait ~30–60s, then open `/csv-user-import/`.

---

## CSV format

### Students + course enrollment (recommended)

```csv
email,course_id
alice.student@university.edu,course-v1:OpenedX+DemoX+DemoCourse
bob.student@university.edu,course-v1:OpenedX+DemoX+DemoCourse
```

### Multiple courses for one student

```csv
email,course_id
alice@university.edu,course-v1:Org+CourseA+2024;course-v1:Org+CourseB+2024
```

Or repeat the email on multiple rows (courses are merged).

### Email only

```csv
email
alice.student@university.edu
bob.student@university.edu
```

Then pass a default course:

```bash
tutor local do import-users-csv /tmp/students.csv \
  --course-id course-v1:OpenedX+DemoX+DemoCourse
```

Column aliases supported: `email`, `e-mail`, `mail` and `course_id`, `course`, `course_key`.

See also: [`examples/users.csv`](examples/users.csv).

---

## How to use

### 1) Staff web UI

1. Sign in to the LMS as a **staff** / admin user  
2. Open `http://<LMS_HOST>/csv-user-import/`  
3. Choose CSV file  
4. Optionally set **Default course ID**  
5. Choose options (send reset email, enroll existing users, dry run)  
6. Click **Import students** (a loader is shown while import runs)

### 2) Tutor job

Copy the CSV into the LMS container, then run:

```bash
docker cp students.csv tutor_local-lms-1:/tmp/students.csv

tutor local do import-users-csv /tmp/students.csv
tutor local do import-users-csv /tmp/students.csv --dry-run
tutor local do import-users-csv /tmp/students.csv \
  --course-id course-v1:OpenedX+DemoX+DemoCourse
```

### 3) Django management command

```bash
tutor local run lms ./manage.py lms import_users_csv /tmp/students.csv
tutor local run lms ./manage.py lms import_users_csv /tmp/students.csv --dry-run
tutor local run lms ./manage.py lms import_users_csv /tmp/students.csv --no-reset-email
tutor local run lms ./manage.py lms import_users_csv /tmp/students.csv --resend-existing
tutor local run lms ./manage.py lms import_users_csv /tmp/students.csv --no-enroll-existing
```

### Useful flags

| Flag | Meaning |
|---|---|
| `--dry-run` | Validate only; no create / enroll / email |
| `--course-id` | Default course when CSV has no course column |
| `--no-reset-email` | Create/enroll without sending password-reset mail |
| `--resend-existing` | Also send password-reset to existing users |
| `--no-enroll-existing` | Only enroll newly created users |
| `--email-delay` | Seconds between password-reset emails |

---

## What happens for each student

1. Create account (if email is new) with a random unknown password  
2. Send password-reset email (new students, unless disabled)  
3. Enroll into listed course(s)  
4. Existing emails are skipped for account creation, but still enrolled by default  

---

## SMTP (required for password-reset emails)

Configure Tutor SMTP before bulk importing real students:

```bash
tutor config save \
  --set RUN_SMTP=false \
  --set SMTP_HOST=mail.example.com \
  --set SMTP_PORT=587 \
  --set SMTP_USE_TLS=true \
  --set SMTP_USE_SSL=false \
  --set SMTP_USERNAME=noreply@example.com \
  --set SMTP_PASSWORD='YOUR_PASSWORD' \
  --set CONTACT_EMAIL=noreply@example.com

tutor local start -d
```

Test:

```bash
tutor local run lms ./manage.py lms shell -c "
from django.core.mail import send_mail
from django.conf import settings
print(send_mail('SMTP test', 'Hello', settings.DEFAULT_FROM_EMAIL, ['you@example.com']))
"
```

---

## Optional LMS settings

| Setting | Default | Purpose |
|---|---|---|
| `CSV_USER_IMPORT_ENABLED` | `True` | Feature flag |
| `CSV_USER_IMPORT_MAX_ROWS` | `5000` | Safety cap per import |
| `CSV_USER_IMPORT_EMAIL_DELAY_SECONDS` | `0.25` | Delay between reset emails |

---

## Uninstall

```bash
tutor plugins disable csv-user-import
tutor config save
# Remove from OPENEDX_EXTRA_PIP_REQUIREMENTS in config.yml if present
tutor images build openedx
tutor local start -d
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `csv-user-import` not in `tutor plugins list` | Install with the same `pip`/venv that provides `tutor` |
| UI 404 on `/csv-user-import/` | Plugin not installed in LMS image/container; rebuild or use Option B + restart LMS |
| Password-reset emails not received | Check SMTP settings; test with `send_mail` above |
| `course not found` during enroll | Use a real course id, e.g. `course-v1:OpenedX+DemoX+DemoCourse` |
| Apache/default page instead of LMS/Studio | Ensure Windows hosts maps `local.edly.io` / `studio.local.edly.io` to `127.0.0.1` and Tutor Caddy owns port 80 |

---

## Development / tests

```bash
pip install -e ".[dev]"
pytest src/openedx_csv_user_import/tests/test_services_unit.py -q
```

---

## License

AGPL-3.0-only
