from django.db import models
from django.utils import timezone
from django.db.models import Sum
from apps.users.models import User
from apps.orders.models import Order, Supplier

# Create your models here.

class Account(models.Model):
    """
    Модель для хранения информации о финансовых счетах.
    """
    ACCOUNT_TYPES = (
        ('cash', 'Наличные'),
        ('bank', 'Банковский счет'),
        ('card', 'Банковская карта'),
        ('electronic', 'Электронный кошелек'),
        ('other', 'Другое'),
    )
    
    name = models.CharField(max_length=100, verbose_name='Название счета')
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, verbose_name='Тип счета')
    currency = models.CharField(max_length=3, default='RUB', verbose_name='Валюта')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Баланс')
    
    # Дополнительная информация
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    account_number = models.CharField(max_length=50, blank=True, null=True, verbose_name='Номер счета')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Счет'
        verbose_name_plural = 'Счета'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()}) - {self.balance} {self.currency}"
    
    def update_balance(self):
        """
        Обновляет баланс счета на основе всех транзакций.
        """
        try:
            income = self.incoming_transactions.aggregate(total=Sum('amount'))['total'] or 0
            expense = self.outgoing_transactions.aggregate(total=Sum('amount'))['total'] or 0
            self.balance = income - expense
            self.save()
        except Exception:
            # В случае ошибки оставляем баланс без изменений
            pass


class Category(models.Model):
    """
    Модель для хранения категорий доходов и расходов.
    """
    CATEGORY_TYPES = (
        ('income', 'Доход'),
        ('expense', 'Расход'),
    )
    
    name = models.CharField(max_length=100, verbose_name='Название категории')
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPES, verbose_name='Тип категории')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories', verbose_name='Родительская категория')
    
    # Метаданные
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['category_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"


class Transaction(models.Model):
    """
    Модель для хранения финансовых транзакций.
    """
    TRANSACTION_TYPES = (
        ('income', 'Доход'),
        ('expense', 'Расход'),
        ('transfer', 'Перевод между счетами'),
        ('adjustment', 'Корректировка'),
    )
    
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name='Тип транзакции')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Сумма')
    date = models.DateTimeField(default=timezone.now, verbose_name='Дата транзакции')
    
    # Связи со счетами
    source_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='outgoing_transactions', verbose_name='Счет-источник')
    destination_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='incoming_transactions', verbose_name='Счет-получатель')
    
    # Категория и описание
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name='Категория')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    
    # Связи с другими моделями
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name='Заказ')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name='Поставщик')
    
    # Метаданные
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='transactions', verbose_name='Создатель')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'
        ordering = ['-date']
    
    def __str__(self):
        try:
            if self.transaction_type == 'transfer' and self.destination_account:
                return f"Перевод {self.amount} {self.source_account.currency} из {self.source_account.name} в {self.destination_account.name}"
            else:
                category_name = self.category.name if self.category else 'Без категории'
                return f"{self.get_transaction_type_display()} {self.amount} {self.source_account.currency} - {category_name}"
        except Exception:
            return f"Транзакция #{self.pk if self.pk else 'новая'}"
    
    def save(self, *args, **kwargs):
        try:
            # Проверяем тип транзакции и устанавливаем соответствующие значения
            if self.transaction_type == 'income':
                # Для дохода источник и получатель - один и тот же счет
                self.destination_account = self.source_account
            elif self.transaction_type == 'expense':
                # Для расхода получатель не указывается
                self.destination_account = None
            
            super().save(*args, **kwargs)
            
            # Обновляем балансы счетов
            if self.source_account:
                self.source_account.update_balance()
            if self.destination_account and self.destination_account != self.source_account:
                self.destination_account.update_balance()
        except Exception:
            # В случае ошибки просто сохраняем транзакцию без обновления балансов
            super().save(*args, **kwargs)


