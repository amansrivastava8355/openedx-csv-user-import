"""Django app configuration for CSV user import."""

from django.apps import AppConfig


class CsvUserImportConfig(AppConfig):
    """Register the app as an Open edX LMS/CMS plugin."""

    name = "openedx_csv_user_import"
    verbose_name = "CSV User Import"
    default_auto_field = "django.db.models.BigAutoField"

    plugin_app = {
        "url_config": {
            "lms.djangoapp": {
                "namespace": "csv_user_import",
                "regex": r"^csv-user-import/",
                "relative_path": "urls",
            },
        },
        "settings_config": {
            "lms.djangoapp": {
                "common": {"relative_path": "settings.common"},
                "production": {"relative_path": "settings.production"},
            },
            "cms.djangoapp": {
                "common": {"relative_path": "settings.common"},
                "production": {"relative_path": "settings.production"},
            },
        },
    }

    def ready(self):
        """Import signal handlers when Django starts."""
        # noqa: F401 — import for side effects if/when signals are added
        pass
