from datetime import timezone

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, F
from .models import Warehouse, InventoryItem, InventoryTransaction, Inventory, InventoryCount


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'contact_person', 'phone', 'is_active', 'item_count', 'total_value')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'address', 'contact_person', 'phone', 'email')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'address', 'description', 'is_active')
        }),
        ('Контактная информация', {
            'fields': ('contact_person', 'phone', 'email')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def item_count(self, obj):
        """
        Возвращает количество различных товаров на складе.
        """
        return obj.inventory_items.count()
    item_count.short_description = 'Кол-во товаров'
    
    def total_value(self, obj):
        """
        Возвращает общую стоимость всех товаров на складе.
        """
        total = obj.inventory_items.aggregate(
            total=Sum(F('quantity') * F('unit_cost'))
        )['total'] or 0
        return f"{total:.2f} руб."
    total_value.short_description = 'Общая стоимость'


class InventoryItemInline(admin.TabularInline):
    model = InventoryItem
    extra = 0
    fields = ('product', 'quantity', 'reserved_quantity', 'available_quantity', 'unit_cost', 'total_value', 'location')
    readonly_fields = ('available_quantity', 'total_value')
    
    def available_quantity(self, obj):
        return obj.available_quantity
    available_quantity.short_description = 'Доступно'
    
    def total_value(self, obj):
        return f"{obj.total_value:.2f} руб."
    total_value.short_description = 'Общая стоимость'


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity', 'reserved_quantity', 'available_quantity', 'unit_cost', 'total_value', 'last_updated')
    list_filter = ('warehouse', 'last_updated')
    search_fields = ('product__name', 'product__sku', 'warehouse__name', 'location')
    readonly_fields = ('available_quantity', 'total_value', 'last_updated')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('product', 'warehouse', 'location')
        }),
        ('Количество и стоимость', {
            'fields': ('quantity', 'reserved_quantity', 'available_quantity', 'unit_cost', 'total_value')
        }),
        ('Метаданные', {
            'fields': ('last_updated',)
        }),
    )
    
    def available_quantity(self, obj):
        return obj.available_quantity
    available_quantity.short_description = 'Доступно'
    
    def total_value(self, obj):
        return f"{obj.total_value:.2f} руб."
    total_value.short_description = 'Общая стоимость'
    
    actions = ['reserve_items', 'release_items']
    
    def reserve_items(self, request, queryset):
        for item in queryset:
            if item.available_quantity > 0:
                InventoryTransaction.objects.create(
                    transaction_type='reservation',
                    product=item.product,
                    source_warehouse=item.warehouse,
                    quantity=1,  # Резервируем по 1 единице
                    unit_cost=item.unit_cost,
                    created_by=request.user,
                    notes='Резервирование через админ-панель'
                )
    reserve_items.short_description = "Зарезервировать по 1 единице"
    
    def release_items(self, request, queryset):
        for item in queryset:
            if item.reserved_quantity > 0:
                InventoryTransaction.objects.create(
                    transaction_type='release',
                    product=item.product,
                    source_warehouse=item.warehouse,
                    quantity=1,  # Освобождаем по 1 единице
                    unit_cost=item.unit_cost,
                    created_by=request.user,
                    notes='Освобождение резерва через админ-панель'
                )
    release_items.short_description = "Освободить по 1 единице из резерва"


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'product', 'quantity', 'source_warehouse', 'destination_warehouse', 'timestamp', 'created_by')
    list_filter = ('transaction_type', 'source_warehouse', 'destination_warehouse', 'timestamp')
    search_fields = ('product__name', 'product__sku', 'notes')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('transaction_type', 'product', 'quantity', 'unit_cost')
        }),
        ('Склады', {
            'fields': ('source_warehouse', 'destination_warehouse')
        }),
        ('Связи', {
            'fields': ('order',)
        }),
        ('Дополнительная информация', {
            'fields': ('notes', 'created_by', 'timestamp')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если это новый объект
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class InventoryCountInline(admin.TabularInline):
    model = InventoryCount
    extra = 0
    fields = ('product', 'expected_quantity', 'actual_quantity', 'discrepancy', 'counted_by', 'counted_at', 'notes')
    readonly_fields = ('discrepancy', 'counted_at')
    
    def discrepancy(self, obj):
        diff = obj.discrepancy
        if diff > 0:
            return format_html('<span style="color: green;">+{}</span>', diff)
        elif diff < 0:
            return format_html('<span style="color: red;">{}</span>', diff)
        return '0'
    discrepancy.short_description = 'Расхождение'


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('inventory_number', 'warehouse', 'status', 'created_by', 'created_at', 'start_date', 'end_date')
    list_filter = ('status', 'warehouse', 'created_at')
    search_fields = ('inventory_number', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    inlines = [InventoryCountInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('inventory_number', 'warehouse', 'status', 'notes')
        }),
        ('Даты', {
            'fields': ('start_date', 'end_date', 'created_at', 'updated_at')
        }),
        ('Метаданные', {
            'fields': ('created_by',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если это новый объект
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['start_inventory', 'complete_inventory', 'cancel_inventory']
    
    def start_inventory(self, request, queryset):
        queryset.filter(status='draft').update(status='in_progress', start_date=timezone.now())
    start_inventory.short_description = "Начать инвентаризацию"
    
    def complete_inventory(self, request, queryset):
        queryset.filter(status='in_progress').update(status='completed', end_date=timezone.now())
    complete_inventory.short_description = "Завершить инвентаризацию"
    
    def cancel_inventory(self, request, queryset):
        queryset.exclude(status='completed').update(status='cancelled')
    cancel_inventory.short_description = "Отменить инвентаризацию"


@admin.register(InventoryCount)
class InventoryCountAdmin(admin.ModelAdmin):
    list_display = ('inventory', 'product', 'expected_quantity', 'actual_quantity', 'discrepancy', 'counted_by', 'counted_at')
    list_filter = ('inventory', 'counted_at')
    search_fields = ('inventory__inventory_number', 'product__name', 'product__sku', 'notes')
    readonly_fields = ('discrepancy', 'counted_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('inventory', 'product')
        }),
        ('Количество', {
            'fields': ('expected_quantity', 'actual_quantity', 'discrepancy')
        }),
        ('Метаданные', {
            'fields': ('counted_by', 'counted_at', 'notes')
        }),
    )
    
    def discrepancy(self, obj):
        diff = obj.discrepancy
        if diff > 0:
            return format_html('<span style="color: green;">+{}</span>', diff)
        elif diff < 0:
            return format_html('<span style="color: red;">{}</span>', diff)
        return '0'
    discrepancy.short_description = 'Расхождение'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если это новый объект
            obj.counted_by = request.user
        super().save_model(request, obj, form, change)
