import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.contrib import messages
from .models import SavedMeal
from .forms import SavedMealForm, HistoryNoteForm, SavedMealFilterForm
from .spoonacular import (
    get_recipe_by_id,
    seed_default_meals_if_empty,
)


def _get_base_queryset(request, status):
    if request.user.is_authenticated:
        return SavedMeal.objects.filter(status=status, user=request.user)
    return SavedMeal.objects.filter(status=status, user__isnull=True)


def _apply_db_filters(qs, filter_data, default_order='-created_at'):
    q = (filter_data.get('q') or '').strip()
    time_filter = filter_data.get('time_filter') or ''
    calorie_filter = filter_data.get('calorie_filter') or ''
    sort_by = filter_data.get('sort_by') or ''

    if q:
        qs = qs.filter(
            Q(recipe_name__icontains=q)
            | Q(ingredients__icontains=q)
            | Q(notes__icontains=q)
        )

    if time_filter == 'quick':
        qs = qs.filter(cooking_time_minutes__lte=20)
    elif time_filter == 'medium':
        qs = qs.filter(cooking_time_minutes__gt=20, cooking_time_minutes__lte=35)
    elif time_filter == 'long':
        qs = qs.filter(cooking_time_minutes__gt=35)

    if calorie_filter == 'low':
        qs = qs.filter(calories_kcal__lte=350)
    elif calorie_filter == 'medium':
        qs = qs.filter(calories_kcal__gt=350, calories_kcal__lte=500)
    elif calorie_filter == 'high':
        qs = qs.filter(calories_kcal__gt=500)

    sort_map = {
        'newest': default_order,
        'time_asc': 'cooking_time_minutes',
        'calories_asc': 'calories_kcal',
        'portions_desc': '-portions_saved',
    }
    order_field = sort_map.get(sort_by, default_order)
    return qs.order_by(order_field, '-id')


def _get_history_queryset(request, filter_data=None):
    qs = _get_base_queryset(request, 'HISTORY')
    if filter_data:
        return _apply_db_filters(qs, filter_data, default_order='-updated_at')
    return qs.order_by('-updated_at', '-created_at')


def _get_saved_queryset(request, filter_data=None):
    qs = _get_base_queryset(request, 'SAVED')
    if filter_data:
        return _apply_db_filters(qs, filter_data, default_order='-created_at')
    return qs.order_by('-created_at')


def _compute_metrics(history_meals):
    portions_agg = history_meals.aggregate(total=Sum('portions_saved'))['total']
    total_portions = portions_agg if portions_agg is not None else 0

    weight_agg = history_meals.aggregate(total=Sum('ingredients_saved_kg'))['total']
    total_weight = round(weight_agg, 1) if weight_agg is not None else 0.0

    recipes_finished = history_meals.count()

    protein_agg = history_meals.aggregate(total=Sum('protein_grams'))['total']
    total_protein = protein_agg if protein_agg is not None else 0

    calories_agg = history_meals.aggregate(total=Sum('calories_kcal'))['total']
    total_calories = calories_agg if calories_agg is not None else 0

    return {
        'total_portions': total_portions,
        'total_weight': total_weight,
        'recipes_finished': recipes_finished,
        'total_protein': total_protein,
        'total_calories': total_calories,
    }


@ensure_csrf_cookie
def show_saved_meals(request):
    user = request.user if request.user.is_authenticated else None
    seed_default_meals_if_empty(user)

    filter_form = SavedMealFilterForm(request.GET or None)
    filter_data = filter_form.cleaned_data if filter_form.is_valid() else {}

    saved_meals = _get_saved_queryset(request, filter_data)
    history_meals = _get_history_queryset(request, filter_data)

    all_history = _get_history_queryset(request)
    metrics = _compute_metrics(all_history)

    context = {
        **metrics,
        'saved_meals': saved_meals,
        'history_meals': history_meals,
        'filter_form': filter_form,
        'meal_form': SavedMealForm(),
        'note_form': HistoryNoteForm(),
        'active_filters': {
            'q': filter_data.get('q', ''),
            'time_filter': filter_data.get('time_filter', ''),
            'calorie_filter': filter_data.get('calorie_filter', ''),
            'sort_by': filter_data.get('sort_by', 'newest') or 'newest',
        },
    }
    return render(request, "saved_meals/index.html", context)


@require_GET
def saved_meals_json(request):
    user = request.user if request.user.is_authenticated else None
    seed_default_meals_if_empty(user)

    filter_form = SavedMealFilterForm(request.GET or None)
    filter_data = filter_form.cleaned_data if filter_form.is_valid() else {}

    include_private = request.user.is_authenticated
    saved_meals = _get_saved_queryset(request, filter_data)
    history_meals = _get_history_queryset(request, filter_data)
    metrics = _compute_metrics(_get_history_queryset(request))

    return JsonResponse({
        'success': True,
        'is_authenticated': include_private,
        'saved_meals': [m.to_dict(include_private=include_private) for m in saved_meals],
        'history_meals': [m.to_dict(include_private=include_private) for m in history_meals],
        'metrics': metrics,
    })


