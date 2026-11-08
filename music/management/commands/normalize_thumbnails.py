from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from music.models import Song
from music.thumbnails import normalize_thumbnail


class Command(BaseCommand):
    help = "Shrink existing song thumbnails to fit 480x360 and store them as JPEG."

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT).resolve()
        done = 0
        for song in Song.objects.exclude(thumbnail=""):
            path = Path(song.thumbnail.path)
            if not path.exists():
                self.stderr.write(f"Missing: {path}")
                continue
            new_path = normalize_thumbnail(path)
            if new_path != path:
                song.thumbnail.name = new_path.relative_to(media_root).as_posix()
                song.save(update_fields=["thumbnail", "modified_at"])
            done += 1
        self.stdout.write(self.style.SUCCESS(f"Normalized {done} thumbnails."))
