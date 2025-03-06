from django.db import models
from django.utils import timezone
from apps.users.models import User

# Create your models here.

class TrackingCompany(models.Model):
    """
    Модель для хранения информации о транспортных компаниях,
    которые осуществляют доставку товаров.
    """
    name = models.CharField(max_length=100, verbose_name='Название компании')
    code = models.CharField(max_length=50, unique=True, verbose_name='Код компании')
    website = models.URLField(blank=True, null=True, verbose_name='Веб-сайт')
    api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name='API ключ')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    
    class Meta:
        verbose_name = 'Транспортная компания'
        verbose_name_plural = 'Транспортные компании'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class TrackingNumber(models.Model):
    """
    Модель для хранения трек-номеров отправлений.
    """
    STATUS_CHOICES = (
        ('pending', 'Ожидает отправки'),
        ('shipped', 'Отправлено'),
        ('in_transit', 'В пути'),
        ('customs', 'На таможне'),
        ('arrived', 'Прибыло в страну назначения'),
        ('delivered', 'Доставлено'),
        ('returned', 'Возвращено'),
        ('lost', 'Утеряно'),
        ('unknown', 'Статус неизвестен'),
    )
    
    number = models.CharField(max_length=100, unique=True, verbose_name='Трек-номер')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tracking_numbers', verbose_name='Пользователь')
    company = models.ForeignKey(TrackingCompany, on_delete=models.SET_NULL, null=True, blank=True, related_name='tracking_numbers', verbose_name='Транспортная компания')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    
    # Статус и даты
    current_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Текущий статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    # Даты отслеживания
    shipped_date = models.DateTimeField(blank=True, null=True, verbose_name='Дата отправки')
    estimated_delivery = models.DateTimeField(blank=True, null=True, verbose_name='Ожидаемая дата доставки')
    delivered_date = models.DateTimeField(blank=True, null=True, verbose_name='Дата доставки')
    
    # Флаги
    is_archived = models.BooleanField(default=False, verbose_name='В архиве')
    is_problematic = models.BooleanField(default=False, verbose_name='Проблемная доставка')
    
    class Meta:
        verbose_name = 'Трек-номер'
        verbose_name_plural = 'Трек-номера'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.number} ({self.get_current_status_display()})"
    
    def update_status(self, status, location=None, details=None):
        """
        Обновляет статус трек-номера и создает запись в истории.
        """
        if status in dict(self.STATUS_CHOICES).keys():
            old_status = self.current_status
            self.current_status = status
            
            # Обновление дат в зависимости от статуса
            if status == 'shipped' and not self.shipped_date:
                self.shipped_date = timezone.now()
            elif status == 'delivered' and not self.delivered_date:
                self.delivered_date = timezone.now()
            
            self.save()
            
            # Создание записи в истории
            TrackingHistory.objects.create(
                tracking_number=self,
                status=status,
                previous_status=old_status,
                location=location,
                details=details
            )
            
            return True
        return False


class TrackingHistory(models.Model):
    """
    Модель для хранения истории изменений статуса трек-номера.
    """
    tracking_number = models.ForeignKey(TrackingNumber, on_delete=models.CASCADE, related_name='history', verbose_name='Трек-номер')
    status = models.CharField(max_length=20, choices=TrackingNumber.STATUS_CHOICES, verbose_name='Статус')
    previous_status = models.CharField(max_length=20, choices=TrackingNumber.STATUS_CHOICES, blank=True, null=True, verbose_name='Предыдущий статус')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время изменения')
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name='Местоположение')
    details = models.TextField(blank=True, null=True, verbose_name='Детали')
    
    class Meta:
        verbose_name = 'История трекинга'
        verbose_name_plural = 'История трекинга'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.tracking_number.number} - {self.get_status_display()} ({self.timestamp.strftime('%d.%m.%Y %H:%M')})"


class TrackingNotification(models.Model):
    """
    Модель для хранения уведомлений об изменении статуса трек-номера.
    """
    tracking_number = models.ForeignKey(TrackingNumber, on_delete=models.CASCADE, related_name='notifications', verbose_name='Трек-номер')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tracking_notifications', verbose_name='Пользователь')
    message = models.TextField(verbose_name='Сообщение')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Уведомление о трекинге'
        verbose_name_plural = 'Уведомления о трекинге'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Уведомление для {self.user.username} о {self.tracking_number.number}"
