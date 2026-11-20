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
                "placeholder": "Share your tips or ingredient variations...",
                "class": "cm-textarea",
            }),
        }
        labels = {"content": "Write a comment"}
        error_messages = {
            "content": {
                "required": "Comment cannot be empty.",
                "max_length": "Comment cannot exceed 1000 characters.",
            },
        }

    def clean_content(self):
        content = self.cleaned_data["content"].strip()
        if not content:
            raise forms.ValidationError("Comment cannot be empty.")
        return content
