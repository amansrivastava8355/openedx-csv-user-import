# Quick install (checklist)

Use this short checklist on a working Tutor instance (staging or prod).

## Important

`tutor plugins enable csv-user-import` on the **host is not enough**.

You must also install the Django package **inside the LMS container**, or bake it
into the Open edX image. Otherwise `/csv-user-import/` returns **Page not found**.

## Path on the server

```text
/path/to/openedx-csv-user-import
```

Examples: `/root/openedx-csv-user-import` (staging/prod) or a local clone path.

---

## Production (recommended): bake into image

```bash
pip install -e /path/to/openedx-csv-user-import
tutor plugins enable csv-user-import
tutor mounts add /path/to/openedx-csv-user-import
tutor config save

tutor images build openedx
tutor local start -d

tutor local run lms ./manage.py lms migrate openedx_csv_user_import --noinput

# Verify Django app is inside LMS
tutor local run lms bash -c \
  'source /openedx/venv/bin/activate && pip show openedx-csv-user-import'
tutor local run lms ./manage.py lms shell -c \
  'from django.urls import reverse; print(reverse("csv_user_import:import"))'
```

Expected: prints `/csv-user-import/`

---

## Fast install (no image rebuild) — staging / quick fix

```bash
# Host Tutor
pip install -e /path/to/openedx-csv-user-import
tutor plugins enable csv-user-import
tutor mounts add /path/to/openedx-csv-user-import
tutor config save
tutor local start -d

# Install INSIDE LMS / CMS / workers (required for UI)
for c in tutor_local-lms-1 tutor_local-cms-1 \
         tutor_local-lms-worker-1 tutor_local-cms-worker-1; do
  docker exec -u 0 "$c" bash -c \
    'source /openedx/venv/bin/activate && pip install -e /mnt/openedx-csv-user-import'
done

docker exec tutor_local-lms-1 bash -c \
  'cd /openedx/edx-platform && ./manage.py lms migrate openedx_csv_user_import --noinput'

docker restart tutor_local-lms-1 tutor_local-cms-1 \
  tutor_local-lms-worker-1 tutor_local-cms-worker-1
```

> Fast install is lost if containers are recreated from an image that was not rebuilt.
> For prod, always finish with the **bake into image** steps above.

---

## Open UI

1. Login as staff on the LMS host
2. Open: `https://<LMS_HOST>/csv-user-import/`

If you see Open edX “Page not found”, the Django app is still missing inside LMS —
re-run the `pip install` + restart steps (or rebuild the image).

---

## Import via CLI

```bash
docker cp students.csv tutor_local-lms-1:/tmp/students.csv
tutor local do import-users-csv /tmp/students.csv --dry-run
tutor local do import-users-csv /tmp/students.csv
```

## CSV example

```csv
email,course_id
student1@university.edu,course-v1:OpenedX+DemoX+DemoCourse
student2@university.edu,course-v1:OpenedX+DemoX+DemoCourse
```

Full details: see [README.md](../README.md).
