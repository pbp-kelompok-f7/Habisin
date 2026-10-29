from django import forms

from .models import InventoryItem


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ["name", "amount", "unit", "place"]
        error_messages = {
            "name": {
                "required": "Nama bahan wajib diisi.",
                "max_length": "Nama bahan maksimal 80 karakter.",
            },
            "amount": {
                "required": "Jumlah wajib diisi.",
                "invalid": "Jumlah harus berupa angka.",
                "max_digits": "Jumlah terlalu besar.",
                "max_whole_digits": "Jumlah terlalu besar.",
                "max_decimal_places": "Maksimal 2 angka di belakang koma.",
            },
            "unit": {
                "required": "Pilih satuan.",
                "invalid_choice": "Satuan tidak valid.",
            },
            "place": {
                "required": "Pilih lokasi penyimpanan.",
                "invalid_choice": "Lokasi tidak valid.",
            },
        }

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if not name:
            raise forms.ValidationError("Nama bahan wajib diisi.")
        return name

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Jumlah harus lebih dari 0.")
        return amount