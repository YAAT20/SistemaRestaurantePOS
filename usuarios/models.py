from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    ROL_MOZO = 'MOZO'
    ROL_ADMIN = 'ADMIN'

    ROLES = [
        (ROL_MOZO, 'Mozo'),
        (ROL_ADMIN, 'Administrador'),
    ]

    rol = models.CharField(max_length=20, choices=ROLES)
    
    def __str__(self):
        return self.username