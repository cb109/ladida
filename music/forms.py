from urllib.parse import urlparse

from django import forms

from .models import Collection, PlaylistImport, Song

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}


class PlaylistImportForm(forms.ModelForm):
    class Meta:
        model = PlaylistImport
        fields = ["url"]

    def clean_url(self):
        url = self.cleaned_data["url"]
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or (parsed.hostname or "").lower() not in YOUTUBE_HOSTS:
            raise forms.ValidationError("Please enter a YouTube URL.")
        return url


class SongChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, song):
        return f"{song.name} — {song.author}" if song.author else song.name


class CollectionForm(forms.ModelForm):
    songs = SongChoiceField(
        queryset=Song.objects.select_related("author").order_by("name"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Collection
        fields = ["name", "songs"]


class AddToCollectionForm(forms.Form):
    collection = forms.ModelChoiceField(queryset=Collection.objects.all())
