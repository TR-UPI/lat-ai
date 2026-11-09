
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            username=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):

    username = models.CharField(
        "Имя пользователя",
        max_length=150,
        unique=True
    )

    email = models.EmailField(
        "Электронная почта",
        unique=True
    )

    display_name = models.CharField(
        "Имя ученика",
        max_length=120,
        blank=True
    )

    ROLE_CHOICES = [
        ("student", "Ученик"),
        ("teacher", "Преподаватель"),
        ("admin", "Администратор"),
    ]

    role = models.CharField(
        "Роль пользователя",
        max_length=20,
        choices=ROLE_CHOICES,
        default="student"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.email
