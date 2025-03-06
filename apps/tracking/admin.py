from django.contrib import admin
from .models import TrackingCompany, TrackingNumber, TrackingHistory, TrackingNotification


@admin.register(TrackingCompany)
class TrackingCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'website', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ('name',)


class TrackingHistoryInline(admin.TabularInline):
    model = TrackingHistory
    extra = 0
    readonly_fields = ('timestamp', 'status', 'previous_status', 'location', 'details')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class TrackingNotificationInline(admin.TabularInline):
    model = TrackingNotification
    extra = 0
    readonly_fields = ('created_at', 'message', 'is_read')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(TrackingNumber)
class TrackingNumberAdmin(admin.ModelAdmin):
    list_display = ('number', 'user', 'company', 'current_status', 'created_at', 'updated_at', 'is_archived', 'is_problematic')
    list_filter = ('current_status', 'company', 'is_archived', 'is_problematic', 'created_at')
    search_fields = ('number', 'user__username', 'user__email', 'description')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    inlines = [TrackingHistoryInline, TrackingNotificationInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('number', 'user', 'company', 'description')
        }),
        ('Статус', {
            'fields': ('current_status', 'is_archived', 'is_problematic')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at', 'shipped_date', 'estimated_delivery', 'delivered_date')
        }),
    )
    
    actions = ['mark_as_archived', 'mark_as_problematic', 'mark_as_delivered']
    
    def mark_as_archived(self, request, queryset):
        queryset.update(is_archived=True)
    mark_as_archived.short_description = "Отметить как архивные"
    
    def mark_as_problematic(self, request, queryset):
        queryset.update(is_problematic=True)
    mark_as_problematic.short_description = "Отметить как проблемные"
    
    def mark_as_delivered(self, request, queryset):
        for tracking in queryset:
            tracking.update_status('delivered', details='Отмечено как доставлено через админ-панель')
    mark_as_delivered.short_description = "Отметить как доставленные"


@admin.register(TrackingHistory)
class TrackingHistoryAdmin(admin.ModelAdmin):
    list_display = ('tracking_number', 'status', 'previous_status', 'timestamp', 'location')
    list_filter = ('status', 'timestamp')
    search_fields = ('tracking_number__number', 'location', 'details')
    readonly_fields = ('tracking_number', 'status', 'previous_status', 'timestamp', 'location', 'details')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(TrackingNotification)
class TrackingNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'tracking_number', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'tracking_number__number', 'message')
    readonly_fields = ('tracking_number', 'user', 'message', 'created_at')
    date_hierarchy = 'created_at'
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Отметить как прочитанные"
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = "Отметить как непрочитанные"
    
    def has_add_permission(self, request):
        return False
