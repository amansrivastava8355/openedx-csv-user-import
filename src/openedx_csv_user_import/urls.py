"""URL routes for CSV user import."""

from django.urls import path

from openedx_csv_user_import import views

app_name = "csv_user_import"

urlpatterns = [
    path("", views.import_csv_view, name="import"),
]
