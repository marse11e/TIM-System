from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from django.utils import timezone
from .models import Account, Category, Transaction, Debt, DebtPayment, Budget, BudgetCategory


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'account_type', 'currency', 'balance', 'is_active')
    list_filter = ('account_type', 'currency', 'is_active')
    search_fields = ('name', 'description', 'account_number')
    readonly_fields = ('balance', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'account_type', 'currency', 'balance', 'is_active')
        }),
        ('Дополнительная информация', {
            'fields': ('description', 'account_number')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['recalculate_balance']
    
    def recalculate_balance(self, request, queryset):
        for account in queryset:
            account.update_balance()
    recalculate_balance.short_description = "Пересчитать баланс"


class SubcategoryInline(admin.TabularInline):
    model = Category
    extra = 0
    fields = ('name', 'category_type', 'description', 'is_active')
    fk_name = 'parent'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'parent', 'is_active')
    list_filter = ('category_type', 'is_active')
    search_fields = ('name', 'description')
    inlines = [SubcategoryInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'category_type', 'description', 'is_active')
        }),
        ('Иерархия', {
            'fields': ('parent',)
        }),
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'amount', 'source_account', 'destination_account', 'category', 'date', 'created_by')
    list_filter = ('transaction_type', 'source_account', 'category', 'date')
    search_fields = ('description', 'amount')
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('transaction_type', 'amount', 'date')
        }),
        ('Счета', {
            'fields': ('source_account', 'destination_account')
        }),
        ('Категория и описание', {
            'fields': ('category', 'description')
        }),
        ('Связи', {
            'fields': ('order', 'supplier')
        }),
        ('Метаданные', {
            'fields': ('created_by',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если это новый объект
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class DebtPaymentInline(admin.TabularInline):
    model = DebtPayment
    extra = 0
    fields = ('amount', 'date', 'transaction', 'notes', 'created_by')
    readonly_fields = ('created_by',)


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ('debt_type', 'amount', 'paid_amount', 'remaining_amount', 'currency', 'status', 'date_created', 'due_date', 'is_overdue')
    list_filter = ('debt_type', 'status', 'currency', 'date_created')
    search_fields = ('description', 'notes')
    readonly_fields = ('paid_amount', 'remaining_amount', 'is_overdue', 'created_at', 'updated_at')
    date_hierarchy = 'date_created'
    inlines = [DebtPaymentInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('debt_type', 'amount', 'paid_amount', 'remaining_amount', 'currency', 'status')
        }),
        ('Даты', {
            'fields': ('date_created', 'due_date', 'is_overdue')
        }),
        ('Связи', {
            'fields': ('user', 'supplier', 'order')
        }),
        ('Дополнительная информация', {
            'fields': ('description', 'notes')
        }),
        ('Метаданные', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def remaining_amount(self, obj):
        return obj.remaining_amount
    remaining_amount.short_description = 'Остаток'
    
    def is_overdue(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color: red;">Да</span>')
        return 'Нет'
    is_overdue.short_description = 'Просрочена'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если это новый объект
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['mark_as_paid', 'mark_as_cancelled']
    
    def mark_as_paid(self, request, queryset):
        for debt in queryset:
            debt.paid_amount = debt.amount
            debt.status = 'paid'
            debt.save()
    mark_as_paid.short_description = "Отметить как оплаченные"
    
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
    mark_as_cancelled.short_description = "Отметить как отмененные"


@admin.register(DebtPayment)
class DebtPaymentAdmin(admin.ModelAdmin):
    list_display = ('debt', 'amount', 'date', 'transaction', 'created_by')
    list_filter = ('date', 'debt__debt_type')
    search_fields = ('notes', 'debt__description')
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('debt', 'amount', 'date')
        }),
        ('Связи', {
            'fields': ('transaction',)
        }),
        ('Дополнительная информация', {
            'fields': ('notes',)
        }),
        ('Метаданные', {
            'fields': ('created_by',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если это новый объект
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class BudgetCategoryInline(admin.TabularInline):
    model = BudgetCategory
    extra = 0
    fields = ('category', 'amount', 'actual_amount', 'progress')
    readonly_fields = ('actual_amount', 'progress')
    
    def actual_amount(self, obj):
        # Проверяем, что объект существует
        if not obj or not obj.pk:
            return '0.00'
        actual = obj.actual_amount
        if actual is None:
            return '0.00'
        return f"{actual:.2f}"
    actual_amount.short_description = 'Фактическая сумма'
    
    def progress(self, obj):
        # Проверяем, что объект существует
        if not obj or not obj.pk:
            return '0.00%'
            
        try:
            progress = obj.progress
            if progress is None:
                progress = 0
                
            if progress > 100:
                return format_html('<span style="color: red;">{:.2f}%</span>', progress)
            elif progress >= 90:
                return format_html('<span style="color: green;">{:.2f}%</span>', progress)
            else:
                return format_html('{:.2f}%', progress)
        except (TypeError, ValueError):
            return '0.00%'
    progress.short_description = 'Выполнение'


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('name', 'period', 'start_date', 'end_date', 'income_budget', 'actual_income', 'income_progress', 'expense_budget', 'actual_expense', 'expense_progress', 'is_active')
    list_filter = ('period', 'is_active', 'start_date')
    search_fields = ('name', 'description')
    readonly_fields = ('actual_income', 'income_progress', 'actual_expense', 'expense_progress', 'created_at', 'updated_at')
    date_hierarchy = 'start_date'
    inlines = [BudgetCategoryInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'period', 'start_date', 'end_date', 'is_active')
        }),
        ('Бюджет доходов', {
            'fields': ('income_budget', 'actual_income', 'income_progress')
        }),
        ('Бюджет расходов', {
            'fields': ('expense_budget', 'actual_expense', 'expense_progress')
        }),
        ('Дополнительная информация', {
            'fields': ('description',)
        }),
        ('Метаданные', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def actual_income(self, obj):
        # Проверяем, что объект существует
        if not obj or not obj.pk:
            return '0.00'
            
        try:
            actual = obj.actual_income
            if actual is None:
                actual = 0
            return f"{actual:.2f}"
        except (TypeError, AttributeError):
            return '0.00'
    actual_income.short_description = 'Фактический доход'
    
    def income_progress(self, obj):
        # Проверяем, что объект существует
        if not obj or not obj.pk:
            return '0.00%'
            
        try:
            progress = obj.income_progress
            if progress is None:
                progress = 0
                
            if progress > 100:
                return format_html('<span style="color: green;">{:.2f}%</span>', progress)
            elif progress >= 90:
                return format_html('<span style="color: green;">{:.2f}%</span>', progress)
            else:
                return format_html('{:.2f}%', progress)
        except (TypeError, ValueError, AttributeError):
            return '0.00%'
    income_progress.short_description = 'Выполнение дохода'
    
    def actual_expense(self, obj):
        # Проверяем, что объект существует
        if not obj or not obj.pk:
            return '0.00'
            
        try:
            actual = obj.actual_expense
            if actual is None:
                actual = 0
            return f"{actual:.2f}"
        except (TypeError, AttributeError):
            return '0.00'
    actual_expense.short_description = 'Фактический расход'
    
    def expense_progress(self, obj):
        # Проверяем, что объект существует
        if not obj or not obj.pk:
            return '0.00%'
            
        try:
            progress = obj.expense_progress
            if progress is None:
                progress = 0
                
            if progress > 100:
                return format_html('<span style="color: red;">{:.2f}%</span>', progress)
            elif progress >= 90:
                return format_html('<span style="color: orange;">{:.2f}%</span>', progress)
            else:
                return format_html('{:.2f}%', progress)
        except (TypeError, ValueError, AttributeError):
            return '0.00%'
    expense_progress.short_description = 'Выполнение расхода'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если это новый объект
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(BudgetCategory)
class BudgetCategoryAdmin(admin.ModelAdmin):
    list_display = ('budget', 'category', 'amount', 'actual_amount', 'progress')
    list_filter = ('budget', 'category')
    search_fields = ('budget__name', 'category__name')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('budget', 'category', 'amount')
        }),
        ('Фактические данные', {
            'fields': ('actual_amount', 'progress')
        }),
    )
    
    readonly_fields = ('actual_amount', 'progress')
    
    def actual_amount(self, obj):
        # Проверяем, что объект существует
        if not obj or not obj.pk:
            return '0.00'
        actual = obj.actual_amount
        if actual is None:
            return '0.00'
        return f"{actual:.2f}"
    actual_amount.short_description = 'Фактическая сумма'
    
    def progress(self, obj):
        # Проверяем, что объект существует
        if not obj or not obj.pk:
            return '0.00%'
            
        try:
            progress = obj.progress
            if progress is None:
                progress = 0
                
            if progress > 100:
                return format_html('<span style="color: red;">{:.2f}%</span>', progress)
            elif progress >= 90:
                return format_html('<span style="color: green;">{:.2f}%</span>', progress)
            else:
                return format_html('{:.2f}%', progress)
        except (TypeError, ValueError):
            return '0.00%'
    progress.short_description = 'Выполнение'
