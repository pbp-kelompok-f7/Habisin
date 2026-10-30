from django import forms
from .models import SavedMeal


class SavedMealForm(forms.ModelForm):
    calories_kcal = forms.IntegerField(min_value=0, required=False)
    protein_grams = forms.IntegerField(min_value=0, required=False)

    class Meta:
        model = SavedMeal
        fields = [
            'recipe_name',
            'ingredients',
            'cooking_time_minutes',
            'portions_saved',
            'calories_kcal',
            'protein_grams',
            'image_url',
            'notes',
        ]


class HistoryNoteForm(forms.ModelForm):
    class Meta:
        model = SavedMeal
        fields = ['notes', 'portions_saved']
