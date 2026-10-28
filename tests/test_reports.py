from datetime import date

import pytest

from expenses.models import Expense


@pytest.fixture
def october(user, food, travel, other_user):
    Expense.objects.create(owner=user, category=food, amount="200.00", date=date(2026, 10, 3))
    Expense.objects.create(owner=user, category=food, amount="150.00", date=date(2026, 10, 9))
    Expense.objects.create(owner=user, category=travel, amount="80.00", date=date(2026, 10, 12))
    Expense.objects.create(owner=user, category=None, amount="20.00", date=date(2026, 10, 30))
    # Noise: different month and different user must be excluded.
    Expense.objects.create(owner=user, category=food, amount="999.00", date=date(2026, 9, 30))
    Expense.objects.create(owner=other_user, amount="500.00", date=date(2026, 10, 5))


def test_monthly_summary(auth_client, october):
    resp = auth_client.get("/api/expenses/summary/", {"month": "2026-10"})
    assert resp.status_code == 200
    data = resp.data
    assert data["month"] == "2026-10"
    assert data["total"] == "450.00"
    assert data["count"] == 4

    by_cat = {row["category"]: row for row in data["by_category"]}
    assert by_cat["Food"]["total"] == "350.00"
    assert by_cat["Food"]["over_budget"] is True  # budget is 300
    assert by_cat["Travel"]["over_budget"] is False  # no budget set
    assert by_cat["Uncategorized"]["total"] == "20.00"
    # Sorted by highest spend first
    assert data["by_category"][0]["category"] == "Food"


def test_monthly_summary_empty_month(auth_client, user):
    resp = auth_client.get("/api/expenses/summary/", {"month": "2020-01"})
    assert resp.data["total"] == "0.00"
    assert resp.data["by_category"] == []


@pytest.mark.parametrize("bad", ["2026-13", "2026-1", "october"])
def test_monthly_summary_rejects_bad_month(auth_client, user, bad):
    resp = auth_client.get("/api/expenses/summary/", {"month": bad})
    assert resp.status_code == 400


def test_yearly_trend(auth_client, october):
    resp = auth_client.get("/api/expenses/trend/", {"year": 2026})
    assert resp.status_code == 200
    months = {m["month"]: m["total"] for m in resp.data["months"]}
    assert len(months) == 12
    assert months["2026-09"] == "999.00"
    assert months["2026-10"] == "450.00"
    assert months["2026-01"] == "0.00"
    assert resp.data["total"] == "1449.00"
