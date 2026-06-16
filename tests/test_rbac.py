import pytest
from apps.identity.models import User, Role, Permission, UserCompanyRole
from apps.core.models import Company


def test_role_creation(db, company):
    role = Role.objects.create(
        company=company,
        code='accountant',
        name='Kế toán viên',
    )
    assert role.pk is not None
    assert str(role) == 'Kế toán viên'


def test_permission_unique_code(db):
    Permission.objects.create(code='gl.voucher.view', name='View vouchers')
    with pytest.raises(Exception):
        Permission.objects.create(code='gl.voucher.view', name='Duplicate')


def test_user_company_role(db, company):
    user = User.objects.create_user(username='alice', password='Secret123')
    role = Role.objects.create(company=company, code='accountant', name='KT')

    ucr = UserCompanyRole.objects.create(
        user=user, company=company, role=role, is_default=True,
    )
    assert ucr.pk is not None


def test_user_has_permission_through_role(db, company):
    from apps.identity.services import UserService

    user = User.objects.create_user(username='alice', password='Secret123')
    role = Role.objects.create(company=company, code='accountant', name='KT')
    perm = Permission.objects.create(code='gl.voucher.view', name='View')
    role.permissions.add(perm)
    UserCompanyRole.objects.create(user=user, company=company, role=role)

    service = UserService(user, company)
    assert service.has_permission('gl.voucher.view') is True
    assert service.has_permission('gl.voucher.delete') is False


def test_superuser_has_all_permissions(db, company):
    from apps.identity.services import UserService

    admin = User.objects.create_superuser(
        username='admin', password='Admin123', email='admin@x.com',
    )
    service = UserService(admin, company)
    assert service.has_permission('anything.at.all') is True


def test_user_with_no_company_has_no_perms(db):
    from apps.identity.services import UserService

    user = User.objects.create_user(username='alice', password='Secret123')
    service = UserService(user, None)
    assert service.has_permission('gl.voucher.view') is False
