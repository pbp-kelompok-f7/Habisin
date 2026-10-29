import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Sum, Q
from django.contrib import messages
from .models import SavedMeal
from .spoonacular import (
    get_recipe_by_id,
    seed_default_meals_if_empty,
)

def _get_history_queryset(request):
    """Retrieve history meals for current user or default unassigned meals."""
    if request.user.is_authenticated:
        qs = SavedMeal.objects.filter(status='HISTORY').filter(
            Q(user=request.user) | Q(user__isnull=True)
        )
    else:
        qs = SavedMeal.objects.filter(status='HISTORY')
    return qs.order_by('-updated_at', '-created_at')

def _get_saved_queryset(request):
    """Retrieve saved meals for current user or default unassigned meals."""
    if request.user.is_authenticated:
        qs = SavedMeal.objects.filter(status='SAVED').filter(
            Q(user=request.user) | Q(user__isnull=True)
        )
    else:
        qs = SavedMeal.objects.filter(status='SAVED')
    return qs.order_by('-created_at')

def _compute_metrics(history_meals):
    """Compute aggregated impact stats with default fallbacks."""
    portions_agg = history_meals.aggregate(total=Sum('portions_saved'))['total']
    total_portions = portions_agg if portions_agg is not None else 7

    weight_agg = history_meals.aggregate(total=Sum('ingredients_saved_kg'))['total']
    total_weight = round(weight_agg, 1) if weight_agg is not None else 1.3

    history_count = history_meals.count()
    recipes_finished = history_count if history_count > 0 else 3

    protein_agg = history_meals.aggregate(total=Sum('protein_grams'))['total']
    total_protein = protein_agg if protein_agg is not None else 23

    calories_agg = history_meals.aggregate(total=Sum('calories_kcal'))['total']
    total_calories = calories_agg if calories_agg is not None else 2000

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

    saved_meals = _get_saved_queryset(request)
    history_meals = _get_history_queryset(request)
    metrics = _compute_metrics(history_meals)

    context = {
        **metrics,
        'saved_meals': saved_meals,
        'history_meals': history_meals,
    }
    return render(request, "saved_meals/index.html", context)

@require_POST
def mark_meal_done(request, meal_id):
    """
    Handle marking a saved meal as done/cooked:
    - If recipe already exists in history, increment portions and delete saved instance.
    - If new, transition status to HISTORY.
    """
    saved_meal = get_object_or_404(SavedMeal, id=meal_id, status='SAVED')

    current_user = request.user if request.user.is_authenticated else None
    recipe_id = saved_meal.recipe_id

    # Check for existing history record with same recipe_id or name
    history_qs = SavedMeal.objects.filter(status='HISTORY')
    if current_user:
        history_qs = history_qs.filter(Q(user=current_user) | Q(user__isnull=True))
    else:
        history_qs = history_qs.filter(user__isnull=True)

    existing_history = None
    if recipe_id:
        existing_history = history_qs.filter(recipe_id=recipe_id).first()
    if not existing_history and saved_meal.recipe_name:
        existing_history = history_qs.filter(recipe_name__iexact=saved_meal.recipe_name).first()

    if existing_history:
        # Increment portion count and nutritional metrics
        existing_history.portions_saved += saved_meal.portions_saved
        existing_history.ingredients_saved_kg = round(
            existing_history.ingredients_saved_kg + saved_meal.ingredients_saved_kg, 1
        )
        existing_history.protein_grams += saved_meal.protein_grams
        existing_history.calories_kcal += saved_meal.calories_kcal
        if current_user and not existing_history.user:
            existing_history.user = current_user
        existing_history.save()

        # Remove from saved meals
        saved_meal.delete()

        action = 'incremented'
        history_meal = existing_history
    else:
        # Move saved meal to history
        saved_meal.status = 'HISTORY'
        if current_user:
            saved_meal.user = current_user
        saved_meal.save()

        action = 'created'
        history_meal = saved_meal

    updated_history = _get_history_queryset(request)
    metrics = _compute_metrics(updated_history)

    meal_payload = {
        'id': history_meal.id,
        'recipe_name': history_meal.recipe_name,
        'ingredients': history_meal.ingredients or '-',
        'portions': history_meal.portions_saved,
        'notes': history_meal.notes or '-',
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({
            'success': True,
            'action': action,
            'history_meal_id': history_meal.id,
            'new_portions': history_meal.portions_saved,
            'meal': meal_payload,
            'metrics': metrics,
        })

    return redirect('saved_meals:show_saved_meals')

@require_POST
def edit_history_note(request, meal_id):
    """Update notes for a history meal entry."""
    history_meal = get_object_or_404(SavedMeal, id=meal_id, status='HISTORY')

    # Parse notes from form-encoded POST or JSON
    notes = ''
    if request.content_type == 'application/json':
        try:
            body = json.loads(request.body)
            notes = body.get('notes', '')
        except Exception:
            pass
    else:
        notes = request.POST.get('notes', '')

    history_meal.notes = notes.strip()
    history_meal.save()

    return JsonResponse({
        'success': True,
        'meal_id': history_meal.id,
        'notes': history_meal.notes,
    })

@require_POST
def delete_history_meal(request, meal_id):
    """Delete a history record."""
    history_meal = get_object_or_404(SavedMeal, id=meal_id, status='HISTORY')
    history_meal.delete()

    updated_history = _get_history_queryset(request)
    metrics = _compute_metrics(updated_history)

    return JsonResponse({
        'success': True,
        'meal_id': meal_id,
        'metrics': metrics,
    })

def save_recipe(request, recipe_id):
    """Add a recipe from Spoonacular catalog to user's saved meals."""
    recipe_data = get_recipe_by_id(recipe_id)
    if not recipe_data:
        messages.error(request, 'Resep tidak ditemukan.')
        return redirect('saved_meals:show_saved_meals')

    user = request.user if request.user.is_authenticated else None

    # Create new saved meal
    SavedMeal.objects.create(
        user=user,
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
