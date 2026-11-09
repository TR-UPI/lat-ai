
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    ordering = ("email",)

    list_display = (
        "email",
        "display_name",
        "role",
        "is_active",
        "is_staff",
        "date_joined",
    )

    list_filter = (
        "role",
        "is_active",
        "is_staff",
        "date_joined",
    )

    search_fields = (
        "email",
        "username",
        "display_name",
    )

    list_per_page = 25

    fieldsets = (
        ("Учётная запись", {
            "fields": (
                "email",
                "username",
                "password",
            )
        }),
        ("Информация о пользователе", {
            "fields": (
                "display_name",
                "role",
                "first_name",
                "last_name",
            )
        }),
        ("Права доступа", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Даты", {
            "fields": (
                "last_login",
                "date_joined",
            )
        }),
    )

    add_fieldsets = (
        ("Создание пользователя", {
            "classes": ("wide",),
            "fields": (
                "username",
                "email",
                "display_name",
                "role",
                "password1",
                "password2",
            ),
        }),
    )

    readonly_fields = (
        "last_login",
        "date_joined",
    )
