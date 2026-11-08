from django.urls import path

from . import views

app_name = "music"

urlpatterns = [
    path("", views.index, name="index"),
    path("imports/", views.import_create, name="import_create"),
    path("imports/<int:pk>/", views.import_progress, name="import_progress"),
]
