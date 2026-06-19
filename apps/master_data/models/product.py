"""Product and Warehouse master data."""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class Product(CompanyOwnedModel):
    """Product/SKU — goods or service."""

    class ProductType(models.TextChoices):
        RAW_MATERIAL = "raw_material", "Nguyên vật liệu"
        SEMI_FINISHED = "semi_finished", "Bán thành phẩm"
        FINISHED = "finished", "Thành phẩm"
        GOODS = "goods", "Hàng hóa"
        SUPPLIES = "supplies", "Vật tư"
        TOOL = "tool", "CCDC"
        SERVICE = "service", "Dịch vụ"

    class CostMethod(models.TextChoices):
        WEIGHTED_AVG = "weighted_avg", "Bình quân gia quyền"
        MOVING_AVG = "moving_avg", "Bình quân di động"
        FIFO = "fifo", "Nhập trước xuất trước"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="products",
        db_index=True,
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=500)
    name_en = models.CharField(max_length=500, blank=True, default="")
    barcode = models.CharField(max_length=50, blank=True, default="")
    product_type = models.CharField(max_length=20, choices=ProductType.choices)
    unit_id = models.CharField(max_length=20)
    product_group_code = models.CharField(max_length=50, blank=True, default="")

    weight = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    volume = models.DecimalField(max_digits=18, decimal_places=4, default=0)

    cost_method = models.CharField(
        max_length=20,
        choices=CostMethod.choices,
        default=CostMethod.WEIGHTED_AVG,
    )
    gl_account_inv = models.CharField(max_length=20)
    gl_account_cogs = models.CharField(max_length=20)
    gl_account_revenue = models.CharField(max_length=20)
    default_vat_rate = models.DecimalField(max_digits=6, decimal_places=4, default=0.10)
    default_unit_price = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    min_stock = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    max_stock = models.DecimalField(max_digits=18, decimal_places=4, default=0)

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "product"
        unique_together = [("company", "code")]
        ordering = ["code"]
        indexes = [
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["barcode"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class ProductPrice(models.Model):
    """Price tier — different prices per customer group or quantity."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="prices",
    )
    name = models.CharField(max_length=100)  # 'Giá sỉ', 'Giá lẻ', 'Giá VIP'
    min_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    unit_price = models.DecimalField(max_digits=20, decimal_places=4)
    currency_code = models.CharField(max_length=3, default="VND")
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_price"
        ordering = ["min_quantity"]

    def __str__(self):
        return f"{self.product.code} {self.name} @ {self.unit_price}"


class ProductVariant(models.Model):
    """Product variant — size, color, etc."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    attribute_name = models.CharField(max_length=100)  # 'Color', 'Size'
    attribute_value = models.CharField(max_length=100)  # 'Red', 'XL'
    barcode = models.CharField(max_length=50, blank=True, default="")
    unit_price_adjustment = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "product_variant"
        unique_together = [("product", "code")]

    def __str__(self):
        return f"{self.product.code} - {self.code} ({self.attribute_value})"


class Warehouse(CompanyOwnedModel):
    """Warehouse / kho."""

    class WarehouseType(models.TextChoices):
        MATERIAL = "material", "Kho nguyên vật liệu"
        FINISHED = "finished", "Kho thành phẩm"
        TRANSIT = "transit", "Kho chuyển hàng"
        VIRTUAL = "virtual", "Kho ảo"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="warehouses",
        db_index=True,
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    warehouse_type = models.CharField(
        max_length=20,
        choices=WarehouseType.choices,
        default=WarehouseType.MATERIAL,
    )
    manager_code = models.CharField(max_length=50, blank=True, default="")
    address = models.TextField(blank=True, default="")
    gl_account = models.CharField(max_length=20, blank=True, default="")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "warehouse"
        unique_together = [("company", "code")]
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"