class Debt(models.Model):
    """
    Модель для хранения информации о задолженностях.
    """
    DEBT_TYPES = (
        ('receivable', 'Дебиторская задолженность'),
        ('payable', 'Кредиторская задолженность'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Активна'),
        ('partially_paid', 'Частично оплачена'),
        ('paid', 'Оплачена'),
        ('cancelled', 'Отменена'),
    )
    
    debt_type = models.CharField(max_length=10, choices=DEBT_TYPES, verbose_name='Тип задолженности')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Сумма')
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Оплаченная сумма')
    currency = models.CharField(max_length=3, default='RUB', verbose_name='Валюта')
    
    # Даты
    date_created = models.DateField(default=timezone.now, verbose_name='Дата возникновения')
    due_date = models.DateField(blank=True, null=True, verbose_name='Срок оплаты')
    
    # Статус
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active', verbose_name='Статус')
    
    # Связи с другими моделями
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='debts', verbose_name='Пользователь')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='debts', verbose_name='Поставщик')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='debts', verbose_name='Заказ')
    
    # Дополнительная информация
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    
    # Метаданные
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_debts', verbose_name='Создатель')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Задолженность'
        verbose_name_plural = 'Задолженности'
        ordering = ['status', 'due_date']
    
    def __str__(self):
        try:
            if self.debt_type == 'receivable':
                debtor = self.user.username if self.user else (self.supplier.name if self.supplier else "Неизвестно")
                return f"Дебиторская задолженность от {debtor} на сумму {self.amount} {self.currency}"
            else:
                creditor = self.user.username if self.user else (self.supplier.name if self.supplier else "Неизвестно")
                return f"Кредиторская задолженность перед {creditor} на сумму {self.amount} {self.currency}"
        except Exception:
            return f"Задолженность #{self.pk if self.pk else 'новая'}"
    
    @property
    def remaining_amount(self):
        """
        Возвращает оставшуюся сумму задолженности.
        """
        try:
            if self.amount is None:
                return 0
            if self.paid_amount is None:
                return self.amount
            return self.amount - self.paid_amount
        except Exception:
            return 0
    
    @property
    def is_overdue(self):
        """
        Возвращает True, если задолженность просрочена.
        """
        try:
            return (self.due_date and 
                    self.due_date < timezone.now().date() and 
                    self.status in ['active', 'partially_paid'])
        except Exception:
            return False
    
    def update_status(self):
        """
        Обновляет статус задолженности на основе оплаченной суммы.
        """
        try:
            if self.paid_amount is None:
                self.paid_amount = 0
                
            if self.amount is None:
                self.amount = 0
                
            if self.paid_amount >= self.amount:
                self.status = 'paid'
            elif self.paid_amount > 0:
                self.status = 'partially_paid'
            else:
                self.status = 'active'
            self.save(update_fields=['status', 'paid_amount'])
        except Exception:
            # В случае ошибки оставляем статус без изменений
            pass


class DebtPayment(models.Model):
    """
    Модель для хранения информации о платежах по задолженностям.
    """
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name='payments', verbose_name='Задолженность')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Сумма платежа')
    date = models.DateField(default=timezone.now, verbose_name='Дата платежа')
    
    # Связь с транзакцией
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='debt_payments', verbose_name='Транзакция')
    
    # Дополнительная информация
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    
    # Метаданные
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='debt_payments', verbose_name='Создатель')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Платеж по задолженности'
        verbose_name_plural = 'Платежи по задолженностям'
        ordering = ['-date']
    
    def __str__(self):
        try:
            return f"Платеж {self.amount} {self.debt.currency} по задолженности от {self.date}"
        except Exception:
            return f"Платеж #{self.pk if self.pk else 'новый'}"
    
    def save(self, *args, **kwargs):
        try:
            super().save(*args, **kwargs)
            
            # Обновляем оплаченную сумму и статус задолженности
            if self.debt:
                total = self.debt.payments.aggregate(total=Sum('amount'))['total']
                self.debt.paid_amount = total if total is not None else 0
                self.debt.update_status()
        except Exception:
            # В случае ошибки просто сохраняем платеж без обновления задолженности
            super().save(*args, **kwargs)


