import pytest


@pytest.mark.django_db
def test_frontend_page_is_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Expense Tracker" in resp.content
    assert b"frontend/app.js" in resp.content
