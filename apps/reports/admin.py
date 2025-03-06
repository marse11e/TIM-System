from django.contrib import admin
from django.utils.html import format_html
from .models import ReportTemplate, Report, ScheduledReport, Dashboard


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'report_type', 'default_format', 'created_by', 'created_at', 'is_active')
    list_filter = ('report_type', 'default_format', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'query')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'report_type', 'is_active')
        }),
        ('Настройки шаблона', {
            'fields': ('template_file', 'default_format')
        }),
        ('Конфигурация', {
            'fields': ('query', 'configuration'),
            'classes': ('collapse',)
        }),
        ('Метаданные', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если это новый объект
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'status', 'file_format', 'created_by', 'created_at', 'download_link')
    list_filter = ('status', 'file_format', 'created_at', 'template')
    search_fields = ('name', 'description', 'created_by__username')
    readonly_fields = ('created_at', 'completed_at', 'status', 'error_message', 'report_file')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'template')
        }),
        ('Параметры отчета', {
            'fields': ('parameters', 'date_range_start', 'date_range_end', 'file_format')
        }),
        ('Результат', {
            'fields': ('status', 'error_message', 'report_file')
        }),
        ('Метаданные', {
            'fields': ('created_by', 'created_at', 'completed_at')
        }),
    )
    
    def download_link(self, obj):
        if obj.report_file:
            return format_html('<a href="{}" target="_blank">Скачать</a>', obj.report_file.url)
        return '-'
    download_link.short_description = 'Скачать отчет'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если это новый объект
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['regenerate_reports']
    
    def regenerate_reports(self, request, queryset):
        for report in queryset:
            report.status = 'pending'
            report.save()
    regenerate_reports.short_description = "Перегенерировать выбранные отчеты"


@admin.register(ScheduledReport)
class ScheduledReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'frequency', 'time_of_day', 'is_active', 'last_run')
    list_filter = ('frequency', 'is_active', 'created_at')
    search_fields = ('name', 'template__name')
    filter_horizontal = ('recipients',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'template', 'is_active')
        }),
        ('Расписание', {
            'fields': ('frequency', 'day_of_week', 'day_of_month', 'time_of_day')
        }),
        ('Настройки отчета', {
            'fields': ('parameters', 'file_format')
        }),
        ('Получатели', {
            'fields': ('recipients', 'send_email')
        }),
        ('Метаданные', {
            'fields': ('created_by', 'created_at', 'last_run')
        }),
    )
    
    readonly_fields = ('created_at', 'last_run')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если это новый объект
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['activate_schedules', 'deactivate_schedules', 'run_now']
    
    def activate_schedules(self, request, queryset):
        queryset.update(is_active=True)
    activate_schedules.short_description = "Активировать выбранные расписания"
    
    def deactivate_schedules(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_schedules.short_description = "Деактивировать выбранные расписания"
    
    def run_now(self, request, queryset):
        # Здесь будет логика для немедленного запуска генерации отчета
        pass
    run_now.short_description = "Запустить генерацию сейчас"


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_public', 'created_at', 'updated_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('name', 'description', 'owner__username')
    filter_horizontal = ('shared_with',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'owner')
        }),
        ('Настройки', {
            'fields': ('layout', 'configuration')
        }),
        ('Доступ', {
            'fields': ('is_public', 'shared_with')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если это новый объект
            obj.owner = request.user
        super().save_model(request, obj, form, change)
