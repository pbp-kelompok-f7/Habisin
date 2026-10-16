from django import forms
from django.contrib.auth import authenticate, get_user_model

User = get_user_model()


class LoginForm(forms.Form):
    email = forms.EmailField(error_messages={
        "required": "Please enter your email.",
        "invalid": "Please enter a valid email address.",
    })
    password = forms.CharField(error_messages={"required": "Please enter your password."})

    def clean(self):
        data = super().clean()
        email, password = data.get("email"), data.get("password")
        if email and password:
            account = User.objects.filter(email__iexact=email).first()
            user = authenticate(username=account.username, password=password) if account else None
            if user is None:
                raise forms.ValidationError("Email or password is incorrect.")
            data["user"] = user
        return data