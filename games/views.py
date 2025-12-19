from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import Game, Registration, Announcement, Activity
from .forms import GameForm


# -------------------------
# Organizer (Code-only) Auth
# -------------------------

def organizer_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.session.get("is_organizer") is True:
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Not allowed.")
    return _wrapped


def organizer_login(request):
    if request.session.get("is_organizer") is True:
        return redirect("games:dashboard")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        if code == settings.ORGANIZER_CODE:
            request.session["is_organizer"] = True
            request.session.set_expiry(60 * 60 * 8)  # 8 hours
            messages.success(request, "Organizer access granted.")
            return redirect("games:dashboard")
        messages.error(request, "Wrong organizer code.")
        return redirect("games:organizer_login")

    return render(request, "games/organizer_login.html")


def organizer_logout(request):
    request.session.pop("is_organizer", None)
    messages.success(request, "Logged out.")
    return redirect("games:enter_code")


# -------------------------
# Player Portal Auth (per-game session)
# -------------------------

def _player_required(view_func):
    @wraps(view_func)
    def _wrapped(request, code, *args, **kwargs):
        key = f"player_reg_{code}"
        if request.session.get(key):
            return view_func(request, code, *args, **kwargs)
        return redirect("games:player_portal_login", code=code)
    return _wrapped


def player_portal_login(request, code):
    game = get_object_or_404(Game, access_code=code)

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        phone_pw = "".join(ch for ch in request.POST.get("password", "") if ch.isdigit())

        reg = Registration.objects.filter(game=game, email__iexact=email).first()
        if not reg:
            messages.error(request, "No registration found for that email on this game.")
            return redirect("games:player_portal_login", code=code)

        computed_digits = "".join(ch for ch in (reg.phone or "") if ch.isdigit())

        ok = False
        if reg.phone_digits and reg.phone_digits == phone_pw:
            ok = True
        elif (not reg.phone_digits) and computed_digits == phone_pw:
            reg.phone_digits = computed_digits
            reg.save(update_fields=["phone_digits"])
            ok = True

        if not ok:
            messages.error(request, "Wrong password. Use your phone number digits only.")
            return redirect("games:player_portal_login", code=code)

        request.session[f"player_reg_{code}"] = reg.id
        request.session.set_expiry(60 * 60 * 8)
        return redirect("games:player_portal_manage", code=code)

    return render(request, "games/player_portal_login.html", {"game": game})


@_player_required
def player_portal_manage(request, code):
    game = get_object_or_404(Game, access_code=code)
    reg_id = request.session.get(f"player_reg_{code}")
    reg = get_object_or_404(Registration, id=reg_id, game=game)

    return render(request, "games/player_portal_manage.html", {"game": game, "reg": reg})


def player_portal_logout(request, code):
    request.session.pop(f"player_reg_{code}", None)
    messages.success(request, "Logged out.")
    return redirect("games:game_detail", code=code)


@_player_required
def player_cancel(request, code):
    game = get_object_or_404(Game, access_code=code)
    reg_id = request.session.get(f"player_reg_{code}")
    reg = get_object_or_404(Registration, id=reg_id, game=game)

    if request.method == "POST":
        if reg.status in [Registration.Status.CANCELLED, Registration.Status.REMOVED, Registration.Status.DENIED]:
            messages.error(request, "This registration can’t be cancelled.")
            return redirect("games:player_portal_manage", code=code)

        reg.status = Registration.Status.CANCELLED
        reg.position = None
        reg.save()

        Activity.objects.create(
            game=game, registration=reg,
            kind=Activity.Kind.CANCELLED,
            message=f"{reg.name} cancelled (email: {reg.email})"
        )

        _promote_from_waitlist_if_needed(game)

        messages.success(request, "Cancelled. You are removed from the list.")
        return redirect("games:player_portal_manage", code=code)

    return render(request, "games/player_cancel.html", {"game": game, "reg": reg})


# -------------------------
# Player Views
# -------------------------

def enter_code(request):
    if request.method == "POST":
        code = request.POST.get("code", "").strip()

        if len(code) != 5 or not code.isdigit():
            messages.error(request, "Please enter a valid 5-digit code.")
            return redirect("games:enter_code")

        game = Game.objects.filter(access_code=code).first()
        if not game:
            messages.error(request, "That code is invalid.")
            return redirect("games:enter_code")

        return redirect("games:game_detail", code=code)

    return render(request, "games/enter_code.html")


