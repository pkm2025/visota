import pytest
from django.test import Client
from apps.identity.models import User


@pytest.fixture
def auth_client(db):
    user = User.objects.create_superuser(username='alice', password='Secret123', email='alice@test.local')
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_layout_has_sidebar_toggle(auth_client):
    """Left sidebar has collapse toggle button."""
    response = auth_client.get('/modern/')
    content = response.content.decode('utf-8')
    assert 'sidebar-toggle' in content or 'toggleSidebar' in content


@pytest.mark.django_db
def test_layout_has_right_sidebar(auth_client):
    """Right sidebar exists in layout."""
    response = auth_client.get('/modern/')
    content = response.content.decode('utf-8')
    assert 'right-sidebar' in content or 'context-panel' in content


@pytest.mark.django_db
def test_layout_has_tab_bar(auth_client):
    """Tab bar component exists."""
    response = auth_client.get('/modern/')
    content = response.content.decode('utf-8')
    assert 'tab-bar' in content or 'tabs-container' in content


@pytest.mark.django_db
def test_right_sidebar_shows_legal_refs(auth_client):
    """Right sidebar contains legal reference links."""
    response = auth_client.get('/modern/')
    content = response.content.decode('utf-8')
    # Should have TT133 or TT200 reference
    assert 'TT133' in content or 'Thông tư' in content
