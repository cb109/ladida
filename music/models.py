from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Author(TimestampedModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Song(TimestampedModel):
    name = models.CharField(max_length=255)
    audio_file = models.FileField(upload_to="songs/")

    def __str__(self):
        return self.name


class Collection(TimestampedModel):
    name = models.CharField(max_length=255)
    songs = models.ManyToManyField(Song, related_name="collections", blank=True)

    def __str__(self):
        return self.name
