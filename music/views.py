from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .forms import PlaylistImportForm
from .models import PlaylistImport
from .tasks import import_playlist


@staff_member_required
def index(request):
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
