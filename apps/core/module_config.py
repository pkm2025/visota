"""Module visibility configuration for the modular sidebar.

Core modules are shown by default for DNSN (TT58) companies.
Advanced modules are hidden by default but can be enabled per-company
in the settings UI. The "Hệ thống" section is always visible regardless
of module visibility settings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.core.models import Company


# --- Module definitions --------------------------------------------------

# Modules always shown in the sidebar. These are the core business areas
# every company needs (accounting, sales, purchasing, invoicing, inventory,
# reporting). "he_thong" (Hệ thống) is always visible and never appears in
# either advanced or enabled lists.
CORE_MODULES: list[str] = [
    "ke_toan",  # Kế toán (ledger, treasury, banking, input_docs, recurring, loans, guarantees)
    "ban_hang",  # Bán hàng (sales)
    "mua_hang",  # Mua hàng (purchasing)
    "hoa_don",  # Hóa đơn (einvoice)
    "kho",  # Kho (inventory)
    "bao_cao",  # Báo cáo (reporting)
]

# Advanced modules hidden by default for DNSN companies. Admins can enable
# them from the settings UI. Each maps to one or more permission modules.
ADVANCED_MODULES: list[str] = [
    "nhan_su",  # HR (hr, payroll)
    "tai_san",  # Tài sản (assets)
    "crm",  # CRM
    "ngan_sach",  # Ngân sách (budget)
    "dau_thau",  # Đấu thầu (bidding)
    "du_an",  # Dự án (projects)
    "vay",  # Vay vốn (loans)
    "bao_lanh",  # Bảo lãnh (guarantees)
]

# Mapping from display module keys (used in settings UI and enabled_modules
# JSON) to the underlying permission module codes checked by has_module_access.
# A display module may expand to multiple permission modules — the module is
# considered visible when at least one of its permission modules is visible.
MODULE_PERMISSION_MAP: dict[str, list[str]] = {
    # Core modules
    "ke_toan": ["ledger", "treasury", "banking", "input_docs", "recurring"],
    "ban_hang": ["sales"],
    "mua_hang": ["purchasing"],
    "hoa_don": ["einvoice"],
    "kho": ["inventory"],
    "bao_cao": ["reporting"],
    # Advanced modules
    "nhan_su": ["hr", "payroll"],
    "tai_san": ["assets"],
    "crm": ["crm"],
    "ngan_sach": ["budget"],
    "dau_thau": ["bidding"],
    "du_an": ["projects"],
    "vay": ["loans"],
    "bao_lanh": ["guarantees"],
}

# Vietnamese labels for each module (for settings UI).
MODULE_LABELS: dict[str, str] = {
    "ke_toan": "Kế toán",
    "ban_hang": "Bán hàng",
    "mua_hang": "Mua hàng",
    "hoa_don": "Hóa đơn",
    "kho": "Kho",
    "bao_cao": "Báo cáo",
    "nhan_su": "Nhân sự",
    "tai_san": "Tài sản",
    "crm": "CRM",
    "ngan_sach": "Ngân sách",
    "dau_thau": "Đấu thầu",
    "du_an": "Dự án",
    "vay": "Vay vốn",
    "bao_lanh": "Bảo lãnh",
}

# Human-readable descriptions for the settings UI.
MODULE_DESCRIPTIONS: dict[str, str] = {
    "ke_toan": "Kế toán tổng hợp — phiếu kế toán, sổ cái, bút toán, khóa sổ",
    "ban_hang": "Hóa đơn bán hàng, khách hàng, công nợ phải thu",
    "mua_hang": "Hóa đơn mua hàng, nhà cung cấp, công nợ phải trả",
    "hoa_don": "Hóa đơn điện tử TT78/2021",
    "kho": "Nhập/xuất/tồn, phiếu kho, kiểm kê",
    "bao_cao": "Báo cáo tài chính — B01, B02, BCĐTK, VAT, TNCN",
    "nhan_su": "Nhân viên, hợp đồng lao động, BHXH, tính lương",
    "tai_san": "Tài sản cố định, khấu hao, thanh lý",
    "crm": "Quản lý quan hệ khách hàng — lead, cơ hội, ticket",
    "ngan_sach": "Ngân sách & dự phóng dòng tiền",
    "dau_thau": "Cơ hội đấu thầu, hồ sơ dự thầu",
    "du_an": "Quản lý dự án, giai đoạn, tiến độ",
    "vay": "Vay vốn ngân hàng, lãi vay, tất toán",
    "bao_lanh": "Bảo lãnh ngân hàng — bid bond, performance",
}

# All configurable modules (core + advanced) in display order.
ALL_MODULES: list[str] = CORE_MODULES + ADVANCED_MODULES


class ModuleVisibilityService:
    """Service for determining which sidebar modules are visible.

    Rules:
    - Core modules are always visible (subject to permission checks).
    - Advanced modules are hidden by default unless explicitly enabled
      in the company's ``enabled_modules`` JSON field.
    - The "Hệ thống" (system) section is always visible and never gated
      by module visibility settings.
    - For non-DNSN companies (tt133/tt200/q48), all modules are visible
      by default (advanced modules only hidden for DNSN/TT58 companies).
    """

    def __init__(self, company: Company | None):
        self.company = company

    @property
    def _is_dnsn(self) -> bool:
        """Return True if this company uses the TT58 (DNSN) regime."""
        if not self.company:
            return False
        return getattr(self.company, "accounting_regime", "") == "tt58"

    def _get_enabled_modules(self) -> set[str]:
        """Return the set of explicitly-enabled display module keys."""
        if not self.company:
            return set()
        raw = getattr(self.company, "enabled_modules", None) or {}
        if isinstance(raw, dict):
            return {k for k, v in raw.items() if v}
        return set()

    def is_module_visible(self, display_module: str) -> bool:
        """Check if a display module should be visible in the sidebar.

        Core modules are always visible.
        Advanced modules are visible only if explicitly enabled (for DNSN)
        or always visible for non-DNSN companies.
        """
        # Non-existent module key — not visible
        if display_module not in ALL_MODULES and display_module != "he_thong":
            return False

        # Hệ thống is always visible
        if display_module == "he_thong":
            return True

        # Core modules are always visible (when a company exists)
        if display_module in CORE_MODULES:
            return self.company is not None

        # No company — advanced modules not visible
        if not self.company:
            return False

        # Advanced modules: for non-DNSN companies, all visible by default
        if not self._is_dnsn:
            return True

        # For DNSN: advanced module visible only if explicitly enabled
        return display_module in self._get_enabled_modules()

    def is_permission_module_visible(self, perm_module: str) -> bool:
        """Check if a permission-level module (e.g. ``hr``, ``assets``) is visible.

        A permission module is visible if at least one display module that
        maps to it is visible.

        Permission modules that are **not** listed in ``MODULE_PERMISSION_MAP``
        (e.g. ``pkm``, ``master_data``, ``contracts``, ``fx``, ``approvals``,
        ``documents``, ``notifications``) are not part of any configurable
        display module. For non-DNSN companies these default to visible so
        that the sidebar navigation works as before. For DNSN companies they
        default to hidden (conservative: only mapped modules are shown).
        """
        mapped = False
        for display_module, perm_modules in MODULE_PERMISSION_MAP.items():
            if perm_module in perm_modules:
                mapped = True
                if self.is_module_visible(display_module):
                    return True
        if mapped:
            return False

        # Unmapped permission module: default to visible for non-DNSN
        # companies, hidden for DNSN companies and when no company is set.
        if not self.company:
            return False
        return not self._is_dnsn

    def get_visible_display_modules(self) -> list[str]:
        """Return ordered list of visible display module keys."""
        return [m for m in ALL_MODULES if self.is_module_visible(m)]

    def get_hidden_display_modules(self) -> list[str]:
        """Return ordered list of hidden display module keys."""
        return [m for m in ALL_MODULES if not self.is_module_visible(m)]

    def get_enabled_display_modules(self) -> list[str]:
        """Return the set of explicitly-enabled advanced module keys."""
        return sorted(self._get_enabled_modules())

    def enable_module(self, display_module: str) -> None:
        """Enable an advanced module for this company."""
        if not self.company:
            return
        if display_module not in ADVANCED_MODULES:
            return
        enabled = dict(self.company.enabled_modules or {})
        enabled[display_module] = True
        self.company.enabled_modules = enabled

    def disable_module(self, display_module: str) -> None:
        """Disable an advanced module for this company."""
        if not self.company:
            return
        if display_module not in ADVANCED_MODULES:
            return
        enabled = dict(self.company.enabled_modules or {})
        enabled[display_module] = False
        self.company.enabled_modules = enabled

    def set_enabled_modules(self, module_keys: list[str]) -> None:
        """Set the complete list of enabled advanced modules."""
        if not self.company:
            return
        valid = {m for m in module_keys if m in ADVANCED_MODULES}
        enabled = {m: (m in valid) for m in ADVANCED_MODULES}
        self.company.enabled_modules = enabled


# Module-level helper functions (convenience for templates/templatetags)


def get_module_visibility_service(company: Company | None) -> ModuleVisibilityService:
    """Factory function to create a ModuleVisibilityService."""
    return ModuleVisibilityService(company)
