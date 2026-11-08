import re
import time
from pathlib import Path

from django.conf import settings
from django.tasks import task
from yt_dlp import YoutubeDL, parse_options

from .models import Author, Collection, PlaylistImport, Song

THUMBNAIL_EXTS = (".jpg", ".png", ".webp")


def _download_opts(progress_hook):
    # Same as the CLI command, but per-video (DB acts as the download archive) into MEDIA_ROOT/songs.
    opts = parse_options([
        "--ignore-config",
        "-x", "--audio-format", "mp3", "--audio-quality", "0",
        "--embed-thumbnail", "--embed-metadata",
        "--write-thumbnail", "--convert-thumbnails", "jpg",
        "--no-playlist", "--quiet", "--no-warnings", "--no-progress",
        "-P", str(Path(settings.MEDIA_ROOT) / "songs"),
        "-o", "%(title)s [%(id)s].%(ext)s",
    ]).ydl_opts
    opts["progress_hooks"] = [progress_hook]
    return opts


def _guess_artist_and_title(info):
    title = info.get("track") or info.get("title") or info["id"]
    artists = info.get("artists") or ([info["artist"]] if info.get("artist") else [])
    if artists:
        return artists[0], title
    if not info.get("track") and " - " in title:
        artist, _, rest = title.partition(" - ")
        return artist.strip(), rest.strip()
    channel = info.get("channel") or info.get("uploader") or ""
    # YouTube Music auto-generated channels are named "<Artist> - Topic"
    return re.sub(r"\s*-\s*Topic$", "", channel) or None, title


def _save(job, *fields):
    job.save(update_fields=[*fields, "modified_at"])


def _download_song(job, url):
    last_update = 0.0

    def hook(d):
        nonlocal last_update
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        now = time.monotonic()
        if d["status"] != "downloading" or not total or now - last_update < 0.5:
            return
        last_update = now
        job.current_percent = min(100, int(d.get("downloaded_bytes", 0) * 100 / total))
        _save(job, "current_percent")

    with YoutubeDL(_download_opts(hook)) as ydl:
        info = ydl.extract_info(url, download=True)

    media_root = Path(settings.MEDIA_ROOT).resolve()
    audio_path = Path(info["requested_downloads"][0]["filepath"]).resolve()
    thumbnail_path = next(
        (p for ext in THUMBNAIL_EXTS if (p := audio_path.with_suffix(ext)).exists()), None
    )

    artist_name, name = _guess_artist_and_title(info)
    author = None
    if artist_name:
        author = Author.objects.filter(name=artist_name).first() or Author.objects.create(
            name=artist_name
        )

    return Song.objects.create(
        name=name[:255],
        author=author,
        youtube_id=info["id"],
        audio_file=audio_path.relative_to(media_root).as_posix(),
        thumbnail=thumbnail_path.relative_to(media_root).as_posix() if thumbnail_path else "",
    )


def _import_entry(job, collection, entry):
    video_id = entry.get("id")
    job.current_title = (entry.get("title") or video_id or "")[:255]
    job.current_percent = 0
    _save(job, "current_title", "current_percent")

    song = Song.objects.filter(youtube_id=video_id).first() if video_id else None
    if song is None:
        try:
            song = _download_song(job, entry.get("webpage_url") or entry.get("url") or video_id)
        except Exception as exc:
            job.failed += 1
            job.log += f"{job.current_title}: {exc}\n"
    if song:
        collection.songs.add(song)
    job.processed += 1
    _save(job, "processed", "failed", "log")


@task()
def import_playlist(import_id: int):
    job = PlaylistImport.objects.get(pk=import_id)
    job.status = PlaylistImport.Status.RUNNING
    _save(job, "status")
    try:
        with YoutubeDL({"extract_flat": "in_playlist", "quiet": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(job.url, download=False)
        # A plain video URL has no entries; treat it as a one-song playlist.
        entries = [e for e in info.get("entries") or [info] if e]
        title = (info.get("title") or job.url)[:255]
        collection = Collection.objects.filter(name=title).first() or Collection.objects.create(
            name=title
        )
        job.title, job.total, job.collection = title, len(entries), collection
        _save(job, "title", "total", "collection")

        for entry in entries:
            _import_entry(job, collection, entry)
        job.status = PlaylistImport.Status.DONE
    except Exception as exc:
        job.status = PlaylistImport.Status.FAILED
        job.log += f"{exc}\n"
    job.current_title = ""
    _save(job, "status", "log", "current_title")
