from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import LoginForm, ProfileForm, RegisterForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    form = LoginForm(request.POST or None)
    next_url = request.POST.get("next") or request.GET.get("next", "")

    if request.method == "POST" and form.is_valid():
        login(request, form.cleaned_data["user"])
        safe = url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        )
        return redirect(next_url if next_url and safe else settings.LOGIN_REDIRECT_URL)

    return render(request, "authentication/login.html", {"form": form, "next": next_url})


def register_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Account created. Please sign in.")
        return redirect("authentication:login")

    return render(request, "authentication/register.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)


@login_required
def profile_view(request):
    user = request.user
    # TODO: ganti data dummy activity dan meals_made dengan data dari database
    activity = [("Mon", 2), ("Tue", 1), ("Wed", 4), ("Thu", 3), ("Fri", 0), ("Sat", 0), ("Sun", 0)]
    context = {
        "profile": {"name": user.get_full_name() or user.username, "username": user.username},
        "activity": [{"day": d, "count": c, "height": c * 40} for d, c in activity],
        "activity_range": "22 Sept - 29 Sept",
        "meals_made": 10,
        "since": user.date_joined.year,
    }
    return render(request, "authentication/profile.html", context)


@login_required
def edit_profile_view(request):
    # User belum tentu punya Profile (dibuat saat pertama kali menyimpan foto)
    profile = getattr(request.user, "profile", None)

    form = ProfileForm(
        request.POST or None,
        request.FILES or None,
        initial={"name": request.user.first_name},
    )
    if request.method == "POST" and form.is_valid():
        form.save(request.user)
        messages.success(request, "Profile updated.")
        return redirect("authentication:profile")

    return render(request, "authentication/edit_profile.html", {"form": form, "profile": profile})