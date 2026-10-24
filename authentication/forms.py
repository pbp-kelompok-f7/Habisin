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
            # Login memakai email: cari user dari email, lalu cek password lewat username-nya
            account = User.objects.filter(email__iexact=email).first()
            user = authenticate(username=account.username, password=password) if account else None
            if user is None:
                raise forms.ValidationError(
                    "We couldn't sign you in. Check your email and password and try again."
                )
            data["user"] = user
        return data


class RegisterForm(forms.Form):
    name = forms.CharField(max_length=60, error_messages={"required": "Please enter your name."})
    email = forms.EmailField(error_messages={
        "required": "Please enter your email.",
        "invalid": "Please enter a valid email address.",
    })
    password = forms.CharField(min_length=8, error_messages={
        "required": "Please enter a password.",
        "min_length": "Password must be at least 8 characters.",
    })
    confirm_password = forms.CharField(error_messages={"required": "Please confirm your password."})

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean(self):
        data = super().clean()
        p, c = data.get("password"), data.get("confirm_password")
        if p and c and p != c:
            self.add_error("confirm_password", "Passwords do not match.")
        return data

    def save(self):
        d = self.cleaned_data
        # Username dibuat otomatis dari email (login tetap memakai email)
        base = d["email"].split("@")[0][:140] or "user"
        username, n = base, 1
        while User.objects.filter(username__iexact=username).exists():
            n += 1
            username = f"{base}{n}"
        return User.objects.create_user(
            username=username, email=d["email"], password=d["password"], first_name=d["name"]
        )