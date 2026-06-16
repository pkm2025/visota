import pytest
from apps.identity.models import User


def test_user_creation(db):
    u = User.objects.create_user(
        username='alice',
        email='alice@example.com',
        password='SecretPass123',
        full_name='Alice Nguyen',
    )
    assert u.pk is not None
    assert u.check_password('SecretPass123')
    assert u.is_active is True
    assert u.is_superuser is False


def test_create_superuser(db):
    u = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='AdminPass123',
    )
    assert u.is_staff is True
    assert u.is_superuser is True


def test_user_str_shows_full_name(db):
    u = User(username='alice', full_name='Alice Nguyen')
    assert str(u) == 'Alice Nguyen (alice)'


def test_user_without_full_name_shows_username(db):
    u = User(username='alice')
    assert str(u) == 'alice'


def test_user_defaults(db):
    u = User.objects.create_user(username='bob', password='Secret123')
    assert u.full_name == ''
    assert u.phone == ''
    assert u.two_factor_enabled is False
    assert u.failed_login_count == 0
    assert u.last_login_ip is None
