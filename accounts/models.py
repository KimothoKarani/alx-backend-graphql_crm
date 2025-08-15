from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    """
    Custom user model that extends Django's AbstractUser.
    Start with this even if you don't need customizations yet.
    """

    # You can add custom fields here in the future
    # For now, this inherits all default User fields and behavior

    # Example custom fields you might add later:
    # phone_number = models.CharField(max_length=15, blank=True)
    # date_of_birth = models.DateField(null=True, blank=True)
    # avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return self.username