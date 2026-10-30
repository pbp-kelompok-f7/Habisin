import os
import uuid

from django.conf import settings
from django.db import models


def photo_upload_path(instance, filename):
    # Nama file diacak supaya tidak bentrok dan tidak bisa menebak file user lain
    ext = os.path.splitext(filename)[1].lower()
    return f"profiles/{instance.user_id}/{uuid.uuid4().hex}{ext}"


class Profile(models.Model):
    """Data tambahan user. Dibuat hanya saat user pertama kali menyimpan Edit Profile,
    jadi secara default user tidak punya profile (dan tidak punya foto)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    photo = models.ImageField(upload_to=photo_upload_path, blank=True)

    def __str__(self):
        return f"Profile of {self.user}"

    def replace_photo(self, uploaded):
        if self.photo:
            self.photo.delete(save=False)  # hapus file lama dari disk
        self.photo.save(uploaded.name, uploaded, save=True)

    def remove_photo(self):
        if self.photo:
            self.photo.delete(save=True)