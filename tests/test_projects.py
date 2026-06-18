"""Tests for Project Management module — Project, Phase, Resource, Transaction."""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company
from apps.hr.models import Department, Employee, Position
from apps.projects.models import (
    Project,
    ProjectPhase,
    ProjectResource,
    ProjectTransaction,
)
from apps.projects.services import ProjectService


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="TCO",
        name="Test Company",
        tax_code="0101234567",
        accounting_regime="tt133",
    )


@pytest.fixture
def project(company):
    return Project.objects.create(
        company=company,
        code="PRJ001",
        name="Website Redesign",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        budget_revenue=Decimal("100000000"),
        budget_cost=Decimal("50000000"),
        status="active",
    )


@pytest.mark.django_db
def test_project_creation(project):
    assert project.pk is not None
    assert str(project) == "PRJ001 - Website Redesign"
    assert project.status == "active"
    assert project.priority == "medium"
    assert project.progress_percent == 0


@pytest.mark.django_db
def test_project_is_overdue(company):
    """is_overdue True when end_date passed and not completed/cancelled."""
    p = Project.objects.create(
        company=company,
        code="OD001",
        name="Late project",
        start_date=date(2020, 1, 1),
        end_date=date(2020, 6, 30),
        status="active",
    )
    assert p.is_overdue is True

    p.status = "completed"
    assert p.is_overdue is False

    p2 = Project.objects.create(
        company=company,
        code="OD002",
        name="Future project",
        start_date=date(2030, 1, 1),
        end_date=date(2030, 6, 30),
        status="active",
    )
    assert p2.is_overdue is False


@pytest.mark.django_db
def test_project_phase(project):
    phase = ProjectPhase.objects.create(
        project=project,
        sequence=1,
        name="Analysis",
        weight=Decimal("20"),
        status="completed",
    )
    assert phase.pk is not None
    assert "Phase 1" in str(phase)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_project_phase_unique_sequence(project):
    """Same sequence cannot be reused within a project."""
    from django.db import IntegrityError

    ProjectPhase.objects.create(project=project, sequence=1, name="A", weight=Decimal("10"))
    with pytest.raises(IntegrityError):
        ProjectPhase.objects.create(project=project, sequence=1, name="B", weight=Decimal("10"))


@pytest.mark.django_db
def test_progress_calculation(project):
    ProjectPhase.objects.create(
        project=project,
        sequence=1,
        name="Analysis",
        weight=Decimal("30"),
        status="completed",
    )
    ProjectPhase.objects.create(
        project=project,
        sequence=2,
        name="Design",
        weight=Decimal("30"),
        status="in_progress",
    )
    ProjectPhase.objects.create(
        project=project,
        sequence=3,
        name="Implementation",
        weight=Decimal("40"),
        status="not_started",
    )

    progress = ProjectService.calculate_progress(project)
    # completed: 30% + in_progress: 30%*0.5 = 15% -> total 45%
    assert progress == Decimal("45.00")

    project.refresh_from_db()
    assert project.progress_percent == Decimal("45.00")


@pytest.mark.django_db
def test_progress_no_phases_returns_existing(project):
    """No phases -> returns existing progress_percent."""
    project.progress_percent = Decimal("33.00")
    project.save()
    progress = ProjectService.calculate_progress(project)
    assert progress == Decimal("33.00")


@pytest.mark.django_db
def test_progress_zero_weight_returns_existing(project):
    """Phases exist but all weights 0 -> returns existing progress."""
    ProjectPhase.objects.create(project=project, sequence=1, name="A", weight=0, status="completed")
    project.progress_percent = Decimal("20.00")
    project.save()
    progress = ProjectService.calculate_progress(project)
    assert progress == Decimal("20.00")


@pytest.mark.django_db
def test_progress_capped_at_100(project):
    """Progress cannot exceed 100 even if weights are mismatched."""
    ProjectPhase.objects.create(
        project=project,
        sequence=1,
        name="A",
        weight=Decimal("50"),
        status="completed",
    )
    ProjectPhase.objects.create(
        project=project,
        sequence=2,
        name="B",
        weight=Decimal("50"),
        status="completed",
    )
    ProjectPhase.objects.create(
        project=project,
        sequence=3,
        name="C",
        weight=Decimal("50"),
        status="completed",
    )
    progress = ProjectService.calculate_progress(project)
    assert progress == Decimal("100.00")


@pytest.mark.django_db
def test_cost_summary(project):
    ProjectTransaction.objects.create(
        project=project,
        transaction_type="revenue",
        transaction_date=date(2026, 6, 15),
        amount=Decimal("50000000"),
    )
    ProjectTransaction.objects.create(
        project=project,
        transaction_type="labor_cost",
        transaction_date=date(2026, 6, 20),
        amount=Decimal("20000000"),
    )
    ProjectTransaction.objects.create(
        project=project,
        transaction_type="material_cost",
        transaction_date=date(2026, 6, 22),
        amount=Decimal("5000000"),
    )

    summary = ProjectService.get_cost_summary(project)
    assert summary["actual_revenue"] == Decimal("50000000")
    assert summary["actual_cost"] == Decimal("25000000")
    assert summary["profit"] == Decimal("25000000")
    assert summary["cost_variance"] == Decimal("25000000")  # 50M budget - 25M actual
    assert summary["revenue_variance"] == Decimal("50000000")  # 100M - 50M
    assert summary["margin"] == Decimal("50")  # 25M / 50M * 100


