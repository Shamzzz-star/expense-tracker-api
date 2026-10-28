from expenses.models import Category


def test_create_category(auth_client, user):
    resp = auth_client.post("/api/categories/", {"name": "Rent", "monthly_budget": "1200.00"})
    assert resp.status_code == 201
    assert Category.objects.get(pk=resp.data["id"]).owner == user


def test_duplicate_category_name_is_rejected_case_insensitive(auth_client, food):
    resp = auth_client.post("/api/categories/", {"name": "food"})
    assert resp.status_code == 400
    assert "name" in resp.data


def test_same_category_name_allowed_for_different_users(auth_client, other_user):
    Category.objects.create(owner=other_user, name="Food")
    resp = auth_client.post("/api/categories/", {"name": "Food"})
    assert resp.status_code == 201


def test_negative_budget_is_rejected(auth_client):
    resp = auth_client.post("/api/categories/", {"name": "Fun", "monthly_budget": "-5"})
    assert resp.status_code == 400


def test_users_only_see_their_own_categories(auth_client, food, other_user):
    hidden = Category.objects.create(owner=other_user, name="Secret")
    resp = auth_client.get("/api/categories/")
    names = [c["name"] for c in resp.data["results"]]
    assert names == ["Food"]
    assert auth_client.get(f"/api/categories/{hidden.pk}/").status_code == 404
