from django import forms

from .models import Profile

MAX_PHOTO_BYTES = 2 * 1024 * 1024
PHOTO_EXTENSIONS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


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
        return user