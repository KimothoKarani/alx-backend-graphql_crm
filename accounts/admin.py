from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    """
    Admin configuration for CustomUser.
    Extends the default UserAdmin to work with your custom model.
    """
    model = CustomUser

    # If you add custom fields later, include them here:
    # fieldsets = UserAdmin.fieldsets + (
    #     ('Additional Info', {'fields': ('phone_number', 'date_of_birth', 'avatar')}),
    # )
    # add_fieldsets = UserAdmin.add_fieldsets + (
    #     ('Additional Info', {'fields': ('phone_number', 'date_of_birth')}),
    # )

admin.site.register(CustomUser, CustomUserAdmin)
