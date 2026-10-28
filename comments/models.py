from django.contrib.auth.models import User
from django.db import models

class Comment(models.Model):
    recipe_id = models.PositiveIntegerField(db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recipe_comments")
    content = models.TextField(max_length=1000)
    likes = models.ManyToManyField(User, related_name="liked_comments", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} di resep {self.recipe_id}: {self.content[:30]}"