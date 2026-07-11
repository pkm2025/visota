import pytest
from django.test import Client

from apps.core.models import Company, UserSearchAffinity
from apps.identity.models import User
from apps.master_data.models import Customer


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="TEST",
        name="Test Company",
        tax_code="0101234567",
        accounting_regime="tt133",
    )


@pytest.fixture
def admin_client(db, company):
    user = User.objects.create_superuser(
        username="bob", password="Secret123", email="bob@test.local"
    )
    c = Client()
    c.force_login(user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


@pytest.mark.django_db
def test_search_returns_matching_customer(admin_client, company):
    Customer.objects.create(company=company, code="KH001", name="Cong ty ABC")
    resp = admin_client.get("/modern/search/", {"q": "ABC"})
    assert resp.status_code == 200
    content = resp.content.decode("utf-8")
    assert "KH001" in content
    assert "Khách hàng" in content


@pytest.mark.django_db
def test_search_caps_results_at_five_per_type(admin_client, company):
    for i in range(7):
        Customer.objects.create(company=company, code=f"KHX{i}", name=f"Match {i}")
    resp = admin_client.get("/modern/search/", {"q": "Match"})
    content = resp.content.decode("utf-8")
    assert content.count("ss-item-code") == 5
    assert "Xem tất cả" in content  # has_more link shown


@pytest.mark.django_db
def test_empty_query_returns_hint(admin_client):
    resp = admin_client.get("/modern/search/", {"q": ""})
    assert resp.status_code == 200
    assert "ss-hint" in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_click_records_affinity(admin_client, company):
    user = User.objects.get(username="bob")
    resp = admin_client.post("/modern/search/click/", {"type": "customer"})
    assert resp.status_code == 204
    affinity = UserSearchAffinity.objects.get(
        user=user, company=company, object_type="customer"
    )
    assert affinity.score == pytest.approx(1.0)

    admin_client.post("/modern/search/click/", {"type": "customer"})
    affinity.refresh_from_db()
    assert affinity.score > 1.0


@pytest.mark.django_db
def test_invalid_click_type_ignored(admin_client, company):
    resp = admin_client.post("/modern/search/click/", {"type": "not_a_type"})
    assert resp.status_code == 204
    assert not UserSearchAffinity.objects.filter(object_type="not_a_type").exists()
