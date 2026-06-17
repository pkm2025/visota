"""HR models: Department, Position, Employee."""

from .employee import Department, Employee, Position
from .labor_contract import Dependent, LaborContract

__all__ = ["Department", "Position", "Employee", "LaborContract", "Dependent"]
