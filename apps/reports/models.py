from django.db import models
from django.utils import timezone
from apps.users.models import User

# Create your models here.

class ReportTemplate(models.Model):
    """
    Модель для хранения шаблонов отчетов.
    """
    REPORT_TYPES = (
        ('inventory', 'Отчет по складу'),
        ('orders', 'Отчет по заказам'),
        ('tracking', 'Отчет по трекингу'),
        ('finance', 'Финансовый отчет'),
        ('custom', 'Пользовательский отчет'),
    )
    
    FORMAT_CHOICES = (
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
    )
    
    name = models.CharField(max_length=100, verbose_name='Название шаблона')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, verbose_name='Тип отчета')
    
    # Настройки шаблона
    template_file = models.FileField(upload_to='report_templates/', blank=True, null=True, verbose_name='Файл шаблона')
    default_format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='excel', verbose_name='Формат по умолчанию')
    
    # SQL-запрос или конфигурация для генерации отчета
    query = models.TextField(blank=True, null=True, verbose_name='SQL-запрос')
    configuration = models.JSONField(blank=True, null=True, verbose_name='Конфигурация')
    
    # Метаданные
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_templates', verbose_name='Создатель')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    
    class Meta:
        verbose_name = 'Шаблон отчета'
        verbose_name_plural = 'Шаблоны отчетов'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"


class Report(models.Model):
    """
    Модель для хранения сгенерированных отчетов.
    """
    STATUS_CHOICES = (
        ('pending', 'В очереди'),
        ('processing', 'Обрабатывается'),
        ('completed', 'Завершен'),
        ('failed', 'Ошибка'),
    )
    
    template = models.ForeignKey(ReportTemplate, on_delete=models.SET_NULL, null=True, related_name='reports', verbose_name='Шаблон')
    name = models.CharField(max_length=100, verbose_name='Название отчета')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    
    # Параметры отчета
    parameters = models.JSONField(blank=True, null=True, verbose_name='Параметры')
    date_range_start = models.DateTimeField(blank=True, null=True, verbose_name='Начало периода')
    date_range_end = models.DateTimeField(blank=True, null=True, verbose_name='Конец периода')
    
    # Файл отчета
    report_file = models.FileField(upload_to='reports/', blank=True, null=True, verbose_name='Файл отчета')
    file_format = models.CharField(max_length=10, choices=ReportTemplate.FORMAT_CHOICES, verbose_name='Формат файла')
    
    # Статус и метаданные
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    error_message = models.TextField(blank=True, null=True, verbose_name='Сообщение об ошибке')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reports', verbose_name='Создатель')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата завершения')
    
    class Meta:
        verbose_name = 'Отчет'
        verbose_name_plural = 'Отчеты'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.created_at.strftime('%d.%m.%Y')})"
    
    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)


class ScheduledReport(models.Model):
    """
    Модель для хранения расписания автоматической генерации отчетов.
    """
    FREQUENCY_CHOICES = (
        ('daily', 'Ежедневно'),
        ('weekly', 'Еженедельно'),
        ('monthly', 'Ежемесячно'),
        ('quarterly', 'Ежеквартально'),
    )
    
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='schedules', verbose_name='Шаблон')
    name = models.CharField(max_length=100, verbose_name='Название')
    
    # Настройки расписания
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, verbose_name='Частота')
    day_of_week = models.IntegerField(blank=True, null=True, verbose_name='День недели (1-7)')
    day_of_month = models.IntegerField(blank=True, null=True, verbose_name='День месяца')
    time_of_day = models.TimeField(verbose_name='Время генерации')
    
    # Настройки отчета
    parameters = models.JSONField(blank=True, null=True, verbose_name='Параметры')
    file_format = models.CharField(max_length=10, choices=ReportTemplate.FORMAT_CHOICES, verbose_name='Формат файла')
    
    # Получатели отчета
    recipients = models.ManyToManyField(User, related_name='scheduled_reports', verbose_name='Получатели')
    send_email = models.BooleanField(default=True, verbose_name='Отправлять по email')
    
    # Метаданные
    is_active = models.BooleanField(default=True, verbose_name='Активно')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_schedules', verbose_name='Создатель')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    last_run = models.DateTimeField(blank=True, null=True, verbose_name='Последний запуск')
    
    class Meta:
        verbose_name = 'Запланированный отчет'
        verbose_name_plural = 'Запланированные отчеты'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class Dashboard(models.Model):
    """
    Модель для хранения настроек дашбордов.
    """
    name = models.CharField(max_length=100, verbose_name='Название дашборда')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    
    # Настройки дашборда
    layout = models.JSONField(blank=True, null=True, verbose_name='Макет')
    configuration = models.JSONField(blank=True, null=True, verbose_name='Конфигурация')
    
    # Доступ
    is_public = models.BooleanField(default=False, verbose_name='Публичный')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboards', verbose_name='Владелец')
    shared_with = models.ManyToManyField(User, related_name='shared_dashboards', blank=True, verbose_name='Доступен для')
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Дашборд'
        verbose_name_plural = 'Дашборды'
        ordering = ['name']
    
    def __str__(self):
        return self.name
