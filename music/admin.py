from django.contrib import admin

from .models import Author, Collection, PlaylistImport, Song


class TimestampedAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "modified_at")
    search_fields = ("name",)
    readonly_fields = ("created_at", "modified_at")


@admin.register(Author)
class AuthorAdmin(TimestampedAdmin):
    pass


@admin.register(Song)
class SongAdmin(TimestampedAdmin):
    list_display = ("name", "author", "created_at", "modified_at")
    list_select_related = ("author",)
    search_fields = ("name", "author__name")


@admin.register(Collection)
class CollectionAdmin(TimestampedAdmin):
    filter_horizontal = ("songs",)


@admin.register(PlaylistImport)
class PlaylistImportAdmin(admin.ModelAdmin):
    list_display = ("__str__", "status", "processed", "total", "failed", "created_at")
    list_filter = ("status",)
    readonly_fields = ("created_at", "modified_at")
