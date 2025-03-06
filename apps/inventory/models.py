from django.db import models
from django.utils import timezone
from apps.users.models import User
from apps.orders.models import Product, Order

# Create your models here.

class Warehouse(models.Model):
    """
    Модель для хранения информации о складах.
    """
    name = models.CharField(max_length=100, verbose_name='Название склада')
    address = models.TextField(blank=True, null=True, verbose_name='Адрес')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    
    # Контактная информация
    contact_person = models.CharField(max_length=100, blank=True, null=True, verbose_name='Контактное лицо')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Телефон')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    
    # Метаданные
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Склад'
        verbose_name_plural = 'Склады'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    """
    Модель для хранения информации о товарных позициях на складе.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_items', verbose_name='Товар')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventory_items', verbose_name='Склад')
    
    # Количество и стоимость
    quantity = models.PositiveIntegerField(default=0, verbose_name='Количество')
    reserved_quantity = models.PositiveIntegerField(default=0, verbose_name='Зарезервировано')
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Стоимость единицы')
    
    # Расположение на складе
    location = models.CharField(max_length=100, blank=True, null=True, verbose_name='Расположение на складе')
    
    # Метаданные
    last_updated = models.DateTimeField(auto_now=True, verbose_name='Последнее обновление')
    
    class Meta:
        verbose_name = 'Товарная позиция'
        verbose_name_plural = 'Товарные позиции'
        ordering = ['warehouse', 'product']
        unique_together = ['product', 'warehouse']
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} шт. на складе {self.warehouse.name}"
    
    @property
    def available_quantity(self):
        """
        Возвращает доступное количество товара (общее количество минус зарезервированное).
        """
        return self.quantity - self.reserved_quantity
    
    @property
    def total_value(self):
        """
        Возвращает общую стоимость товарной позиции.
        """
        return self.quantity * self.unit_cost


class InventoryTransaction(models.Model):
    """
    Модель для хранения информации о движении товаров на складе.
    """
    TRANSACTION_TYPES = (
        ('receipt', 'Поступление'),
        ('issue', 'Отгрузка'),
        ('transfer', 'Перемещение'),
        ('adjustment', 'Корректировка'),
        ('return', 'Возврат'),
        ('reservation', 'Резервирование'),
        ('release', 'Освобождение резерва'),
    )
    
    # Основная информация
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, verbose_name='Тип операции')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_transactions', verbose_name='Товар')
    source_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='outgoing_transactions', verbose_name='Склад-источник')
    destination_warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='incoming_transactions', verbose_name='Склад-получатель')
    
    # Количество и стоимость
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Стоимость единицы')
    
    # Связи с другими моделями
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_transactions', verbose_name='Заказ')
    
    # Метаданные
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время операции')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='inventory_transactions', verbose_name='Создатель')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    
    class Meta:
        verbose_name = 'Складская операция'
        verbose_name_plural = 'Складские операции'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.product.name} ({self.quantity} шт.)"
    
    def save(self, *args, **kwargs):
        # Создаем транзакцию
        super().save(*args, **kwargs)
        
        # Обновляем остатки на складе
        self._update_inventory()
    
    def _update_inventory(self):
        """
        Обновляет остатки на складе в зависимости от типа операции.
        """
        # Получаем или создаем товарную позицию на складе-источнике
        source_item, _ = InventoryItem.objects.get_or_create(
            product=self.product,
            warehouse=self.source_warehouse,
            defaults={'unit_cost': self.unit_cost}
        )
        
        # Обрабатываем различные типы операций
        if self.transaction_type == 'receipt':
            # Поступление товара
            source_item.quantity += self.quantity
            source_item.unit_cost = self.unit_cost  # Обновляем стоимость
            source_item.save()
            
        elif self.transaction_type == 'issue':
            # Отгрузка товара
            if source_item.quantity >= self.quantity:
                source_item.quantity -= self.quantity
                source_item.save()
            
        elif self.transaction_type == 'transfer' and self.destination_warehouse:
            # Перемещение товара между складами
            if source_item.quantity >= self.quantity:
                # Уменьшаем количество на складе-источнике
                source_item.quantity -= self.quantity
                source_item.save()
                
                # Увеличиваем количество на складе-получателе
                dest_item, _ = InventoryItem.objects.get_or_create(
                    product=self.product,
                    warehouse=self.destination_warehouse,
                    defaults={'unit_cost': self.unit_cost}
                )
                dest_item.quantity += self.quantity
                dest_item.save()
            
        elif self.transaction_type == 'adjustment':
            # Корректировка остатков
            source_item.quantity = self.quantity
            source_item.save()
            
        elif self.transaction_type == 'return':
            # Возврат товара
            source_item.quantity += self.quantity
            source_item.save()
            
        elif self.transaction_type == 'reservation':
            # Резервирование товара
            if source_item.available_quantity >= self.quantity:
                source_item.reserved_quantity += self.quantity
                source_item.save()
            
        elif self.transaction_type == 'release':
            # Освобождение резерва
            if source_item.reserved_quantity >= self.quantity:
                source_item.reserved_quantity -= self.quantity
                source_item.save()


class Inventory(models.Model):
    """
    Модель для хранения информации об инвентаризациях.
    """
    STATUS_CHOICES = (
        ('draft', 'Черновик'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    )
    
    # Основная информация
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventories', verbose_name='Склад')
    inventory_number = models.CharField(max_length=50, unique=True, verbose_name='Номер инвентаризации')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='Статус')
    
    # Даты
    start_date = models.DateTimeField(blank=True, null=True, verbose_name='Дата начала')
    end_date = models.DateTimeField(blank=True, null=True, verbose_name='Дата завершения')
    
    # Метаданные
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_inventories', verbose_name='Создатель')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    
    class Meta:
        verbose_name = 'Инвентаризация'
        verbose_name_plural = 'Инвентаризации'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Инвентаризация #{self.inventory_number} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Обновляем даты в зависимости от статуса
        if self.status == 'in_progress' and not self.start_date:
            self.start_date = timezone.now()
        elif self.status == 'completed' and not self.end_date:
            self.end_date = timezone.now()
        
        super().save(*args, **kwargs)


class InventoryCount(models.Model):
    """
    Модель для хранения результатов подсчета товаров при инвентаризации.
    """
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='counts', verbose_name='Инвентаризация')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_counts', verbose_name='Товар')
    
    # Количество
    expected_quantity = models.PositiveIntegerField(verbose_name='Ожидаемое количество')
    actual_quantity = models.PositiveIntegerField(verbose_name='Фактическое количество')
    
    # Метаданные
    counted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='inventory_counts', verbose_name='Подсчитано')
    counted_at = models.DateTimeField(auto_now_add=True, verbose_name='Время подсчета')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    
    class Meta:
        verbose_name = 'Результат подсчета'
        verbose_name_plural = 'Результаты подсчета'
        ordering = ['inventory', 'product']
        unique_together = ['inventory', 'product']
    
    def __str__(self):
        return f"{self.product.name} в инвентаризации #{self.inventory.inventory_number}"
    
    @property
    def discrepancy(self):
        """
        Возвращает разницу между фактическим и ожидаемым количеством.
        """
        return self.actual_quantity - self.expected_quantity
    
    @property
    def has_discrepancy(self):
        """
        Возвращает True, если есть расхождение между фактическим и ожидаемым количеством.
        """
        return self.discrepancy != 0