@require_POST
def add_saved_meal(request):
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Silakan Sign In terlebih dahulu untuk menambahkan menu pribadi.',
        }, status=403)

    if request.content_type == 'application/json':
        try:
            payload = json.loads(request.body)
        except Exception:
            payload = {}
        form = SavedMealForm(payload)
    else:
        form = SavedMealForm(request.POST)

    if form.is_valid():
        meal = form.save(user=request.user)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({
                'success': True,
                'meal': meal.to_dict(include_private=True),
            }, status=201)
        messages.success(request, f"Menu '{meal.recipe_name}' berhasil ditambahkan!")
        return redirect('saved_meals:show_saved_meals')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({
            'success': False,
            'errors': form.errors,
        }, status=400)

    messages.error(request, 'Gagal menambahkan menu. Periksa kembali isian form.')
    return redirect('saved_meals:show_saved_meals')


@require_POST
def mark_meal_done(request, meal_id):
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Silakan Sign In terlebih dahulu untuk menandai masakan selesai.',
        }, status=403)

    saved_meal = get_object_or_404(SavedMeal, id=meal_id, status='SAVED', user=request.user)
    recipe_id = saved_meal.recipe_id

    history_qs = SavedMeal.objects.filter(status='HISTORY', user=request.user)

    existing_history = None
    if recipe_id:
        existing_history = history_qs.filter(recipe_id=recipe_id).first()
    if not existing_history and saved_meal.recipe_name:
        existing_history = history_qs.filter(recipe_name__iexact=saved_meal.recipe_name).first()

    if existing_history:
        existing_history.portions_saved += saved_meal.portions_saved
        existing_history.ingredients_saved_kg = round(
            existing_history.ingredients_saved_kg + saved_meal.ingredients_saved_kg, 1
        )
        existing_history.protein_grams += saved_meal.protein_grams
        existing_history.calories_kcal += saved_meal.calories_kcal
        if saved_meal.notes and not existing_history.notes:
            existing_history.notes = saved_meal.notes
        existing_history.save()
        saved_meal.delete()

        action = 'incremented'
        history_meal = existing_history
    else:
        saved_meal.status = 'HISTORY'
        saved_meal.save()

        action = 'created'
        history_meal = saved_meal

    updated_history = _get_history_queryset(request)
    metrics = _compute_metrics(updated_history)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({
            'success': True,
            'action': action,
            'history_meal_id': history_meal.id,
            'new_portions': history_meal.portions_saved,
            'meal': history_meal.to_dict(include_private=True),
            'metrics': metrics,
        })

    return redirect('saved_meals:show_saved_meals')


@require_POST
def edit_history_note(request, meal_id):
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Silakan Sign In terlebih dahulu untuk mengubah catatan.',
        }, status=403)

    history_meal = get_object_or_404(SavedMeal, id=meal_id, status='HISTORY', user=request.user)

    if request.content_type == 'application/json':
        try:
            body = json.loads(request.body)
        except Exception:
            body = {}
        data = {
            'notes': body.get('notes', ''),
            'portions_saved': body.get('portions_saved', history_meal.portions_saved),
        }
    else:
        data = {
            'notes': request.POST.get('notes', ''),
            'portions_saved': request.POST.get('portions_saved', history_meal.portions_saved),
        }

    form = HistoryNoteForm(data, instance=history_meal)
    if form.is_valid():
        updated_meal = form.save(commit=False)
        updated_meal.ingredients_saved_kg = round(updated_meal.portions_saved * 0.2, 1)
        updated_meal.save()
        metrics = _compute_metrics(_get_history_queryset(request))
        return JsonResponse({
            'success': True,
            'meal_id': updated_meal.id,
            'notes': updated_meal.notes,
            'portions_saved': updated_meal.portions_saved,
            'metrics': metrics,
        })

    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@require_POST
def delete_history_meal(request, meal_id):
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Silakan Sign In terlebih dahulu untuk menghapus riwayat.',
        }, status=403)

    history_meal = get_object_or_404(SavedMeal, id=meal_id, status='HISTORY', user=request.user)
    history_meal.delete()

    updated_history = _get_history_queryset(request)
    metrics = _compute_metrics(updated_history)

    return JsonResponse({
        'success': True,
        'meal_id': meal_id,
        'metrics': metrics,
    })


@require_POST
def delete_saved_meal(request, meal_id):
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Silakan Sign In terlebih dahulu untuk menghapus menu.',
        }, status=403)

    saved_meal = get_object_or_404(SavedMeal, id=meal_id, status='SAVED', user=request.user)
    saved_meal.delete()

    return JsonResponse({
        'success': True,
        'meal_id': meal_id,
    })


@login_required
def save_recipe(request, recipe_id):
    recipe_data = get_recipe_by_id(recipe_id)
    if not recipe_data:
        messages.error(request, 'Resep tidak ditemukan.')
        return redirect('saved_meals:show_saved_meals')

    SavedMeal.objects.create(
        user=request.user,
        recipe_id=recipe_data['id'],
        recipe_name=recipe_data['title'],
        image_url=recipe_data.get('image', ''),
        cooking_time_minutes=recipe_data.get('readyInMinutes', 30),
        portions_saved=recipe_data.get('servings', 1),
        ingredients_saved_kg=recipe_data.get('ingredients_kg', 0.2),
        protein_grams=recipe_data.get('protein', 10),
        calories_kcal=recipe_data.get('calories', 300),
        ingredients=recipe_data.get('ingredients', ''),
        status='SAVED',
    )

    messages.success(request, f"Resep '{recipe_data['title']}' berhasil ditambahkan ke Saved Meals!")
    return redirect('saved_meals:show_saved_meals')
