from django import forms

from .models import InventoryItem


def capitalize_words(value):
    return " ".join(word.capitalize() for word in value.split())


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ["name", "amount", "unit", "place"]
        error_messages = {
            "name": {
                "required": "Item name is required.",
                "max_length": "Item name must be 80 characters or fewer.",
            },
            "amount": {
                "required": "Amount is required.",
                "invalid": "Amount must be a number.",
                "max_digits": "Amount is too large.",
                "max_whole_digits": "Amount is too large.",
                "max_decimal_places": "Use at most 2 decimal places.",
            },
            "unit": {
                "required": "Choose a unit.",
                "invalid_choice": "Invalid unit.",
            },
            "place": {
                "required": "Choose a storage location.",
                "invalid_choice": "Invalid location.",
            },
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = capitalize_words(self.cleaned_data["name"])
        if not name:
            raise forms.ValidationError("Item name is required.")

        if self.user is not None:
            duplicates = InventoryItem.objects.filter(user=self.user, name__iexact=name)
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            existing = duplicates.first()
            if existing:
                raise forms.ValidationError(
                    f"{existing.name} is already in your {existing.get_place_display()}. "
                    "Use a different name or update the existing item."
                )
        return name

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than 0.")
        return amount