class Budget(models.Model):
    """
    Модель для хранения информации о бюджетах.
    """
    PERIOD_CHOICES = (
        ('daily', 'Ежедневно'),
        ('weekly', 'Еженедельно'),
        ('monthly', 'Ежемесячно'),
        ('quarterly', 'Ежеквартально'),
        ('yearly', 'Ежегодно'),
        ('custom', 'Произвольный период'),
    )
    
    name = models.CharField(max_length=100, verbose_name='Название бюджета')
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, verbose_name='Период')
    
    # Даты
    start_date = models.DateField(verbose_name='Дата начала')
    end_date = models.DateField(verbose_name='Дата окончания')
    
    # Суммы
    income_budget = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Бюджет доходов')
    expense_budget = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Бюджет расходов')
    
    # Дополнительная информация
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    
    # Метаданные
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='budgets', verbose_name='Создатель')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Бюджет'
        verbose_name_plural = 'Бюджеты'
        ordering = ['-start_date']
    
    def __str__(self):
        try:
            start_date_str = self.start_date.strftime('%d.%m.%Y') if self.start_date else "Не указана"
            end_date_str = self.end_date.strftime('%d.%m.%Y') if self.end_date else "Не указана"
            return f"{self.name} ({start_date_str} - {end_date_str})"
        except Exception:
            return f"Бюджет #{self.pk if self.pk else 'новый'}"
    
    @property
    def actual_income(self):
        """
        Возвращает фактический доход за период бюджета.
        """
        try:
            # Проверяем, что даты установлены
            if not self.start_date or not self.end_date:
                return 0
                
            result = Transaction.objects.filter(
                transaction_type='income',
                date__gte=self.start_date,
                date__lte=self.end_date
            ).aggregate(total=Sum('amount'))['total']
            
            return result if result is not None else 0
        except Exception:
            return 0
    
    @property
    def actual_expense(self):
        """
        Возвращает фактический расход за период бюджета.
        """
        try:
            # Проверяем, что даты установлены
            if not self.start_date or not self.end_date:
                return 0
                
            result = Transaction.objects.filter(
                transaction_type='expense',
                date__gte=self.start_date,
                date__lte=self.end_date
            ).aggregate(total=Sum('amount'))['total']
            
            return result if result is not None else 0
        except Exception:
            return 0
    
    @property
    def income_progress(self):
        """
        Возвращает процент выполнения бюджета доходов.
        """
        try:
            # Проверяем, что бюджет доходов больше нуля
            if not self.income_budget or self.income_budget <= 0:
                return 0
                
            # Получаем фактический доход
            actual = self.actual_income
            if actual is None:
                actual = 0
                
            return (actual / self.income_budget) * 100
        except (TypeError, ZeroDivisionError, AttributeError):
            return 0
    
    @property
    def expense_progress(self):
        """
        Возвращает процент выполнения бюджета расходов.
        """
        try:
            # Проверяем, что бюджет расходов больше нуля
            if not self.expense_budget or self.expense_budget <= 0:
                return 0
                
            # Получаем фактический расход
            actual = self.actual_expense
            if actual is None:
                actual = 0
                
            return (actual / self.expense_budget) * 100
        except (TypeError, ZeroDivisionError, AttributeError):
            return 0


class BudgetCategory(models.Model):
    """
    Модель для хранения информации о бюджетах по категориям.
    """
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='category_budgets', verbose_name='Бюджет')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets', verbose_name='Категория')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Сумма')
    
    class Meta:
        verbose_name = 'Бюджет по категории'
        verbose_name_plural = 'Бюджеты по категориям'
        ordering = ['budget', 'category']
        unique_together = ['budget', 'category']
    
    def __str__(self):
        try:
            return f"{self.category.name} в бюджете {self.budget.name}"
        except Exception:
            return f"Бюджет по категории #{self.pk if self.pk else 'новый'}"
    
    @property
    def actual_amount(self):
        """
        Возвращает фактическую сумму по категории за период бюджета.
        """
        try:
            # Проверяем, что бюджет и категория существуют
            if not self.budget or not self.category:
                return 0
                
            # Проверяем, что даты бюджета установлены
            if not self.budget.start_date or not self.budget.end_date:
                return 0
                
            result = Transaction.objects.filter(
                category=self.category,
                date__gte=self.budget.start_date,
                date__lte=self.budget.end_date
            ).aggregate(total=Sum('amount'))['total']
            
            return result if result is not None else 0
        except Exception:
            return 0
    
    @property
    def progress(self):
        """
        Возвращает процент выполнения бюджета по категории.
        """
        try:
            # Проверяем, что сумма больше нуля, чтобы избежать деления на ноль
            if not self.amount or self.amount <= 0:
                return 0
                
            # Получаем фактическую сумму
            actual = self.actual_amount
            if actual is None:
                actual = 0
                
            return (actual / self.amount) * 100
        except (TypeError, ZeroDivisionError, AttributeError):
            return 0
