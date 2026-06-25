"""Tests for approvals module: submit, approve chain, reject."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.approvals.models import ApprovalRequest, ApprovalRule
from apps.approvals.services import ApprovalService, NoApprovalRuleError
from apps.contracts.models import Contract
from apps.core.models import Company
from apps.identity.models import Role, UserCompanyRole
from apps.notifications.models import Notification

User = get_user_model()


@pytest.fixture
def company(db):
    return Company.objects.create(code="TESTAPP", name="Test Approval Co")


@pytest.fixture
def admin(db, company):
    return User.objects.create_superuser(
        username="admin", password="Secret123!", email="admin@test.local"
    )


@pytest.fixture
def requester(db, company):
    return User.objects.create_user(username="alice", password="Secret123!")


@pytest.fixture
def approver(db, company):
    u = User.objects.create_user(username="approver_acc", password="Secret123!")
    role = Role.objects.create(company=company, code="accountant", name="KT")
    UserCompanyRole.objects.create(user=u, company=company, role=role, is_default=True)
    return u


@pytest.fixture
def chief(db, company):
    u = User.objects.create_user(username="chief_acc", password="Secret123!")
    role = Role.objects.create(company=company, code="chief_accountant", name="KTT")
    UserCompanyRole.objects.create(user=u, company=company, role=role, is_default=True)
    return u


@pytest.fixture
def rule_50_500(company):
    return ApprovalRule.objects.create(
        company=company, voucher_type="sales_receipt",
        min_amount=Decimal("50000000"), max_amount=Decimal("500000000"),
        approver_roles=["accountant", "chief_accountant"],
    )


@pytest.fixture
def target_obj(company):
    """Contract instance — real model with _meta for ContentType lookup."""
    return Contract.objects.create(
        company=company, contract_no="C-APP-001",
        contract_date=date(2026, 6, 23),
        party_name="Investor", value=Decimal("100000000"),
        status=Contract.Status.ACTIVE,
    )


# ---------- Model ----------

@pytest.mark.django_db
def test_approval_rule_str(company):
    rule = ApprovalRule.objects.create(
        company=company, voucher_type="sales_receipt",
        min_amount=Decimal("100"), max_amount=Decimal("1000"),
        approver_roles=["admin"],
    )
    assert "sales_receipt" in str(rule)
    assert "admin" in str(rule)


@pytest.mark.django_db
def test_approval_request_status_default(company, admin):
    from django.contrib.contenttypes.models import ContentType
    ct = ContentType.objects.get_for_model(User)
    req = ApprovalRequest.objects.create(
        company=company, content_type=ct, object_id=admin.id,
        object_label="Test", amount=Decimal("100"),
        requested_by=admin,
    )
    assert req.status == ApprovalRequest.Status.PENDING


# ---------- Service ----------

@pytest.mark.django_db
def test_get_rule_matches_amount_range(company, rule_50_500):
    rule = ApprovalService.get_rule(company, "sales_receipt", Decimal("100000000"))
    assert rule is not None
    assert rule.min_amount == Decimal("50000000")


@pytest.mark.django_db
def test_get_rule_returns_none_outside_range(company, rule_50_500):
    rule = ApprovalService.get_rule(company, "sales_receipt", Decimal("10"))
    assert rule is None


@pytest.mark.django_db
def test_is_approval_required(company, rule_50_500):
    assert ApprovalService.is_approval_required(company, "sales_receipt", Decimal("100000000")) is True
    assert ApprovalService.is_approval_required(company, "sales_receipt", Decimal("10")) is False


@pytest.mark.django_db
def test_submit_creates_steps_per_role(company, requester, rule_50_500, target_obj):
    req = ApprovalService.submit(
        obj=target_obj, voucher_type="sales_receipt",
        amount=Decimal("100000000"), requested_by=requester,
    )
    assert req.status == ApprovalRequest.Status.PENDING
    assert req.steps.count() == 2
    assert req.steps.first().role_required == "accountant"
    assert req.steps.last().role_required == "chief_accountant"


@pytest.mark.django_db
def test_submit_without_rule_raises(company, requester, target_obj):
    with pytest.raises(NoApprovalRuleError):
        ApprovalService.submit(
            obj=target_obj, voucher_type="sales_receipt",
            amount=Decimal("1"), requested_by=requester,
        )


@pytest.mark.django_db
def test_submit_cancels_prior_pending(company, requester, rule_50_500, target_obj):
    ApprovalService.submit(
        obj=target_obj, voucher_type="sales_receipt",
        amount=Decimal("100000000"), requested_by=requester,
    )
    ApprovalService.submit(
        obj=target_obj, voucher_type="sales_receipt",
        amount=Decimal("100000000"), requested_by=requester,
    )
    cancelled = ApprovalRequest.objects.filter(
        status=ApprovalRequest.Status.CANCELLED
    ).count()
    assert cancelled == 1


@pytest.mark.django_db
def test_approve_advances_to_next_step(company, requester, approver, chief, rule_50_500, target_obj):
    req = ApprovalService.submit(
        obj=target_obj, voucher_type="sales_receipt",
        amount=Decimal("100000000"), requested_by=requester,
    )
    ApprovalService.approve(req, approver, note="OK step 1")
    req.refresh_from_db()
    assert req.status == ApprovalRequest.Status.PENDING
    assert req.steps.get(sequence=1).status == "approved"
    assert req.steps.get(sequence=1).approved_by == approver
    assert req.steps.get(sequence=2).status == "pending"


@pytest.mark.django_db
def test_approve_final_step_finalizes(company, requester, approver, chief, rule_50_500, target_obj):
    req = ApprovalService.submit(
        obj=target_obj, voucher_type="sales_receipt",
        amount=Decimal("100000000"), requested_by=requester,
    )
    ApprovalService.approve(req, approver)
    ApprovalService.approve(req, chief)
    req.refresh_from_db()
    assert req.status == ApprovalRequest.Status.APPROVED
    assert req.completed_at is not None


@pytest.mark.django_db
def test_reject_blocks_remaining_steps(company, requester, approver, chief, rule_50_500, target_obj):
    req = ApprovalService.submit(
        obj=target_obj, voucher_type="sales_receipt",
        amount=Decimal("100000000"), requested_by=requester,
    )
    ApprovalService.reject(req, approver, reason="Quá đắt")
    req.refresh_from_db()
    assert req.status == ApprovalRequest.Status.REJECTED
    assert "Quá đắt" in req.rejection_reason
    assert req.steps.filter(status="rejected").exists()


@pytest.mark.django_db
def test_pending_for_user_filters_by_role(company, requester, approver, chief, rule_50_500, target_obj):
    ApprovalService.submit(
        obj=target_obj, voucher_type="sales_receipt",
        amount=Decimal("100000000"), requested_by=requester,
    )
    assert ApprovalService.pending_for_user(approver, company).count() == 1
    assert ApprovalService.pending_for_user(chief, company).count() == 1
    assert ApprovalService.pending_for_user(requester, company).count() == 0


@pytest.mark.django_db
def test_notification_fired_to_next_approver(company, requester, approver, rule_50_500, target_obj):
    ApprovalService.submit(
        obj=target_obj, voucher_type="sales_receipt",
        amount=Decimal("100000000"), requested_by=requester,
    )
    assert Notification.objects.filter(user=approver).count() == 1


@pytest.mark.django_db
def test_submitter_notified_on_approval(company, requester, approver, chief, rule_50_500, target_obj):
    req = ApprovalService.submit(
        obj=target_obj, voucher_type="sales_receipt",
        amount=Decimal("100000000"), requested_by=requester,
    )
    ApprovalService.approve(req, approver)
    ApprovalService.approve(req, chief)
    assert Notification.objects.filter(user=requester).count() == 1


@pytest.mark.django_db
def test_submitter_notified_on_rejection(company, requester, approver, chief, rule_50_500, target_obj):
    req = ApprovalService.submit(
        obj=target_obj, voucher_type="sales_receipt",
        amount=Decimal("100000000"), requested_by=requester,
    )
    ApprovalService.reject(req, approver, reason="x")
    assert Notification.objects.filter(user=requester).count() == 1
