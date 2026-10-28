from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import CommentForm
from .models import Comment

INITIAL_COMMENT_COUNT = 5


def recipe_url(recipe_id):
    return reverse("discovery:show_recipe_detail", args=[recipe_id]) + "#komentar"


def comment_section_context(request, recipe_id):
    """Data untuk templates/comments/_section.html. Dipanggil dari view detail resep."""
    comments = (
        Comment.objects.filter(recipe_id=recipe_id)
        .select_related("user")
        .annotate(like_count=Count("likes"))
        .order_by("-created_at")  # wajib eksplisit: Meta.ordering diabaikan saat annotate(Count)
    )
    total = comments.count()
    show_all = request.GET.get("semua") == "1"
    shown = list(comments if show_all else comments[:INITIAL_COMMENT_COUNT])

    liked_ids = set()
    if request.user.is_authenticated:
        liked_ids = set(
            request.user.liked_comments.filter(recipe_id=recipe_id).values_list("id", flat=True)
        )
    for comment in shown:
        comment.is_liked = comment.id in liked_ids

    return {
        "comment_recipe_id": recipe_id,
        "comments": shown,
        "comment_total": total,
        "comment_has_more": total > len(shown),
        "comment_form": CommentForm(),
    }


@login_required
@require_POST
def add_comment(request, recipe_id):
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.recipe_id = recipe_id
        comment.user = request.user
        comment.save()
    else:
        messages.error(request, form.errors.get("content", ["Komentar tidak valid."])[0], extra_tags="comment")
    return redirect(recipe_url(recipe_id))


@login_required
@require_POST
def toggle_like(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    if comment.likes.filter(pk=request.user.pk).exists():
        comment.likes.remove(request.user)
    else:
        comment.likes.add(request.user)
    return redirect(recipe_url(comment.recipe_id))


@login_required
@require_POST
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, user=request.user)
    recipe_id = comment.recipe_id
    comment.delete()
    return redirect(recipe_url(recipe_id))