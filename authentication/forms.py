from django import forms
from django.contrib.auth import authenticate, get_user_model

from .models import Profile

User = get_user_model()

MAX_PHOTO_BYTES = 2 * 1024 * 1024
PHOTO_EXTENSIONS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


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


class ProfileForm(forms.Form):
    name = forms.CharField(max_length=60, error_messages={
        "required": "Please enter your name.",
        "max_length": "Name must be 60 characters or fewer.",
    })
    photo = forms.ImageField(
        required=False,
        widget=forms.FileInput,
        error_messages={"invalid_image": "Please upload a valid image (JPG, PNG, or WEBP)."},
    )
    remove_photo = forms.BooleanField(required=False)

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if not name:
            raise forms.ValidationError("Please enter your name.")
        return name

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if not photo:
            return None
        if photo.size > MAX_PHOTO_BYTES:
            raise forms.ValidationError("Photo must be 2 MB or smaller.")
        fmt = getattr(getattr(photo, "image", None), "format", None)
        if fmt not in PHOTO_EXTENSIONS:
            raise forms.ValidationError("Photo must be a JPG, PNG, or WEBP image.")
        # Ekstensi ditentukan dari isi file yang sebenarnya, bukan dari nama yang dikirim browser
        photo.name = f"photo.{PHOTO_EXTENSIONS[fmt]}"
        return photo

    def save(self, user):
        data = self.cleaned_data
        user.first_name = data["name"]
        user.save(update_fields=["first_name"])

        photo, remove = data.get("photo"), data.get("remove_photo")
        if photo or remove:
            profile, _ = Profile.objects.get_or_create(user=user)
            if photo:
                profile.replace_photo(photo)
            else:
                profile.remove_photo()