from django.db import models
from django.utils import timezone
from apps.users.models import User
from apps.tracking.models import TrackingNumber

# Create your models here.

class Supplier(models.Model):
    """
    Модель для хранения информации о поставщиках.
    """
    name = models.CharField(max_length=100, verbose_name='Название поставщика')
    contact_person = models.CharField(max_length=100, blank=True, null=True, verbose_name='Контактное лицо')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Телефон')
    address = models.TextField(blank=True, null=True, verbose_name='Адрес')
    website = models.URLField(blank=True, null=True, verbose_name='Веб-сайт')
    
    # Дополнительная информация
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Модель для хранения информации о товарах.
    """
    name = models.CharField(max_length=255, verbose_name='Название товара')
    sku = models.CharField(max_length=50, blank=True, null=True, unique=True, verbose_name='Артикул')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    
    # Цены
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='Закупочная цена')
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='Продажная цена')
    
    # Связи
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name='Поставщик')
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    
    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.sku})" if self.sku else self.name


class Order(models.Model):
    """
    Модель для хранения информации о заказах.
    """
    STATUS_CHOICES = (
        ('draft', 'Черновик'),
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачен'),
        ('processing', 'В обработке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
        ('refunded', 'Возвращен'),
    )
    
    # Основная информация
    order_number = models.CharField(max_length=50, unique=True, verbose_name='Номер заказа')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name='Пользователь')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='Статус')
    
    # Даты
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    paid_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата оплаты')
    shipped_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата отправки')
    delivered_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата доставки')
    
    # Финансовая информация
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Общая сумма')
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Оплаченная сумма')
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Стоимость доставки')
    
    # Связи с другими моделями
    tracking_numbers = models.ManyToManyField(TrackingNumber, blank=True, related_name='orders', verbose_name='Трек-номера')
    
    # Дополнительная информация
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    
    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Заказ #{self.order_number} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Автоматическое обновление дат в зависимости от статуса
        if self.status == 'paid' and not self.paid_at:
            self.paid_at = timezone.now()
        elif self.status == 'shipped' and not self.shipped_at:
            self.shipped_at = timezone.now()
        elif self.status == 'delivered' and not self.delivered_at:
            self.delivered_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def calculate_total(self):
        """
        Пересчитывает общую сумму заказа на основе товаров в заказе.
        """
        total = sum(item.subtotal for item in self.items.all())
        self.total_amount = total + self.shipping_cost
        self.save()
        return self.total_amount


class OrderItem(models.Model):
    """
    Модель для хранения информации о товарах в заказе.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Заказ')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items', verbose_name='Товар')
    
    # Информация о товаре на момент заказа (для сохранения истории)
    product_name = models.CharField(max_length=255, verbose_name='Название товара')
    product_sku = models.CharField(max_length=50, blank=True, null=True, verbose_name='Артикул')
    
    # Количество и цены
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена за единицу')
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Товар в заказе'
        verbose_name_plural = 'Товары в заказе'
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity} в заказе #{self.order.order_number}"
    
    @property
    def subtotal(self):
        """
        Рассчитывает стоимость позиции (количество * цена за единицу).
        """
        return self.quantity * self.unit_price
    
    def save(self, *args, **kwargs):
        # Если товар указан, но название не заполнено, заполняем его
        if self.product and not self.product_name:
            self.product_name = self.product.name
            self.product_sku = self.product.sku
            self.unit_price = self.product.selling_price or 0
        
        super().save(*args, **kwargs)
        
        # Пересчитываем общую сумму заказа
        self.order.calculate_total()


class OrderHistory(models.Model):
    """
    Модель для хранения истории изменений заказа.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='history', verbose_name='Заказ')
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, verbose_name='Статус')
    previous_status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, blank=True, null=True, verbose_name='Предыдущий статус')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время изменения')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_history', verbose_name='Пользователь')
    comment = models.TextField(blank=True, null=True, verbose_name='Комментарий')
    
    class Meta:
        verbose_name = 'История заказа'
        verbose_name_plural = 'История заказов'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Заказ #{self.order.order_number} изменен на {self.get_status_display()} ({self.timestamp.strftime('%d.%m.%Y %H:%M')})"


class Payment(models.Model):
    """
    Модель для хранения информации о платежах.
    """
    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Наличные'),
        ('card', 'Банковская карта'),
        ('bank_transfer', 'Банковский перевод'),
        ('electronic', 'Электронный платеж'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Ожидает обработки'),
        ('completed', 'Завершен'),
        ('failed', 'Ошибка'),
        ('refunded', 'Возвращен'),
    )
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments', verbose_name='Заказ')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, verbose_name='Способ оплаты')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    
    # Информация о платеже
    transaction_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='ID транзакции')
    payment_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата платежа')
    
    # Дополнительная информация
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    
    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Платеж {self.amount} руб. для заказа #{self.order.order_number} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Если платеж успешный, обновляем оплаченную сумму заказа
        if self.status == 'completed':
            self.order.paid_amount += self.amount
            
            # Если заказ полностью оплачен, меняем его статус
            if self.order.paid_amount >= self.order.total_amount and self.order.status == 'pending':
                self.order.status = 'paid'
            
            self.order.save()
