"""Tests for Knowledge Base (help center) views."""

import pytest
from django.test import Client

from apps.identity.models import User
from apps.public.models import BlogArticle


@pytest.fixture
def auth_client(db):
    User.objects.create_superuser(username="helptest", password="Secret123", email="h@test.local")
    c = Client()
    c.force_login(User.objects.get(username="helptest"))
    return c


@pytest.fixture
def help_articles(db):
    from apps.public.management.commands.seed_help_articles import HELP_ARTICLES

    for a in HELP_ARTICLES:
        BlogArticle.objects.update_or_create(
            slug=a["slug"],
            defaults={
                "title": a["title"],
                "excerpt": a["excerpt"],
                "content": a["content"],
                "tags": a["tags"],
                "status": BlogArticle.Status.PUBLISHED,
            },
        )
    return BlogArticle.objects.filter(tags__icontains="help")


@pytest.mark.django_db
def test_help_index_requires_login(db):
    c = Client()
    response = c.get("/modern/help/")
    assert response.status_code == 302
    assert "/auth/login/" in response.url


@pytest.mark.django_db
def test_help_index_loads(auth_client, help_articles):
    response = auth_client.get("/modern/help/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Trợ giúp" in content
    assert "hạch toán" in content.lower() or "HĐĐT" in content


@pytest.mark.django_db
def test_help_index_search(auth_client, help_articles):
    response = auth_client.get("/modern/help/?search=thuế")
    assert response.status_code == 200
    assert response.context["search"] == "thuế"


@pytest.mark.django_db
def test_help_detail_loads(auth_client, help_articles):
    article = help_articles.first()
    response = auth_client.get(f"/modern/help/{article.slug}/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert article.title in content


@pytest.mark.django_db
def test_help_detail_increments_views(auth_client, help_articles):
    article = help_articles.first()
    initial_views = article.view_count
    auth_client.get(f"/modern/help/{article.slug}/")
    article.refresh_from_db()
    assert article.view_count == initial_views + 1


@pytest.mark.django_db
def test_help_detail_404_for_nonexistent(auth_client):
    response = auth_client.get("/modern/help/nonexistent-slug-xyz/")
    assert response.status_code == 404
