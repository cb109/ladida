from django.urls import path

from . import views

app_name = "music"

urlpatterns = [
    path("", views.song_list, name="song_list"),
    path("songs/<int:pk>/", views.song_detail, name="song_detail"),
    path("songs/<int:pk>/collections/add/", views.song_collection_add, name="song_collection_add"),
    path(
        "songs/<int:pk>/collections/<int:collection_pk>/remove/",
        views.song_collection_remove,
        name="song_collection_remove",
    ),
    path("collections/", views.collection_list, name="collection_list"),
    path("collections/new/", views.collection_form, name="collection_create"),
    path("collections/<int:pk>/edit/", views.collection_form, name="collection_edit"),
    path("collections/<int:pk>/delete/", views.collection_delete, name="collection_delete"),
    path("import/", views.import_page, name="import_page"),
    path("imports/", views.import_create, name="import_create"),
    path("imports/<int:pk>/", views.import_progress, name="import_progress"),
]
