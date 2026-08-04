"""Settings helpers for the CSV user import plugin."""


def plugin_settings(settings):
    """Apply plugin defaults onto the Open edX settings object."""
    settings.CSV_USER_IMPORT_ENABLED = getattr(settings, "CSV_USER_IMPORT_ENABLED", True)
    # Max rows processed in a single upload / command run (safety for universities).
    settings.CSV_USER_IMPORT_MAX_ROWS = getattr(settings, "CSV_USER_IMPORT_MAX_ROWS", 5000)
    # Delay between password-reset emails to reduce SMTP rate-limit risk.
    settings.CSV_USER_IMPORT_EMAIL_DELAY_SECONDS = getattr(
        settings, "CSV_USER_IMPORT_EMAIL_DELAY_SECONDS", 0.25
    )
