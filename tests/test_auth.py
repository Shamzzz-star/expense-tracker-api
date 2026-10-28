import pytest


@pytest.mark.django_db
def test_register_creates_user(client):
    resp = client.post(
        "/api/auth/register/",
        {"username": "carol", "email": "carol@example.com", "password": "S3cure-pass!"},
    )
    assert resp.status_code == 201
    assert resp.data["username"] == "carol"
    assert "password" not in resp.data


@pytest.mark.django_db
def test_register_rejects_weak_password(client):
    resp = client.post("/api/auth/register/", {"username": "dave", "password": "123"})
    assert resp.status_code == 400
    assert "password" in resp.data


def test_login_returns_jwt_pair_and_token_works(client, user):
    resp = client.post("/api/auth/token/", {"username": "alice", "password": "S3cure-pass!"})
    assert resp.status_code == 200
    assert {"access", "refresh"} <= resp.data.keys()

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    me = client.get("/api/auth/me/")
    assert me.status_code == 200
    assert me.data["username"] == "alice"


def test_login_with_wrong_password_fails(client, user):
    resp = client.post("/api/auth/token/", {"username": "alice", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/api/expenses/", "/api/categories/", "/api/auth/me/"])
def test_endpoints_require_authentication(client, url):
    assert client.get(url).status_code == 401


@pytest.mark.django_db
def test_login_is_rate_limited(client, user, monkeypatch):
    from django.core.cache import cache
    from rest_framework.throttling import ScopedRateThrottle

    cache.clear()
    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"auth": "3/min"})
    codes = [
        client.post("/api/auth/token/", {"username": "alice", "password": "wrong"}).status_code
        for _ in range(4)
    ]
    assert codes == [401, 401, 401, 429]
