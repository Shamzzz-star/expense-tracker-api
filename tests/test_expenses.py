from datetime import date
from decimal import Decimal

import pytest

from expenses.models import Category, Expense


@pytest.fixture
def sample_expenses(user, food, travel):
    return [
        Expense.objects.create(owner=user, category=food, amount="12.50", date=date(2026, 10, 1), description="Lunch"),
        Expense.objects.create(owner=user, category=food, amount="40.00", date=date(2026, 10, 15), description="Groceries"),
        Expense.objects.create(owner=user, category=travel, amount="250.00", date=date(2026, 9, 20), description="Train tickets"),
    ]


def test_create_expense(auth_client, user, food):
    resp = auth_client.post(
        "/api/expenses/",
        {"amount": "19.99", "date": "2026-10-20", "category": food.pk, "description": "Pizza"},
    )
    assert resp.status_code == 201
    assert resp.data["category_name"] == "Food"
    expense = Expense.objects.get(pk=resp.data["id"])
    assert expense.owner == user
    assert expense.amount == Decimal("19.99")


@pytest.mark.parametrize("amount", ["0", "-10"])
def test_amount_must_be_positive(auth_client, amount):
    resp = auth_client.post("/api/expenses/", {"amount": amount, "date": "2026-10-20"})
    assert resp.status_code == 400
    assert "amount" in resp.data


def test_cannot_use_another_users_category(auth_client, other_user):
    foreign = Category.objects.create(owner=other_user, name="Bob's")
    resp = auth_client.post(
        "/api/expenses/", {"amount": "5", "date": "2026-10-20", "category": foreign.pk}
    )
    assert resp.status_code == 400
    assert "category" in resp.data


def test_cannot_read_or_edit_another_users_expense(auth_client, other_user):
    theirs = Expense.objects.create(owner=other_user, amount="99", date=date(2026, 10, 1))
    assert auth_client.get(f"/api/expenses/{theirs.pk}/").status_code == 404
    assert auth_client.patch(f"/api/expenses/{theirs.pk}/", {"amount": "1"}).status_code == 404
    assert auth_client.delete(f"/api/expenses/{theirs.pk}/").status_code == 404


def test_update_and_delete_expense(auth_client, sample_expenses):
    expense = sample_expenses[0]
    resp = auth_client.patch(f"/api/expenses/{expense.pk}/", {"amount": "15.00"})
    assert resp.status_code == 200
    assert resp.data["amount"] == "15.00"

    assert auth_client.delete(f"/api/expenses/{expense.pk}/").status_code == 204
    assert not Expense.objects.filter(pk=expense.pk).exists()


def test_deleting_category_keeps_expenses_uncategorized(auth_client, sample_expenses, food):
    auth_client.delete(f"/api/categories/{food.pk}/")
    sample_expenses[0].refresh_from_db()
    assert sample_expenses[0].category is None


def test_filter_by_date_range(auth_client, sample_expenses):
    resp = auth_client.get("/api/expenses/", {"date_from": "2026-10-01", "date_to": "2026-10-31"})
    assert resp.data["count"] == 2


def test_filter_by_category_and_amount(auth_client, sample_expenses, food):
    resp = auth_client.get("/api/expenses/", {"category": food.pk, "min_amount": "20"})
    assert [e["description"] for e in resp.data["results"]] == ["Groceries"]


def test_search_and_ordering(auth_client, sample_expenses):
    resp = auth_client.get("/api/expenses/", {"search": "train"})
    assert resp.data["count"] == 1

    resp = auth_client.get("/api/expenses/", {"ordering": "amount"})
    amounts = [e["amount"] for e in resp.data["results"]]
    assert amounts == ["12.50", "40.00", "250.00"]


def test_export_csv(auth_client, sample_expenses):
    resp = auth_client.get("/api/expenses/export/", {"date_from": "2026-10-01"})
    assert resp.status_code == 200
    assert resp["Content-Type"] == "text/csv"
    lines = resp.content.decode().strip().splitlines()
    assert lines[0] == "date,amount,category,description"
    assert len(lines) == 3  # header + 2 October expenses


def test_export_csv_neutralises_spreadsheet_formulas(auth_client, user):
    Expense.objects.create(owner=user, amount="5.00", date=date(2026, 10, 3), description="=HYPERLINK(\"x\")")
    resp = auth_client.get("/api/expenses/export/")
    row = resp.content.decode().strip().splitlines()[1]
    assert "'=HYPERLINK" in row
