import pytest
from apps.identity.backends import RoleBasedBackend
from apps.identity.models import User, Role, Permission, UserCompanyRole
from apps.core.models import Company


def test_authenticate_with_username(db):
    User.objects.create_user(username='alice', password='Secret123')
    backend = RoleBasedBackend()
    user = backend.authenticate(None, username='alice', password='Secret123')
    assert user is not None
    assert user.username == 'alice'


def test_authenticate_with_email(db):
    User.objects.create_user(
        username='alice', email='alice@example.com', password='Secret123',
    )
    backend = RoleBasedBackend()
    user = backend.authenticate(
        None, username='alice@example.com', password='Secret123',
    )
    assert user is not None


def test_authenticate_wrong_password(db):
    User.objects.create_user(username='alice', password='Secret123')
    backend = RoleBasedBackend()
    user = backend.authenticate(None, username='alice', password='wrong')
    assert user is None


def test_authenticate_nonexistent_user(db):
    backend = RoleBasedBackend()
    user = backend.authenticate(None, username='ghost', password='whatever')
    assert user is None


def test_authenticate_with_none_username(db):
    backend = RoleBasedBackend()
    user = backend.authenticate(None, username=None, password='whatever')
    assert user is None


def test_authenticate_records_login_ip(db):
    from apps.identity.audit import record_login

    user = User.objects.create_user(username='alice', password='Secret123')

    class FakeReq:
        META = {'REMOTE_ADDR': '192.168.1.100'}

    record_login(user, FakeReq())
    user.refresh_from_db()
    assert user.last_login_ip == '192.168.1.100'
    assert user.failed_login_count == 0


def test_user_permissions_context_no_user(db):
    """user_permissions context processor returns has_perm=False for anonymous."""
    from apps.identity.context_processors import user_permissions

    class FakeReq:
        user = type('Anon', (), {'is_authenticated': False})()
        current_company = None

    ctx = user_permissions(FakeReq())
    assert ctx['has_perm']('anything') is False


def test_user_permissions_context_authenticated(db, company):
    """user_permissions context processor returns UserService for auth user."""
    from apps.identity.context_processors import user_permissions
    from apps.identity.services import UserService

    user = User.objects.create_user(username='alice', password='Secret123')
    role = Role.objects.create(company=company, code='acc', name='KT')
    perm = Permission.objects.create(code='gl.voucher.view', name='View')
    role.permissions.add(perm)
    UserCompanyRole.objects.create(user=user, company=company, role=role)

    class FakeReq:
        pass
    fake_req = FakeReq()
    fake_req.user = user
    fake_req.current_company = company

    ctx = user_permissions(fake_req)
    assert ctx['has_perm']('gl.voucher.view') is True
    assert ctx['has_perm']('gl.voucher.delete') is False
