import pytest
from django.test import Client
from django.urls import reverse
from apps.identity.models import User


@pytest.mark.django_db
def test_login_page_loads():
    client = Client()
    response = client.get('/auth/login/')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'name="username"' in content
    assert 'name="password"' in content
    assert 'Đăng nhập' in content


@pytest.mark.django_db
def test_login_with_valid_credentials():
    User.objects.create_user(
        username='alice', password='Secret123', full_name='Alice',
    )
    client = Client()
    response = client.post('/auth/login/', {
        'username': 'alice',
        'password': 'Secret123',
    })
    assert response.status_code == 302
    assert '/modern/' in response.url


@pytest.mark.django_db
def test_login_with_wrong_password_shows_error():
    User.objects.create_user(username='alice', password='Secret123')
    client = Client()
    response = client.post('/auth/login/', {
        'username': 'alice',
        'password': 'wrongpass',
    })
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'không đúng' in content or 'incorrect' in content.lower()


@pytest.mark.django_db
def test_login_redirects_authenticated_user():
    """Already-logged-in user hitting /auth/login/ should redirect to /modern/."""
    user = User.objects.create_user(username='alice', password='Secret123')
    client = Client()
    client.force_login(user)
    response = client.get('/auth/login/')
    assert response.status_code == 302


@pytest.mark.django_db
def test_logout():
    user = User.objects.create_user(username='alice', password='Secret123')
    client = Client()
    client.force_login(user)
    response = client.post('/auth/logout/')
    assert response.status_code == 302


@pytest.mark.django_db
def test_login_records_ip():
    """Successful login should record IP on user."""
    User.objects.create_user(username='alice', password='Secret123')
    client = Client()
    client.post('/auth/login/', {
        'username': 'alice',
        'password': 'Secret123',
    }, REMOTE_ADDR='203.0.113.42')

    user = User.objects.get(username='alice')
    assert user.last_login_ip == '203.0.113.42'


@pytest.mark.django_db
def test_login_page_has_brand_name():
    """Login page should display brand name."""
    client = Client()
    response = client.get('/auth/login/')
    content = response.content.decode('utf-8')
    assert 'PMKetoan' in content
