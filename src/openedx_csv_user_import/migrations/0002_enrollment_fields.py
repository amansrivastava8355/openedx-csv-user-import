# Generated for openedx-csv-user-import 0.2.0 — add course enrollment audit fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("openedx_csv_user_import", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="csvimportbatch",
            name="already_enrolled_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="csvimportbatch",
            name="enrolled_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="csvimportbatch",
            name="enrollment_failed_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="csvimportrow",
            name="course_ids",
            field=models.CharField(blank=True, max_length=1024),
        ),
        migrations.AlterField(
            model_name="csvimportrow",
            name="detail",
            field=models.CharField(blank=True, max_length=1024),
        ),
        migrations.AlterField(
            model_name="csvimportrow",
            name="status",
            field=models.CharField(max_length=128),
        ),
    ]
