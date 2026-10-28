from django import forms
from .models import Comment

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 3,
                "maxlength": 1000,
                "placeholder": "Bagikan tips atau variasi bahan yang kamu pakai...",
                "class": "cm-textarea",
            }),
        }
        labels = {"content": "Tulis komentar"}
        error_messages = {
            "content": {
                "required": "Komentar tidak boleh kosong.",
                "max_length": "Komentar maksimal 1000 karakter.",
            },
        }

    def clean_content(self):
        content = self.cleaned_data["content"].strip()
        if not content:
            raise forms.ValidationError("Komentar tidak boleh kosong.")
        return content