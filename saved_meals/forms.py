from django import forms
from .models import SavedMeal


class SavedMealForm(forms.ModelForm):
    """Form untuk menambahkan menu baru ke Saved Meals (Create/Insert)."""

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
        widgets = {
            'recipe_name': forms.TextInput(attrs={
                'placeholder': 'Contoh: Nasi Goreng Mawut Sisa Kulkas',
                'required': True,
            }),
            'ingredients': forms.TextInput(attrs={
                'placeholder': 'Contoh: Nasi, Telur, Kol, Ayam Suwir',
                'required': True,
            }),
            'cooking_time_minutes': forms.NumberInput(attrs={'min': 1, 'max': 360}),
            'portions_saved': forms.NumberInput(attrs={'min': 1, 'max': 50}),
            'calories_kcal': forms.NumberInput(attrs={'min': 10, 'max': 5000}),
            'protein_grams': forms.NumberInput(attrs={'min': 0, 'max': 500}),
            'image_url': forms.URLInput(attrs={
                'placeholder': 'https://images.unsplash.com/... (opsional)',
            }),
            'notes': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Catatan rencana masak (opsional)...',
            }),
        }

    def clean_recipe_name(self):
        name = (self.cleaned_data.get('recipe_name') or '').strip()
        if not name:
            raise forms.ValidationError('Nama menu wajib diisi.')
        return name

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if user and user.is_authenticated:
            instance.user = user
        instance.status = 'SAVED'
        instance.ingredients_saved_kg = round((instance.portions_saved or 1) * 0.2, 1)
        if commit:
            instance.save()
        return instance


class HistoryNoteForm(forms.ModelForm):

    class Meta:
        model = SavedMeal
        fields = ['notes', 'portions_saved']

    def clean_notes(self):
        return (self.cleaned_data.get('notes') or '').strip()

    def clean_portions_saved(self):
        portions = self.cleaned_data.get('portions_saved')
        if portions is not None and portions < 1:
            raise forms.ValidationError('Jumlah porsi minimal 1.')
        return portions or 1


class SavedMealFilterForm(forms.Form):

    TIME_CHOICES = [
        ('', 'Semua Waktu Masak'),
        ('quick', 'Cepat (≤ 20 menit)'),
        ('medium', 'Sedang (21 - 35 menit)'),
        ('long', 'Lama (> 35 menit)'),
    ]

    CALORIE_CHOICES = [
        ('', 'Semua Kalori'),
        ('low', 'Rendah Kalori (≤ 350 kkal)'),
        ('medium', 'Sedang (351 - 500 kkal)'),
        ('high', 'Tinggi (> 500 kkal)'),
    ]

    SORT_CHOICES = [
        ('newest', 'Terbaru'),
        ('time_asc', 'Waktu Masak Tercepat'),
        ('calories_asc', 'Kalori Terendah'),
        ('portions_desc', 'Porsi Terbanyak'),
    ]

    q = forms.CharField(required=False, max_length=100)
    time_filter = forms.ChoiceField(choices=TIME_CHOICES, required=False)
    calorie_filter = forms.ChoiceField(choices=CALORIE_CHOICES, required=False)
    sort_by = forms.ChoiceField(choices=SORT_CHOICES, required=False)
