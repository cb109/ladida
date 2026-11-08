import hashlib
from pathlib import Path

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AddToCollectionForm, CollectionForm, PlaylistImportForm
from .models import Collection, PlaylistImport, Song
from .tasks import import_playlist

SONGS_PER_PAGE = 50
UI_DIRS = [Path(__file__).parent / "static", Path(__file__).parent / "templates"]


def _ui_version():
    digest = hashlib.sha256()
    for root in UI_DIRS:
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def service_worker(request):
    # The version changes whenever a template or static file changes, which makes
    # the browser install the new worker and drop the old UI cache.
    response = render(
        request, "music/sw.js", {"version": _ui_version()}, content_type="application/javascript"
    )
    response["Cache-Control"] = "no-cache"
    return response


def _is_htmx(request):
    return request.headers.get("HX-Request") == "true" and not request.headers.get(
        "HX-History-Restore-Request"
    )


@staff_member_required
def song_list(request):
    songs = Song.objects.select_related("author").prefetch_related(_collections_prefetch()).order_by("name")
    q = request.GET.get("q", "").strip()
    if q:
        songs = songs.filter(
            Q(name__icontains=q) | Q(author__name__icontains=q) | Q(collections__name__icontains=q)
        ).distinct()
    collection = None
    collection_id = request.GET.get("collection", "")
    if collection_id.isdigit():
        collection = get_object_or_404(Collection, pk=collection_id)
        songs = songs.filter(collections=collection)

    context = {
        "page": Paginator(songs, SONGS_PER_PAGE).get_page(request.GET.get("page")),
        "q": q,
        "collection": collection,
        "collections": Collection.objects.with_song_count().order_by("name"),
    }
    template = "music/_song_rows.html" if _is_htmx(request) else "music/song_list.html"
    return render(request, template, context)


def _collections_prefetch():
    return Prefetch("collections", queryset=Collection.objects.with_song_count())


def _song_collections_context(song):
    return {
        "song": song,
        "song_collections": song.collections.with_song_count().order_by("name"),
        "other_collections": Collection.objects.with_song_count().exclude(songs=song).order_by("name"),
    }


@staff_member_required
def song_detail(request, pk):
    song = get_object_or_404(Song.objects.select_related("author"), pk=pk)
    in_dialog = _is_htmx(request)
    template = "music/_song_panel.html" if in_dialog else "music/song_detail.html"
    return render(request, template, {**_song_collections_context(song), "in_dialog": in_dialog})


def _render_song_collections(request, song):
    song = Song.objects.select_related("author").prefetch_related(_collections_prefetch()).get(pk=song.pk)
    return render(
        request, "music/_song_collections_response.html", _song_collections_context(song)
    )


@staff_member_required
@require_POST
def song_collection_add(request, pk):
    song = get_object_or_404(Song, pk=pk)
    form = AddToCollectionForm(request.POST)
    if form.is_valid():
        form.cleaned_data["collection"].songs.add(song)
    return _render_song_collections(request, song)


@staff_member_required
@require_POST
def song_collection_remove(request, pk, collection_pk):
    song = get_object_or_404(Song, pk=pk)
    get_object_or_404(Collection, pk=collection_pk).songs.remove(song)
    return _render_song_collections(request, song)


@staff_member_required
def collection_list(request):
    collections = Collection.objects.with_song_count().order_by("name")
    return render(request, "music/collection_list.html", {"collections": collections})


@staff_member_required
def collection_form(request, pk=None):
    collection = get_object_or_404(Collection.objects.with_song_count(), pk=pk) if pk else None
    form = CollectionForm(request.POST or None, instance=collection)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("music:collection_list")
    return render(request, "music/collection_form.html", {"form": form, "collection": collection})


@staff_member_required
def collection_player(request, pk):
    collection = get_object_or_404(Collection.objects.with_song_count(), pk=pk)
    # Through-table pk order == order the songs were added (playlist order for imports).
    entries = (
        Collection.songs.through.objects.filter(collection=collection)
        .select_related("song__author")
        .order_by("pk")
    )
    tracks = [
        {
            "name": e.song.name,
            "artist": e.song.author.name if e.song.author else "",
            "audio": e.song.audio_file.url,
            "thumbnail": e.song.thumbnail.url if e.song.thumbnail else "",
        }
        for e in entries
    ]
    return render(request, "music/collection_player.html", {"collection": collection, "tracks": tracks})


@staff_member_required
def collection_delete(request, pk):
    collection = get_object_or_404(Collection.objects.with_song_count(), pk=pk)
    if request.method == "POST":
        collection.delete()
        return redirect("music:collection_list")
    return render(request, "music/collection_confirm_delete.html", {"collection": collection})


@staff_member_required
def import_page(request):
    return render(
        request,
        "music/index.html",
        {
            "form": PlaylistImportForm(),
            "imports": PlaylistImport.objects.select_related("collection")[:20],
        },
    )


@staff_member_required
@require_POST
def import_create(request):
    form = PlaylistImportForm(request.POST)
    job = None
    if form.is_valid():
        job = form.save()
        import_playlist.enqueue(job.pk)
        form = PlaylistImportForm()
    return render(request, "music/_import_form.html", {"form": form, "new_import": job})


@staff_member_required
def import_progress(request, pk):
    job = get_object_or_404(PlaylistImport.objects.select_related("collection"), pk=pk)
    return render(request, "music/_import.html", {"job": job})
