import random
from django.db import models
from django.utils import timezone


class Game(models.Model):
    title = models.CharField(max_length=120)
    location = models.CharField(max_length=200, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    capacity = models.PositiveIntegerField(default=18)
    access_code = models.CharField(max_length=5, unique=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.access_code:
            self.access_code = self._generate_unique_code()
        super().save(*args, **kwargs)

    def _generate_unique_code(self):
        while True:
            code = f"{random.randint(0, 99999):05d}"
            if not Game.objects.filter(access_code=code).exists():
                return code

    @property
    def is_past(self):
        return self.end_time < timezone.now()

    def __str__(self):
        return f"{self.title} ({self.access_code})"


class Announcement(models.Model):
    title = models.CharField(max_length=120)
    message = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Registration(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        WAITLIST = "WAITLIST", "Waitlist"
        DENIED = "DENIED", "Denied"
        CANCELLED = "CANCELLED", "Cancelled"
        REMOVED = "REMOVED", "Removed by organizer"

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="registrations")
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40)

    # store digits-only phone for “password”
    phone_digits = models.CharField(max_length=30, editable=False)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    # position used separately for confirmed and waitlist
    position = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("game", "email")

    def save(self, *args, **kwargs):
        self.phone_digits = "".join(ch for ch in (self.phone or "") if ch.isdigit())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.game.access_code} - {self.status}"


class Activity(models.Model):
    class Kind(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        APPROVED = "APPROVED", "Approved"
        DENIED = "DENIED", "Denied"
        CANCELLED = "CANCELLED", "Cancelled"
        REMOVED = "REMOVED", "Removed"
        MOVED = "MOVED", "Moved list"

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="activity")
    registration = models.ForeignKey(Registration, on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.kind} - {self.message}"
