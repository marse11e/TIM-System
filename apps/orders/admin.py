from django.contrib import admin
from django.utils.html import format_html
from .models import Supplier, Product, Order, OrderItem, OrderHistory, Payment


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'contact_person', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'contact_person', 'is_active')
        }),
        ('Контактная информация', {
            'fields': ('email', 'phone', 'address', 'website')
        }),
        ('Дополнительная информация', {
            'fields': ('description',)
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'supplier', 'purchase_price', 'selling_price', 'is_active')
    list_filter = ('is_active', 'supplier', 'created_at')
    search_fields = ('name', 'sku', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'sku', 'description', 'is_active')
        }),
        ('Цены', {
            'fields': ('purchase_price', 'selling_price')
        }),
        ('Связи', {
            'fields': ('supplier',)
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at')
        }),
    )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('subtotal',)
    fields = ('product', 'product_name', 'product_sku', 'quantity', 'unit_price', 'subtotal')


class OrderHistoryInline(admin.TabularInline):
    model = OrderHistory
    extra = 0
    readonly_fields = ('timestamp', 'status', 'previous_status', 'user', 'comment')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('payment_date',)
    fields = ('amount', 'payment_method', 'status', 'transaction_id', 'payment_date', 'notes')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'total_amount', 'paid_amount', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'user__username', 'user__email', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'paid_at', 'shipped_at', 'delivered_at')
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline, PaymentInline, OrderHistoryInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('order_number', 'user', 'status', 'notes')
        }),
        ('Финансовая информация', {
            'fields': ('total_amount', 'paid_amount', 'shipping_cost')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at', 'paid_at', 'shipped_at', 'delivered_at')
        }),
        ('Трекинг', {
            'fields': ('tracking_numbers',)
        }),
    )
    
    filter_horizontal = ('tracking_numbers',)
    
    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            old_obj = Order.objects.get(pk=obj.pk)
            old_status = old_obj.status
        
        super().save_model(request, obj, form, change)
        
        # Создаем запись в истории, если статус изменился
        if change and old_status != obj.status:
            OrderHistory.objects.create(
                order=obj,
                status=obj.status,
                previous_status=old_status,
                user=request.user,
                comment=f"Статус изменен через админ-панель"
            )
    
    actions = ['mark_as_paid', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_cancelled']
    
    def mark_as_paid(self, request, queryset):
        for order in queryset:
            if order.status != 'paid':
                old_status = order.status
                order.status = 'paid'
                order.save()
                
                OrderHistory.objects.create(
                    order=order,
                    status='paid',
                    previous_status=old_status,
                    user=request.user,
                    comment="Отмечено как оплаченное через админ-панель"
                )
    mark_as_paid.short_description = "Отметить как оплаченные"
    
    def mark_as_shipped(self, request, queryset):
        for order in queryset:
            if order.status != 'shipped':
                old_status = order.status
                order.status = 'shipped'
                order.save()
                
                OrderHistory.objects.create(
                    order=order,
                    status='shipped',
                    previous_status=old_status,
                    user=request.user,
                    comment="Отмечено как отправленное через админ-панель"
                )
    mark_as_shipped.short_description = "Отметить как отправленные"
    
    def mark_as_delivered(self, request, queryset):
        for order in queryset:
            if order.status != 'delivered':
                old_status = order.status
                order.status = 'delivered'
                order.save()
                
                OrderHistory.objects.create(
                    order=order,
                    status='delivered',
                    previous_status=old_status,
                    user=request.user,
                    comment="Отмечено как доставленное через админ-панель"
                )
    mark_as_delivered.short_description = "Отметить как доставленные"
    
    def mark_as_cancelled(self, request, queryset):
        for order in queryset:
            if order.status != 'cancelled':
                old_status = order.status
                order.status = 'cancelled'
                order.save()
                
                OrderHistory.objects.create(
                    order=order,
                    status='cancelled',
                    previous_status=old_status,
                    user=request.user,
                    comment="Отмечено как отмененное через админ-панель"
                )
    mark_as_cancelled.short_description = "Отметить как отмененные"


@admin.register(OrderHistory)
class OrderHistoryAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'previous_status', 'timestamp', 'user')
    list_filter = ('status', 'timestamp')
    search_fields = ('order__order_number', 'comment')
    readonly_fields = ('order', 'status', 'previous_status', 'timestamp', 'user', 'comment')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'amount', 'payment_method', 'status', 'payment_date', 'transaction_id')
    list_filter = ('status', 'payment_method', 'payment_date')
    search_fields = ('order__order_number', 'transaction_id', 'notes')
    readonly_fields = ('payment_date',)
    date_hierarchy = 'payment_date'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('order', 'amount', 'payment_method', 'status')
        }),
        ('Детали платежа', {
            'fields': ('transaction_id', 'payment_date', 'notes')
        }),
    )
    
    actions = ['mark_as_completed', 'mark_as_refunded']
    
    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed')
        
        # Обновляем статус заказов
        for payment in queryset:
            payment.order.paid_amount += payment.amount
            if payment.order.paid_amount >= payment.order.total_amount and payment.order.status == 'pending':
                payment.order.status = 'paid'
                payment.order.save()
                
                OrderHistory.objects.create(
                    order=payment.order,
                    status='paid',
                    previous_status='pending',
                    user=request.user,
                    comment="Автоматически отмечено как оплаченное после подтверждения платежа"
                )
    mark_as_completed.short_description = "Отметить как завершенные"
    
    def mark_as_refunded(self, request, queryset):
        queryset.update(status='refunded')
    mark_as_refunded.short_description = "Отметить как возвращенные"
