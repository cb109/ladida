from django.contrib import admin

from .models import Author, Collection, Song


class TimestampedAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "modified_at")
    search_fields = ("name",)
    readonly_fields = ("created_at", "modified_at")


@admin.register(Author)
class AuthorAdmin(TimestampedAdmin):
    pass


@admin.register(Song)
class SongAdmin(TimestampedAdmin):
    pass


@admin.register(Collection)
class CollectionAdmin(TimestampedAdmin):
    filter_horizontal = ("songs",)
