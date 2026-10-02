from django.shortcuts import render
from django.db.models import Sum
from .models import SavedMeal

def show_saved_meals(request):
    saved_meals = SavedMeal.objects.filter(status='SAVED').order_by('-created_at')
    history_meals = SavedMeal.objects.filter(status='HISTORY').order_by('-created_at')

    # Aggregated metrics calculation (with fallbacks matching the mockup)
    portions_agg = SavedMeal.objects.aggregate(total=Sum('portions_saved'))['total']
    total_portions = portions_agg if portions_agg is not None else 7

    weight_agg = SavedMeal.objects.aggregate(total=Sum('ingredients_saved_kg'))['total']
    total_weight = weight_agg if weight_agg is not None else 1.3

    history_count = history_meals.count()
    recipes_finished = history_count if history_count > 0 else 3

    protein_agg = SavedMeal.objects.aggregate(total=Sum('protein_grams'))['total']
    total_protein = protein_agg if protein_agg is not None else 23

    calories_agg = SavedMeal.objects.aggregate(total=Sum('calories_kcal'))['total']
    total_calories = calories_agg if calories_agg is not None else 2000

    # Default mockup sample cards if table is empty
    sample_meals = [
        {
            'id': 1,
            'recipe_name': 'Sup Ayam Wortel Kentang',
            'image_url': 'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=800&q=80',
            'cooking_time_minutes': 30,
            'portions_saved': 2,
            'is_favorite': False,
            'status': 'SAVED',
        },
        {
            'id': 2,
            'recipe_name': 'Sup Ayam Wortel Kentang',
            'image_url': 'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=800&q=80',
            'cooking_time_minutes': 30,
            'portions_saved': 2,
            'is_favorite': False,
            'status': 'SAVED',
        },
        {
            'id': 3,
            'recipe_name': 'Sup Ayam Wortel Kentang',
            'image_url': 'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=800&q=80',
            'cooking_time_minutes': 30,
            'portions_saved': 3,
            'is_favorite': False,
            'status': 'SAVED',
        },
    ]

    context = {
        'total_portions': total_portions,
        'total_weight': total_weight,
        'recipes_finished': recipes_finished,
        'total_protein': total_protein,
        'total_calories': total_calories,
        'saved_meals': saved_meals if saved_meals.exists() else sample_meals,
        'history_meals': history_meals if history_meals.exists() else sample_meals,
    }
    return render(request, "saved_meals/index.html", context)