@pytest.mark.django_db
def test_cost_summary_no_revenue(project):
    """Margin is 0 when no revenue."""
    ProjectTransaction.objects.create(
        project=project,
        transaction_type="labor_cost",
        transaction_date=date(2026, 6, 20),
        amount=Decimal("10000"),
    )
    summary = ProjectService.get_cost_summary(project)
    assert summary["actual_revenue"] == Decimal("0")
    assert summary["margin"] == 0


@pytest.mark.django_db
def test_resource_assignment(project, company):
    dept = Department.objects.create(company=company, code="IT", name="IT")
    pos = Position.objects.create(code="DEV", name="Dev", level=1)
    emp = Employee.objects.create(
        company=company,
        code="NV01",
        full_name="Dev",
        department=dept,
        position=pos,
        hire_date=date(2020, 1, 1),
        base_salary=Decimal("20000000"),
    )

    res = ProjectResource.objects.create(
        project=project,
        resource_type="human",
        employee=emp,
        role="Developer",
        quantity=Decimal("160"),
        unit="hours",
        unit_cost=Decimal("200000"),  # 200k/hour
    )
    res.refresh_from_db()
    # planned_cost = 160 * 200000 = 32,000,000
    assert res.planned_cost == Decimal("32000000")
    assert "human" in str(res)


@pytest.mark.django_db
def test_resource_explicit_planned_cost_kept(project, company):
    """When planned_cost is provided, save() should not overwrite."""
    dept = Department.objects.create(company=company, code="IT", name="IT")
    pos = Position.objects.create(code="DEV", name="Dev", level=1)
    emp = Employee.objects.create(
        company=company,
        code="NV01",
        full_name="Dev",
        department=dept,
        position=pos,
        hire_date=date(2020, 1, 1),
    )
    res = ProjectResource.objects.create(
        project=project,
        resource_type="human",
        employee=emp,
        quantity=Decimal("100"),
        unit_cost=Decimal("1000"),
        planned_cost=Decimal("99999"),
    )
    res.refresh_from_db()
    assert res.planned_cost == Decimal("99999")


@pytest.mark.django_db
def test_resource_summary(project, company):
    dept = Department.objects.create(company=company, code="IT", name="IT")
    pos = Position.objects.create(code="DEV", name="Dev", level=1)
    e1 = Employee.objects.create(
        company=company,
        code="NV01",
        full_name="A",
        department=dept,
        position=pos,
        hire_date=date(2020, 1, 1),
    )
    e2 = Employee.objects.create(
        company=company,
        code="NV02",
        full_name="B",
        department=dept,
        position=pos,
        hire_date=date(2020, 1, 1),
    )

    ProjectResource.objects.create(
        project=project,
        resource_type="human",
        employee=e1,
        quantity=Decimal("100"),
        unit_cost=Decimal("100"),
        planned_cost=Decimal("10000"),
        actual_cost=Decimal("8000"),
    )
    ProjectResource.objects.create(
        project=project,
        resource_type="human",
        employee=e2,
        quantity=Decimal("50"),
        unit_cost=Decimal("200"),
        planned_cost=Decimal("10000"),
        actual_cost=Decimal("12000"),
    )
    ProjectResource.objects.create(
        project=project,
        resource_type="material",
        quantity=Decimal("5"),
        unit_cost=Decimal("1000"),
        planned_cost=Decimal("5000"),
        actual_cost=Decimal("5000"),
    )

    summary = ProjectService.get_resource_summary(project)
    assert summary["human_count"] == 2
    assert summary["material_count"] == 1
    assert summary["human_cost_planned"] == Decimal("20000")
    assert summary["human_cost_actual"] == Decimal("20000")
    assert summary["material_cost_planned"] == Decimal("5000")
    assert summary["material_cost_actual"] == Decimal("5000")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_project_unique_code_per_company(company):
    """Same code is allowed for different companies but unique within one."""
    from django.db import IntegrityError

    Project.objects.create(company=company, code="X1", name="A", start_date=date(2026, 1, 1))
    with pytest.raises(IntegrityError):
        Project.objects.create(company=company, code="X1", name="B", start_date=date(2026, 1, 1))

    other = Company.objects.create(
        code="OTHER",
        name="Other",
        tax_code="9999999999",
        accounting_regime="tt133",
    )
    Project.objects.create(
        company=other, code="X1", name="A copy", start_date=date(2026, 1, 1)
    )  # different company -> OK


@pytest.mark.django_db
def test_transaction_str(project):
    t = ProjectTransaction.objects.create(
        project=project,
        transaction_type="labor_cost",
        transaction_date=date(2026, 6, 1),
        amount=Decimal("5000000"),
    )
    assert "PRJ001" in str(t)
    assert "labor_cost" in str(t)


@pytest.mark.django_db
def test_project_linked_to_contract(company):
    """Project can be linked to a Contract."""
    from apps.contracts.models import Contract

    contract = Contract.objects.create(
        company=company,
        contract_no="HD-2026-001",
        contract_date=date(2026, 1, 1),
        contract_type=Contract.ContractType.SERVICE,
        party_name="Cty ABC",
        value=Decimal("200000000"),
        status="active",
    )
    p = Project.objects.create(
        company=company,
        code="PRJ-C-001",
        name="Service project",
        start_date=date(2026, 2, 1),
        contract=contract,
        customer_name="Cty ABC",
    )
    p.refresh_from_db()
    assert p.contract_id == contract.pk
    assert contract.projects.count() == 1
    assert contract.projects.first().pk == p.pk
