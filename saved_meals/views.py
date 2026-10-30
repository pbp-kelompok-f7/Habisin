from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from discovery.views import _capitalize_words, _extract_ingredients, _lookup_meal
from .models import SavedMeal
from .forms import SavedMealForm, HistoryNoteForm
from .openfoodfacts import estimate_meal_nutrition, scale_nutrition

LEGACY_SEED_RECIPE_IDS = (101, 102, 103, 104, 105)


def _purge_legacy_seeds(user):
    SavedMeal.objects.filter(user=user, recipe_id__in=LEGACY_SEED_RECIPE_IDS).delete()


def _get_meals(request, status, apply_filter=True):
    qs = SavedMeal.objects.filter(status=status, user=request.user)

    if not apply_filter:
        return qs.order_by('-updated_at', '-id')

    q = request.GET.get('q', '').strip()
    time_filter = request.GET.get('time_filter', '')
    calorie_filter = request.GET.get('calorie_filter', '')

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

    return qs.order_by('-updated_at', '-id')


def _compute_metrics(history_qs):
    agg = history_qs.aggregate(
        portions=Sum('portions_saved'),
        weight=Sum('ingredients_saved_kg'),
        protein=Sum('protein_grams'),
        calories=Sum('calories_kcal'),
    )
    weight = agg['weight']
    return {
        'total_portions': agg['portions'] or 0,
        'total_weight': round(weight, 1) if weight else 0,
        'recipes_finished': history_qs.count(),
        'total_protein': agg['protein'] or 0,
        'total_calories': agg['calories'] or 0,
    }


@login_required
@ensure_csrf_cookie
def show_saved_meals(request):
    _purge_legacy_seeds(request.user)
    saved_meals = _get_meals(request, 'SAVED')
    history_meals = _get_meals(request, 'HISTORY')
    metrics = _compute_metrics(_get_meals(request, 'HISTORY', apply_filter=False))

    context = {
        **metrics,
        'saved_meals': saved_meals,
        'history_meals': history_meals,
        'note_form': HistoryNoteForm(),
        'q': request.GET.get('q', ''),
        'time_filter': request.GET.get('time_filter', ''),
        'calorie_filter': request.GET.get('calorie_filter', ''),
    }
    return render(request, 'saved_meals/index.html', context)


@login_required
@require_GET
def saved_meals_json(request):
    _purge_legacy_seeds(request.user)
    saved_meals = _get_meals(request, 'SAVED')
    history_meals = _get_meals(request, 'HISTORY')
    metrics = _compute_metrics(_get_meals(request, 'HISTORY', apply_filter=False))

    return JsonResponse({
        'success': True,
        'saved_meals': [m.to_dict() for m in saved_meals],
        'history_meals': [m.to_dict() for m in history_meals],
        'metrics': metrics,
    })


@login_required
@require_POST
def add_saved_meal(request):
    form = SavedMealForm(request.POST)
    if form.is_valid():
        meal = form.save(commit=False)
        meal.user = request.user
        meal.status = 'SAVED'
        portions = meal.portions_saved or 1
        meal.ingredients_saved_kg = round(portions * 0.2, 1)

        calories_val = form.cleaned_data.get('calories_kcal')
        protein_val = form.cleaned_data.get('protein_grams')
        if not calories_val or protein_val is None:
            nutrition = estimate_meal_nutrition(meal.ingredients or meal.recipe_name, portions=portions)
            if not calories_val:
                meal.calories_kcal = nutrition['calories_kcal']
            if protein_val is None:
                meal.protein_grams = nutrition['protein_grams']

        meal.save()
        return JsonResponse({'success': True, 'meal': meal.to_dict()}, status=201)

    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def add_recipe_to_saved_meals(request, recipe_id):
    existing = SavedMeal.objects.filter(user=request.user, status='SAVED', recipe_id=recipe_id).first()
    if existing:
        return JsonResponse({'success': True, 'created': False, 'meal': existing.to_dict()})

    meal = _lookup_meal(recipe_id)
    if not meal:
        return JsonResponse({'success': False, 'error': 'Resep tidak ditemukan.'}, status=404)

    ingredients = ', '.join(_capitalize_words(i) for i in _extract_ingredients(meal))
    nutrition = estimate_meal_nutrition(ingredients, portions=1)

    saved_meal = SavedMeal.objects.create(
        user=request.user,
        recipe_id=recipe_id,
        recipe_name=_capitalize_words(meal['strMeal']),
        image_url=meal['strMealThumb'],
        ingredients=ingredients,
        calories_kcal=nutrition['calories_kcal'],
        protein_grams=nutrition['protein_grams'],
        status='SAVED',
    )
    return JsonResponse({'success': True, 'created': True, 'meal': saved_meal.to_dict()}, status=201)


@login_required
@require_POST
def mark_meal_done(request, meal_id):
    saved_meal = get_object_or_404(SavedMeal, id=meal_id, status='SAVED', user=request.user)
    existing = SavedMeal.objects.filter(
        status='HISTORY',
        user=request.user,
        recipe_name__iexact=saved_meal.recipe_name,
    ).first()

    if existing:
        existing.portions_saved += saved_meal.portions_saved
        existing.ingredients_saved_kg = round(existing.ingredients_saved_kg + saved_meal.ingredients_saved_kg, 1)
        existing.protein_grams += saved_meal.protein_grams
        existing.calories_kcal += saved_meal.calories_kcal
        existing.save()
        saved_meal.delete()
        history_meal = existing
    else:
        saved_meal.status = 'HISTORY'
        saved_meal.save()
        history_meal = saved_meal

    metrics = _compute_metrics(_get_meals(request, 'HISTORY', apply_filter=False))
    return JsonResponse({
        'success': True,
        'meal': history_meal.to_dict(),
        'metrics': metrics,
    })


@login_required
@require_POST
def edit_history_note(request, meal_id):
    history_meal = get_object_or_404(SavedMeal, id=meal_id, status='HISTORY', user=request.user)
    old_portions = history_meal.portions_saved or 1
    old_calories = history_meal.calories_kcal
    old_protein = history_meal.protein_grams

    form = HistoryNoteForm(request.POST, instance=history_meal)

    if form.is_valid():
        meal = form.save(commit=False)
        new_portions = meal.portions_saved or 1
        meal.ingredients_saved_kg = round(new_portions * 0.2, 1)
        if new_portions != old_portions:
            meal.calories_kcal, meal.protein_grams = scale_nutrition(
                old_calories, old_protein, old_portions, new_portions
            )
        meal.save()
        metrics = _compute_metrics(_get_meals(request, 'HISTORY', apply_filter=False))
        return JsonResponse({
            'success': True,
            'meal_id': meal.id,
            'notes': meal.notes,
            'portions_saved': meal.portions_saved,
            'calories_kcal': meal.calories_kcal,
            'protein_grams': meal.protein_grams,
            'metrics': metrics,
        })

    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def delete_meal(request, meal_id):
    meal = get_object_or_404(SavedMeal, id=meal_id, user=request.user)
    meal.delete()

    metrics = _compute_metrics(_get_meals(request, 'HISTORY', apply_filter=False))
    return JsonResponse({
        'success': True,
        'meal_id': meal_id,
        'metrics': metrics,
    })
