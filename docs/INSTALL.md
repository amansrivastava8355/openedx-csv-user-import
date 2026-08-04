# Quick install (checklist)

Use this short checklist on a working Tutor instance.

## Path on this server

```text
/home/vagrant/openedx/tutor/openedx-csv-user-import
```

## Fast install (no image rebuild)

```bash
# Host Tutor venv
pip install -e /home/vagrant/openedx/tutor/openedx-csv-user-import
tutor plugins enable csv-user-import
tutor config save

docker cp /home/vagrant/openedx/tutor/openedx-csv-user-import \
  tutor_local-lms-1:/openedx/openedx-csv-user-import

docker exec -u 0 tutor_local-lms-1 bash -c \
  'source /openedx/venv/bin/activate && pip install -e /openedx/openedx-csv-user-import'

docker exec tutor_local-lms-1 bash -c \
  'cd /openedx/edx-platform && ./manage.py lms migrate openedx_csv_user_import --noinput'

docker restart tutor_local-lms-1
```

## Open UI

1. Login as staff: `http://local.edly.io/login`
2. Open: `http://local.edly.io/csv-user-import/`

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
