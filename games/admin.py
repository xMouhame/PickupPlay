from django.contrib import admin
from .models import Game, Registration, Announcement


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("title", "location", "start_time", "end_time", "capacity", "access_code")
    readonly_fields = ("access_code", "created_at")
    list_filter = ("location", "start_time")
    search_fields = ("title", "location", "access_code")


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "game", "status", "position", "created_at")
    list_filter = ("status", "game")
    search_fields = ("name", "email", "phone")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "message")
