from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Расширенная модель пользователя для системы управления складом.
    Включает дополнительные поля и роли для работы с Telegram-ботом.
    """
    
    # Роли пользователей
    ROLE_CHOICES = (
        ('admin', 'Администратор'),
        ('observer', 'Наблюдатель'),
        ('user', 'Пользователь'),
        ('accountant', 'Бухгалтер'),
        ('warehouse', 'Кладовщик'),
    )
    
    # Основные поля
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user', verbose_name='Роль')
    telegram_id = models.CharField(max_length=50, blank=True, null=True, unique=True, verbose_name='Telegram ID')
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name='Номер телефона')
    
    # Дополнительные поля для работы с системой
    is_verified = models.BooleanField(default=False, verbose_name='Верифицирован')
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_accountant(self):
        return self.role == 'accountant'
    
    @property
    def is_warehouse(self):
        return self.role == 'warehouse'


class UserActivity(models.Model):
    """
    Модель для отслеживания активности пользователей в системе.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities', verbose_name='Пользователь')
    action = models.CharField(max_length=255, verbose_name='Действие')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время')
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP-адрес')
    
    class Meta:
        verbose_name = 'Активность пользователя'
        verbose_name_plural = 'Активности пользователей'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} - {self.action} ({self.timestamp.strftime('%d.%m.%Y %H:%M')})"



