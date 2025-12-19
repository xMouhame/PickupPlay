from django.urls import path
from . import views

app_name = "games"

urlpatterns = [
    # Players
    path("", views.enter_code, name="enter_code"),
    path("game/<str:code>/", views.game_detail, name="game_detail"),

    # Player portal (check status / cancel)
    path("my/<str:code>/", views.player_portal_login, name="player_portal_login"),
    path("my/<str:code>/manage/", views.player_portal_manage, name="player_portal_manage"),
    path("my/<str:code>/logout/", views.player_portal_logout, name="player_portal_logout"),
    path("my/<str:code>/cancel/", views.player_cancel, name="player_cancel"),

    # Organizer secret-code login
    path("organizer/login/", views.organizer_login, name="organizer_login"),
    path("organizer/logout/", views.organizer_logout, name="organizer_logout"),

    # Organizer dashboard
    path("dashboard/", views.dashboard, name="dashboard"),

    # Approve/Deny registrations (pending list)
    path("dashboard/approve/<int:reg_id>/", views.approve_registration, name="approve_registration"),
    path("dashboard/deny/<int:reg_id>/", views.deny_registration, name="deny_registration"),

    # Edit/Delete games
    path("dashboard/game/<int:game_id>/edit/", views.edit_game, name="edit_game"),
    path("dashboard/game/<int:game_id>/delete/", views.delete_game, name="delete_game"),

    # Organizer manage a specific game (add/remove/move players)
    path("dashboard/game/<int:game_id>/", views.manage_game, name="manage_game"),
    path("dashboard/game/<int:game_id>/remove/<int:reg_id>/", views.organizer_remove_player, name="organizer_remove_player"),
    path("dashboard/game/<int:game_id>/move/<int:reg_id>/<str:target>/", views.organizer_move_player, name="organizer_move_player"),

    path("news/save/", views.news_save, name="news_save"),
    path("news/<int:news_id>/delete/", views.news_delete, name="news_delete"),
]
