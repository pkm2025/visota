"""UX framework: InteractionStyleRegistry (plugin system for UX variants).

Supports multiple interaction styles per operation (Guided/Standard/Quick/Bulk).
Layout packs (Modern/Classic/Mobile/Portal) are orthogonal — see apps/core/ux/defaults.py.
"""

# Core operations that may have multiple interaction styles
CORE_OPERATIONS = [
    'voucher.create', 'voucher.edit',
    'sales_invoice.create', 'sales_invoice.edit',
    'purchase_invoice.create', 'purchase_invoice.edit',
    'customer.create', 'vendor.create', 'product.create',
    'stock_voucher.create',
    'period.closing',
]


class InteractionStyle:
    """Base class for interaction styles (Guided, Standard, Quick, Bulk).

    Subclasses define:
    - code: unique identifier ('guided', 'standard', 'quick', 'bulk')
    - name: human-readable name
    - description: short description for switcher UI
    - template_prefix: directory prefix for templates
    - url_suffix: URL path segment (empty for default/standard)
    - required_permission: permission code required to use this style (None = no restriction)
    - supported_operations: list of operations this style supports
    """

    code: str = ''
    name: str = ''
    description: str = ''
    template_prefix: str = ''
    url_suffix: str = ''
    required_permission: str | None = None
    supported_operations: list[str] = []

    @classmethod
    def get_template(cls, operation: str, template_name: str = 'form.html') -> str:
        """Return template path for an operation under this style."""
        return f'{cls.template_prefix}/{operation}/{template_name}'

    @classmethod
    def supports(cls, operation: str) -> bool:
        """Check if this style supports a given operation."""
        return operation in cls.supported_operations


class GuidedStyle(InteractionStyle):
    """Wizard-style for newcomers. Step-by-step with tooltips and smart defaults."""

    code = 'guided'
    name = 'Hướng dẫn'
    description = 'Wizard từng bước cho người mới'
    template_prefix = 'guided'
    url_suffix = 'guided'
    required_permission = None
    supported_operations = [
        'voucher.create', 'voucher.edit',
        'sales_invoice.create', 'sales_invoice.edit',
        'purchase_invoice.create',
        'customer.create', 'vendor.create', 'product.create',
    ]


class StandardStyle(InteractionStyle):
    """Default full form for accountants. Single page with all fields + keyboard shortcuts."""

    code = 'standard'
    name = 'Tiêu chuẩn'
    description = 'Form đầy đủ cho kế toán chuyên nghiệp'
    template_prefix = 'standard'
    url_suffix = ''  # default — no URL suffix
    required_permission = None
    supported_operations = list(CORE_OPERATIONS)  # supports all


class QuickStyle(InteractionStyle):
    """Minimal form for fast data entry. Type-ahead, Enter-to-next-field."""

    code = 'quick'
    name = 'Nhanh'
    description = 'Minimal fields, smart defaults'
    template_prefix = 'quick'
    url_suffix = 'quick'
    required_permission = None
    supported_operations = [
        'voucher.create',
        'sales_invoice.create',
        'purchase_invoice.create',
        'customer.create', 'vendor.create', 'product.create',
    ]


class BulkStyle(InteractionStyle):
    """Paste from Excel for batch entry. Bulk validate + create."""

    code = 'bulk'
    name = 'Hàng loạt'
    description = 'Paste Excel, preview, bulk create'
    template_prefix = 'bulk'
    url_suffix = 'bulk'
    required_permission = None
    supported_operations = [
        'voucher.create',
        'sales_invoice.create',
        'customer.create', 'vendor.create', 'product.create',
    ]


class InteractionStyleRegistry:
    """Registry of available interaction styles. Plugins can register custom styles."""

    _registry: dict[str, type[InteractionStyle]] = {}

    @classmethod
    def register(cls, style_class: type[InteractionStyle]) -> None:
        """Register a new interaction style. Overwrites existing with same code."""
        cls._registry[style_class.code] = style_class

    @classmethod
    def get(cls, code: str) -> type[InteractionStyle] | None:
        """Look up a style by code. Returns None if not registered."""
        return cls._registry.get(code)

    @classmethod
    def all(cls) -> list[type[InteractionStyle]]:
        """Return all registered style classes."""
        return list(cls._registry.values())

    @classmethod
    def all_codes(cls) -> list[str]:
        """Return all registered style codes."""
        return list(cls._registry.keys())

    @classmethod
    def for_operation(cls, operation: str) -> list[type[InteractionStyle]]:
        """Return all styles that support a given operation."""
        return [s for s in cls.all() if s.supports(operation)]

    @classmethod
    def for_user(cls, user, operation: str) -> list[type[InteractionStyle]]:
        """Return styles the user is allowed to use for a given operation."""
        result = []
        for s in cls.for_operation(operation):
            if not s.required_permission:
                result.append(s)
            elif user.is_superuser:
                result.append(s)
            else:
                # Check permission via UserService if we have a company context
                from apps.identity.services import UserService
                company = getattr(user, '_current_company', None)
                if company and UserService(user, company).has_permission(s.required_permission):
                    result.append(s)
        return result


# Register built-in styles at module import
InteractionStyleRegistry.register(GuidedStyle)
InteractionStyleRegistry.register(StandardStyle)
InteractionStyleRegistry.register(QuickStyle)
InteractionStyleRegistry.register(BulkStyle)
