from django import template
from django.utils import timezone

register = template.Library()

AVATAR_COLORS = [
    ("#f7dfba", "#5b3d12"),  # krem
    ("#ffa74f", "#3b1f00"),  # oranye
    ("#09332c", "#f7edda"),  # hijau tua
    ("#2e4b3c", "#f7edda"),  # hijau
    ("#e8d5f0", "#4a2a5c"),  # ungu muda
    ("#cfe3f5", "#16405f"),  # biru muda
]


@register.filter
def waktu_lalu(value):
    if not value:
        return ""
    seconds = int((timezone.now() - value).total_seconds())
    if seconds < 60:
        return "Baru saja"
    if seconds < 3600:
        return f"{seconds // 60} menit lalu"
    if seconds < 86400:
        return f"{seconds // 3600} jam lalu"
    days = seconds // 86400
    if days == 1:
        return "Kemarin"
    if days < 7:
        return f"{days} hari lalu"
    return timezone.localtime(value).strftime("%d/%m/%Y")


def display_name(user):
    return user.get_full_name() or user.username


@register.filter
def nama_tampil(user):
    return display_name(user)


@register.filter
def inisial(user):
    parts = display_name(user).split()
    letters = "".join(p[0] for p in parts[:2]) if len(parts) > 1 else display_name(user)[:2]
    return letters.upper()


@register.filter
def warna_avatar(user):
    bg, fg = AVATAR_COLORS[user.pk % len(AVATAR_COLORS)]
    return f"background:{bg};color:{fg}"