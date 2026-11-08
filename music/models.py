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

    author = models.ForeignKey(
        Author, on_delete=models.SET_NULL, null=True, blank=True, related_name="songs"
    )
    audio_file = models.FileField(upload_to="songs/")

    thumbnail = models.FileField(upload_to="songs/", blank=True)

    # null (not "") so manually added songs don't collide on the unique constraint
    youtube_id = models.CharField(max_length=64, unique=True, null=True, blank=True)

    def __str__(self):
        return self.name


class Collection(TimestampedModel):
    name = models.CharField(max_length=255)

    songs = models.ManyToManyField(Song, related_name="collections", blank=True)

    def __str__(self):
        return self.name


class PlaylistImport(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    url = models.URLField(max_length=500)

    title = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=16, choices=Status, default=Status.PENDING)

    total = models.PositiveIntegerField(default=0)

    processed = models.PositiveIntegerField(default=0)

    failed = models.PositiveIntegerField(default=0)

    current_title = models.CharField(max_length=255, blank=True)

    current_percent = models.PositiveSmallIntegerField(default=0)

    log = models.TextField(blank=True)

    collection = models.ForeignKey(
        Collection, on_delete=models.SET_NULL, null=True, blank=True, related_name="imports"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or self.url

    @property
    def is_active(self):
        return self.status in (self.Status.PENDING, self.Status.RUNNING)

    @property
    def percent(self):
        if not self.total:
            return 0
        return int(self.processed * 100 / self.total)
