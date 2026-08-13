from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

#TODO:Déplacer dans manager.py
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model"""

    email = models.EmailField(max_length=255,
                              unique=True,
                              verbose_name='Email')
    
    objects = UserManager()

    # Email comme identifiant
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def save(self, *args, **kwargs):
        # username reste unique et obligatoire via AbstractUser, mais n'est
        # jamais saisi (email fait office d'identifiant) : on le déduit de
        # l'email pour éviter qu'il reste vide et entre en collision.
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name()}"

