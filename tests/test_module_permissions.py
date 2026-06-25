"""End-to-end tests for module-level permission enforcement."""

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import Permission, Role, User, UserCompanyRole


@pytest.fixture
def setup(db):
    from apps.identity.management.commands.seed_permissions import MODULE_PERMISSIONS

    # Seed minimal permission catalog (only the ones we test against)
    for module, name_vi, desc in MODULE_PERMISSIONS:
        Permission.objects.get_or_create(
            code=f"{module}.access",
            defaults={"module": module, "name": name_vi, "description": desc},
        )

    company = Company.objects.create(code="PCO", name="Perm Co")
    admin = User.objects.create_superuser(
        username="root", password="Root1234", email="root@t.co"
    )
    sales_user = User.objects.create_user(
        username="salesguy", password="Sales1234", email="sales@t.co"
    )
    # Build a sales-only role (sales + CRM)
    role = Role.objects.create(company=company, code="sales_only", name="Sales")
    role.permissions.add(Permission.objects.get(code="sales.access"))
    role.permissions.add(Permission.objects.get(code="crm.access"))
    UserCompanyRole.objects.create(
        user=sales_user, company=company, role=role, is_default=True
    )
    return company, admin, sales_user


@pytest.mark.django_db
def test_anonymous_redirected_to_login():
    c = Client()
    r = c.get("/modern/vouchers/")
    assert r.status_code == 302
    assert "/auth/login/" in r.url


@pytest.mark.django_db
def test_superuser_bypasses_permission_check(setup):
    _, admin, _ = setup
    c = Client()
    c.force_login(admin)
    # Admin can hit any module
    for url in [
        "/modern/vouchers/",
        "/modern/sales-invoices/",
        "/modern/employees/",
        "/modern/reports/trial-balance/",
    ]:
        r = c.get(url)
        assert r.status_code == 200, f"{url} returned {r.status_code}"


@pytest.mark.django_db
def test_sales_user_can_access_sales(setup):
    _, _, sales_user = setup
    c = Client()
    c.force_login(sales_user)
    r = c.get("/modern/sales-invoices/")
    assert r.status_code == 200


@pytest.mark.django_db
def test_sales_user_blocked_from_ledger(setup):
    _, _, sales_user = setup
    c = Client()
    c.force_login(sales_user)
    r = c.get("/modern/vouchers/")
    assert r.status_code == 302
    assert "/no-access/" in r.url


@pytest.mark.django_db
def test_sales_user_blocked_from_hr(setup):
    _, _, sales_user = setup
    c = Client()
    c.force_login(sales_user)
    r = c.get("/modern/employees/")
    assert r.status_code == 302
    assert "/no-access/" in r.url


@pytest.mark.django_db
def test_dashboard_always_accessible(setup):
    _, _, sales_user = setup
    c = Client()
    c.force_login(sales_user)
    r = c.get("/modern/")
    assert r.status_code == 200


@pytest.mark.django_db
def test_no_access_page_renders(setup):
    _, _, sales_user = setup
    c = Client()
    c.force_login(sales_user)
    r = c.get("/no-access/")
    assert r.status_code == 200
    assert "Không có quyền truy cập".encode() in r.content


@pytest.mark.django_db
def test_my_permissions_page_lists_granted(setup):
    _, _, sales_user = setup
    c = Client()
    c.force_login(sales_user)
    r = c.get("/modern/me/permissions/")
    assert r.status_code == 200
    body = r.content.decode()
    assert "Bán hàng" in body
    assert "Quyền của tôi" in body


@pytest.mark.django_db
def test_admin_role_list_requires_staff(setup):
    _, _, sales_user = setup
    c = Client()
    c.force_login(sales_user)
    r = c.get("/modern/admin/roles/")
    # StaffRequiredMixin blocks non-staff
    assert r.status_code in (302, 403)


@pytest.mark.django_db
def test_admin_sees_role_list(setup):
    _, admin, _ = setup
    c = Client()
    c.force_login(admin)
    r = c.get("/modern/admin/roles/")
    assert r.status_code == 200
    assert "Vai trò".encode() in r.content


@pytest.mark.django_db
def test_nav_filters_for_sales_user(setup):
    """Sales+CRM user sees CRM section but not HR section in nav."""
    _, _, sales_user = setup
    c = Client()
    c.force_login(sales_user)
    r = c.get("/modern/")
    body = r.content.decode()

    def wrapper_for(localStorage_key: str) -> str:
        idx = body.find(f"localStorage.getItem('{localStorage_key}')")
        assert idx > 0, f"nav section {localStorage_key} not found"
        wrapper_start = body.rfind('<div class="nav-section"', 0, idx)
        end = body.find(">", idx)
        return body[wrapper_start : end + 1]

    crm_open = wrapper_for("nav_CRM")
    hr_open = wrapper_for("nav_NS")
    assert "display:none" not in crm_open, f"CRM should be visible: {crm_open}"
    assert "display:none" in hr_open, f"HR should be hidden: {hr_open}"