def game_detail(request, code):
    game = get_object_or_404(Game, access_code=code)

    if game.is_past:
        return render(request, "games/game_closed.html", {"game": game})

    # page announcements (inside game page, optional)
    announcements = Announcement.objects.filter(is_active=True).order_by("-created_at")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()

        if not name or not email or not phone:
            messages.error(request, "Please fill out all fields.")
            return redirect("games:game_detail", code=code)

        if Registration.objects.filter(game=game, email=email).exists():
            messages.error(request, "This email is already registered for this game.")
            return redirect("games:game_detail", code=code)

        reg = Registration.objects.create(
            game=game,
            name=name,
            email=email,
            phone=phone,
            status=Registration.Status.PENDING,
        )

        Activity.objects.create(
            game=game, registration=reg,
            kind=Activity.Kind.REQUESTED,
            message=f"New request: {reg.name} ({reg.email})"
        )

        messages.success(
            request,
            "Request sent. To check status or cancel: click 'Manage my spot' and login with email + phone digits."
        )
        return redirect("games:game_detail", code=code)

    confirmed = game.registrations.filter(status=Registration.Status.CONFIRMED).order_by("position")
    waitlist = game.registrations.filter(status=Registration.Status.WAITLIST).order_by("position")
    pending_count = game.registrations.filter(status=Registration.Status.PENDING).count()

    context = {
        "game": game,
        "announcements": announcements,
        "confirmed": confirmed,
        "waitlist": waitlist,
        "pending_count": pending_count,
    }
    return render(request, "games/game_detail.html", context)


# -------------------------
# Helpers
# -------------------------

def _recalc_positions(game: Game) -> None:
    confirmed = game.registrations.filter(status=Registration.Status.CONFIRMED).order_by("created_at")
    for i, r in enumerate(confirmed, start=1):
        if r.position != i:
            r.position = i
            r.save(update_fields=["position"])

    waitlist = game.registrations.filter(status=Registration.Status.WAITLIST).order_by("created_at")
    for i, r in enumerate(waitlist, start=1):
        if r.position != i:
            r.position = i
            r.save(update_fields=["position"])


def _promote_from_waitlist_if_needed(game: Game) -> None:
    confirmed_count = game.registrations.filter(status=Registration.Status.CONFIRMED).count()
    if confirmed_count < game.capacity:
        next_wait = game.registrations.filter(status=Registration.Status.WAITLIST).order_by("created_at").first()
        if next_wait:
            next_wait.status = Registration.Status.CONFIRMED
            next_wait.position = None
            next_wait.save()
            Activity.objects.create(
                game=game, registration=next_wait,
                kind=Activity.Kind.MOVED,
                message=f"Auto-promoted from waitlist: {next_wait.name}"
            )
            _recalc_positions(game)


def _recent_activity():
    return Activity.objects.select_related("game").order_by("-created_at")[:12]


# -------------------------
# Organizer Dashboard + Actions
# -------------------------

@organizer_required
def dashboard(request):
    game_form = GameForm()

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "create_game":
            game_form = GameForm(request.POST)
            if game_form.is_valid():
                game = game_form.save()
                Activity.objects.create(
                    game=game, kind=Activity.Kind.MOVED,
                    message=f"Game created: {game.title} (code {game.access_code})"
                )
                messages.success(request, f"Game created. Code: {game.access_code}")
                return redirect("games:dashboard")
            messages.error(request, "Please fix the errors in the game form.")

    now = timezone.now()
    upcoming_games = Game.objects.filter(start_time__gte=now).order_by("start_time")

    pending_regs = (
        Registration.objects.filter(status=Registration.Status.PENDING)
        .select_related("game")
        .order_by("created_at")
    )

    # ✅ News list for offcanvas Manage News panel
    news_list = Announcement.objects.order_by("-created_at")[:20]

    context = {
        "game_form": game_form,
        "upcoming_games": upcoming_games,
        "pending_regs": pending_regs,
        "recent_activity": _recent_activity(),
        "news_list": news_list,
    }
    return render(request, "games/dashboard.html", context)


@organizer_required
def approve_registration(request, reg_id: int):
    reg = get_object_or_404(Registration, id=reg_id)

    if reg.status != Registration.Status.PENDING:
        messages.error(request, "This request was already processed.")
        return redirect("games:dashboard")

    game = reg.game
    confirmed_count = game.registrations.filter(status=Registration.Status.CONFIRMED).count()

    if confirmed_count < game.capacity:
        reg.status = Registration.Status.CONFIRMED
        msg = f"Approved (CONFIRMED): {reg.name}"
    else:
        reg.status = Registration.Status.WAITLIST
        msg = f"Approved (WAITLIST): {reg.name}"

    reg.position = None
    reg.save()
    _recalc_positions(game)

    Activity.objects.create(game=game, registration=reg, kind=Activity.Kind.APPROVED, message=msg)
    messages.success(request, msg)
    return redirect("games:dashboard")


