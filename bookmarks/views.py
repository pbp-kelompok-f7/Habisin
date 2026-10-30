from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from discovery.views import _capitalize_words, _extract_ingredients, _lookup_meal, _paginate
from fridge.views import api_login_required, read_json

from .models import Category, SavedRecipe, default_category

NAME_MAX_LENGTH = Category._meta.get_field("name").max_length
MAX_CATEGORIES_PER_USER = 50
MAX_QUERY_LENGTH = 100


def _serialize_category(category):
    return {"id": category.id, "name": category.name, "is_default": category.is_default}


def _serialize_saved_recipe(saved):
    return {
        "id": saved.recipe_id,
        "name": saved.name,
        "image": saved.image,
        "ingredients": saved.ingredients,
        "ingredient_count": len(saved.ingredients),
    }


def _search_saved_recipes(category, query, page_number):
    recipes = list(category.recipes.all())
    if query:
        # Cocokkan nama resep atau salah satu bahannya; difilter di Python karena icontains pada
        # JSONField di SQLite membandingkan teks JSON yang sudah di-escape
        needle = query.casefold()
        recipes = [
            r for r in recipes
            if needle in r.name.casefold() or any(needle in i.casefold() for i in r.ingredients)
        ]
    page_obj, page_meta = _paginate(recipes, page_number)
    return {
        "query": query,
        **page_meta,
        "recipes": [_serialize_saved_recipe(r) for r in page_obj.object_list],
    }


def _clean_name(user, data, exclude=None):
    """Mengembalikan (nama, error); error berbentuk sama dengan form_errors di fridge."""
    name = str(data.get("name", "")).strip()
    if not name:
        return None, {"name": ["Category name cannot be empty."]}
    if len(name) > NAME_MAX_LENGTH:
        return None, {"name": [f"Category name cannot exceed {NAME_MAX_LENGTH} characters."]}
    duplicates = Category.objects.filter(user=user, name__iexact=name)
    if exclude is not None:
        duplicates = duplicates.exclude(pk=exclude.pk)
    if duplicates.exists():
        return None, {"name": ["A category with this name already exists."]}
    return name, None


@login_required
def show_bookmarks(request):
    fallback = default_category(request.user)
    categories = list(
        Category.objects.filter(user=request.user).annotate(recipe_count=Count("recipes"))
    )
    selected_id = request.GET.get("category", "")
    selected = next((c for c in categories if str(c.id) == selected_id), None)
    if selected is None:
        selected = next(c for c in categories if c.id == fallback.id)

    return render(request, "bookmarks/index.html", {
        "categories": categories,
        "selected_category": selected,
        "default_category": fallback,
        **_search_saved_recipes(selected, "", 1),
    })


@require_GET
@api_login_required
def category_recipes(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    query = request.GET.get("q", "").strip()[:MAX_QUERY_LENGTH]
    return JsonResponse(_search_saved_recipes(category, query, request.GET.get("page")))


@require_POST
@api_login_required
def category_create(request):
    data = read_json(request)
    if data is None:
        return JsonResponse({"error": "Invalid data."}, status=400)

    if Category.objects.filter(user=request.user).count() >= MAX_CATEGORIES_PER_USER:
        return JsonResponse(
            {"errors": {"name": [f"You can only create up to {MAX_CATEGORIES_PER_USER} categories."]}}, status=400
        )

    name, errors = _clean_name(request.user, data)
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    category = Category.objects.create(user=request.user, name=name)
    return JsonResponse({"category": _serialize_category(category)}, status=201)


@require_POST
@api_login_required
def category_rename(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    if category.is_default:
        return JsonResponse({"error": "Default category cannot be renamed."}, status=400)

    data = read_json(request)
    if data is None:
        return JsonResponse({"error": "Invalid data."}, status=400)

    name, errors = _clean_name(request.user, data, exclude=category)
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    category.name = name
    category.save(update_fields=["name"])
    return JsonResponse({"category": _serialize_category(category)})


@require_POST
@api_login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    if category.is_default:
        return JsonResponse({"error": "Default category cannot be deleted."}, status=400)

    category.delete()
    return JsonResponse({"deleted": pk, "redirect_category": default_category(request.user).id})


@require_POST
@api_login_required
def category_recipe_delete(request, pk, recipe_id):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    saved = get_object_or_404(SavedRecipe, category=category, recipe_id=recipe_id)
    saved.delete()
    return JsonResponse({"deleted": recipe_id, "recipe_count": category.recipes.count()})


@require_GET
@api_login_required
def recipe_categories(request, recipe_id):
    default_category(request.user)
    selected_ids = set(
        SavedRecipe.objects.filter(category__user=request.user, recipe_id=recipe_id)
        .values_list("category_id", flat=True)
    )
    categories = [
        {**_serialize_category(c), "selected": c.id in selected_ids}
        for c in Category.objects.filter(user=request.user)
    ]
    return JsonResponse({"categories": categories})


@require_POST
@api_login_required
def recipe_save(request, recipe_id):
    data = read_json(request)
    raw_ids = data.get("category_ids") if data else None
    if not isinstance(raw_ids, list):
        return JsonResponse({"error": "Invalid data."}, status=400)

    wanted = Category.objects.filter(user=request.user, pk__in=[i for i in raw_ids if isinstance(i, int)])
    wanted_ids = set(wanted.values_list("id", flat=True))
    saved = SavedRecipe.objects.filter(category__user=request.user, recipe_id=recipe_id)
    existing_ids = set(saved.values_list("category_id", flat=True))
    to_add = wanted_ids - existing_ids

    snapshot = None
    if to_add:
        existing = saved.first()
        if existing:
            snapshot = {"name": existing.name, "image": existing.image, "ingredients": existing.ingredients}
        else:
            meal = _lookup_meal(recipe_id)
            if not meal:
                return JsonResponse({"error": "Recipe not found."}, status=404)
            snapshot = {
                "name": _capitalize_words(meal["strMeal"]),
                "image": meal["strMealThumb"],
                "ingredients": [_capitalize_words(i) for i in _extract_ingredients(meal)],
            }

    with transaction.atomic():
        saved.exclude(category_id__in=wanted_ids).delete()
        SavedRecipe.objects.bulk_create(
            [SavedRecipe(category_id=pk, recipe_id=recipe_id, **snapshot) for pk in to_add],
            ignore_conflicts=True,
        )

    return JsonResponse({"bookmarked": bool(wanted_ids)})
