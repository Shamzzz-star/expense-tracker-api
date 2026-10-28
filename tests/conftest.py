import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from expenses.models import Category

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="alice", password="S3cure-pass!")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="bob", password="S3cure-pass!")


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def auth_client(user):
    api = APIClient()
    api.force_authenticate(user=user)
    return api


@pytest.fixture
def food(user):
    return Category.objects.create(owner=user, name="Food", monthly_budget="300.00")


@pytest.fixture
def travel(user):
    return Category.objects.create(owner=user, name="Travel")
