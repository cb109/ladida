from urllib.parse import urlparse

from django import forms

from .models import PlaylistImport

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
