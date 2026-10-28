from django.contrib import admin

from .models import Category, Expense


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "monthly_budget", "created_at"]
    list_filter = ["owner"]
    search_fields = ["name"]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["date", "amount", "category", "owner", "description"]
    list_filter = ["owner", "category", "date"]
    search_fields = ["description"]
    date_hierarchy = "date"
