from django import forms

from .models import InventoryItem


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

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if not name:
            raise forms.ValidationError("Item name is required.")
        return name

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than 0.")
        return amount