from django import forms
from django.utils import timezone
from .models import Game, Announcement


class GameForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ["title", "location", "start_time", "end_time", "capacity"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control form-control-lg input-glass"}),
            "location": forms.TextInput(attrs={"class": "form-control form-control-lg input-glass"}),
            "start_time": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control form-control-lg input-glass"},
                format="%Y-%m-%dT%H:%M",
            ),
            "end_time": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control form-control-lg input-glass"},
                format="%Y-%m-%dT%H:%M",
            ),
            "capacity": forms.NumberInput(attrs={"class": "form-control form-control-lg input-glass", "min": 1, "max": 50}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["start_time"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["end_time"].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")

        if start and timezone.is_naive(start):
            cleaned["start_time"] = timezone.make_aware(start, timezone.get_current_timezone())
        if end and timezone.is_naive(end):
            cleaned["end_time"] = timezone.make_aware(end, timezone.get_current_timezone())

        if cleaned.get("start_time") and cleaned.get("end_time"):
            if cleaned["end_time"] <= cleaned["start_time"]:
                self.add_error("end_time", "End time must be after start time.")
        return cleaned


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title", "message", "is_active"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control form-control-lg input-glass"}),
            "message": forms.Textarea(attrs={"class": "form-control input-glass", "rows": 4}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