@organizer_required
def deny_registration(request, reg_id: int):
    reg = get_object_or_404(Registration, id=reg_id)

    if reg.status != Registration.Status.PENDING:
        messages.error(request, "This request was already processed.")
        return redirect("games:dashboard")

    reg.status = Registration.Status.DENIED
    reg.position = None
    reg.save()

    Activity.objects.create(game=reg.game, registration=reg, kind=Activity.Kind.DENIED, message=f"Denied: {reg.name}")
    messages.success(request, f"Denied: {reg.name}")
    return redirect("games:dashboard")


@organizer_required
def edit_game(request, game_id: int):
    game = get_object_or_404(Game, id=game_id)

    if request.method == "POST":
        form = GameForm(request.POST, instance=game)
        if form.is_valid():
            form.save()
            Activity.objects.create(game=game, kind=Activity.Kind.MOVED, message=f"Game edited: {game.title}")
            messages.success(request, "Game updated.")
            return redirect("games:dashboard")
        messages.error(request, "Fix the errors in the form.")
    else:
        form = GameForm(instance=game)

    return render(request, "games/edit_game.html", {"form": form, "game": game, "recent_activity": _recent_activity()})


@organizer_required
def delete_game(request, game_id: int):
    game = get_object_or_404(Game, id=game_id)

    if request.method == "POST":
        Activity.objects.create(game=game, kind=Activity.Kind.MOVED, message=f"Game deleted: {game.title}")
        game.delete()
        messages.success(request, "Game deleted.")
        return redirect("games:dashboard")

    return render(request, "games/delete_game.html", {"game": game, "recent_activity": _recent_activity()})


@organizer_required
def manage_game(request, game_id: int):
    game = get_object_or_404(Game, id=game_id)

    confirmed = game.registrations.filter(status=Registration.Status.CONFIRMED).order_by("position")
    waitlist = game.registrations.filter(status=Registration.Status.WAITLIST).order_by("position")
    pending = game.registrations.filter(status=Registration.Status.PENDING).order_by("created_at")

    return render(request, "games/manage_game.html", {
        "game": game,
        "confirmed": confirmed,
        "waitlist": waitlist,
        "pending": pending,
        "recent_activity": _recent_activity(),
    })


@organizer_required
def organizer_remove_player(request, game_id: int, reg_id: int):
    game = get_object_or_404(Game, id=game_id)
    reg = get_object_or_404(Registration, id=reg_id, game=game)

    reg.status = Registration.Status.REMOVED
    reg.position = None
    reg.save()

    Activity.objects.create(game=game, registration=reg, kind=Activity.Kind.REMOVED, message=f"Removed: {reg.name}")
    _promote_from_waitlist_if_needed(game)
    _recalc_positions(game)

    messages.success(request, f"Removed: {reg.name}")
    return redirect("games:manage_game", game_id=game.id)


@organizer_required
def organizer_move_player(request, game_id: int, reg_id: int, target: str):
    game = get_object_or_404(Game, id=game_id)
    reg = get_object_or_404(Registration, id=reg_id, game=game)

    target = target.upper()
    if target not in ["CONFIRMED", "WAITLIST", "PENDING"]:
        messages.error(request, "Invalid target list.")
        return redirect("games:manage_game", game_id=game.id)

    if target == "CONFIRMED":
        confirmed_count = game.registrations.filter(status=Registration.Status.CONFIRMED).count()
        if confirmed_count >= game.capacity and reg.status != Registration.Status.CONFIRMED:
            target = "WAITLIST"

    reg.status = target
    reg.position = None
    reg.save()

    Activity.objects.create(game=game, registration=reg, kind=Activity.Kind.MOVED, message=f"Moved: {reg.name} → {target}")
    _recalc_positions(game)

    messages.success(request, f"Moved: {reg.name} → {target}")
    return redirect("games:manage_game", game_id=game.id)


# -------------------------
# ✅ NEWS MANAGEMENT (offcanvas actions)
# -------------------------

@organizer_required
def news_save(request):
    if request.method != "POST":
        return redirect("games:dashboard")

    news_id = request.POST.get("news_id", "").strip()
    title = request.POST.get("title", "").strip()
    message = request.POST.get("message", "").strip()
    is_active = request.POST.get("is_active") == "1"

    if not title or not message:
        messages.error(request, "Title and message are required.")
        return redirect("games:dashboard")

    if news_id:
        ann = get_object_or_404(Announcement, id=news_id)
        ann.title = title
        ann.message = message
        ann.is_active = is_active
        ann.save()
        messages.success(request, "News updated.")
    else:
        Announcement.objects.create(title=title, message=message, is_active=is_active)
        messages.success(request, "News posted.")

    return redirect("games:dashboard")


@organizer_required
def news_delete(request, news_id: int):
    if request.method != "POST":
        return redirect("games:dashboard")

    ann = get_object_or_404(Announcement, id=news_id)
    ann.delete()
    messages.success(request, "News deleted.")
    return redirect("games:dashboard")
