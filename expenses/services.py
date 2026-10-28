"""Reporting queries for expenses, kept out of the views so they are easy to test."""

from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import ExtractMonth

from .models import Category, Expense


def monthly_summary(user, year: int, month: int) -> dict:
    """Total spend for one month, broken down by category, with budget usage."""
    expenses = Expense.objects.filter(owner=user, date__year=year, date__month=month)
    total = expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    rows = (
        expenses.values("category_id", "category__name")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    budgets = dict(
        Category.objects.filter(owner=user).values_list("id", "monthly_budget")
    )

    by_category = []
    for row in rows:
        budget = budgets.get(row["category_id"])
        by_category.append(
            {
                "category_id": row["category_id"],
                "category": row["category__name"] or "Uncategorized",
                "total": row["total"],
                "count": row["count"],
                "budget": budget,
                "over_budget": budget is not None and row["total"] > budget,
            }
        )

    return {
        "month": f"{year:04d}-{month:02d}",
        "total": total,
        "count": expenses.count(),
        "by_category": by_category,
    }


def yearly_trend(user, year: int) -> dict:
    """Total spend for each of the 12 months in a year (zero for empty months)."""
    totals = dict(
        Expense.objects.filter(owner=user, date__year=year)
        .annotate(month=ExtractMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .values_list("month", "total")
    )
    months = [
        {"month": f"{year:04d}-{m:02d}", "total": totals.get(m, Decimal("0"))}
        for m in range(1, 13)
    ]
    return {"year": year, "total": sum(m["total"] for m in months), "months": months}


def current_month() -> tuple[int, int]:
    today = date.today()
    return today.year, today.month
