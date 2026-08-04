# Generated manually for openedx-csv-user-import 0.1.0

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CsvImportBatch",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("source_filename", models.CharField(blank=True, max_length=255)),
                ("dry_run", models.BooleanField(default=False)),
                ("created_count", models.PositiveIntegerField(default=0)),
                ("skipped_count", models.PositiveIntegerField(default=0)),
                ("reset_sent_count", models.PositiveIntegerField(default=0)),
                ("reset_failed_count", models.PositiveIntegerField(default=0)),
                ("invalid_count", models.PositiveIntegerField(default=0)),
                ("error_count", models.PositiveIntegerField(default=0)),
                ("notes", models.TextField(blank=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="csv_import_batches",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "CSV import batch",
                "verbose_name_plural": "CSV import batches",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CsvImportRow",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("email", models.EmailField(db_index=True, max_length=254)),
                ("username", models.CharField(blank=True, max_length=150)),
                ("status", models.CharField(max_length=64)),
                ("detail", models.CharField(blank=True, max_length=512)),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rows",
                        to="openedx_csv_user_import.csvimportbatch",
                    ),
                ),
            ],
            options={
                "ordering": ["id"],
            },
        ),
    ]
