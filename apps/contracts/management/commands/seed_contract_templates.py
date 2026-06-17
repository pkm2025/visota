"""Seed 7 contract templates with full Vietnamese legal text."""

from django.core.management.base import BaseCommand

from apps.contracts.models import ContractTemplate

LEGAL_BASIS_LABOR = (
    "Bộ luật Lao động 45/2019/QH14 (Điều 20, 21, 22, 23, 24, 25, 26, 27, 28); "
    "Luật Bảo hiểm xã hội 41/2024/QH15; Luật Bảo hiểm y tế (sửa đổi) 51/2024/QH15; "
    "Nghị định 74/2024/NĐ-CP (lương tối thiểu vùng); Nghị định 73/2024/NĐ-CP (lương cơ sở 2.340.000đ)."
)
LEGAL_BASIS_CIVIL = "Bộ luật Dân sự 91/2015/QH13 (Điều 388-410, 484-510, 528-547)."

LABOR_FIXED_HTML = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>Hợp đồng lao động xác định thời hạn</title></head>
<body>
<h2>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</h2>
<p>Độc lập - Tự do - Hạnh phúc</p>
<h3>HỢP ĐỒNG LAO ĐỘNG XÁC ĐỊNH THỜI HẠN</h3>
<p>(Số: {{ contract_no }})</p>
<p>Hôm nay, ngày {{ today|date:"d/m/Y" }}, tại {{ company.name }}, chúng tôi gồm:</p>
<p><strong>BÊN A — NGƯỜI LAO ĐỘNG:</strong></p>
<ul>
  <li>Họ và tên: {{ contract.party_name }}</li>
  <li>Ngày sinh: {{ employee_birth_date|default:"" }}</li>
  <li>Số CCCD: {{ party_tax_code|default:"" }}</li>
  <li>Địa chỉ: {{ party_address|default:"" }}</li>
</ul>
<p><strong>BÊN B — NGƯỜI SỬ DỤNG LAO ĐỘNG:</strong></p>
<ul>
  <li>{{ company.name }}</li>
  <li>Mã số thuế: {{ company.tax_code }}</li>
  <li>Địa chỉ: {{ company.address }}</li>
  <li>Người đại diện: {{ company.legal_representative|default:"" }}</li>
</ul>
<p>Điều 1. Thời hạn hợp đồng: Từ {{ start_date|date:"d/m/Y" }} đến {{ end_date|date:"d/m/Y" }}.</p>
<p>Điều 2. Công việc: {{ contract.description|default:"Theo vị trí phân công" }}.</p>
<p>Điều 3. Tiền lương: {{ value }} {{ currency_code }} được trả tháng vào ngày hàng tháng.</p>
<p>Điều 4. Bảo hiểm, chế độ theo BLLĐ 2019 và Luật BHXH 41/2024/QH15.</p>
<p style="margin-top:40px">
  <em>Căn cứ pháp lý: %s</em>
</p>
</body></html>
""" % LEGAL_BASIS_LABOR

LABOR_INDEFINITE_HTML = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>Hợp đồng lao động không xác định thời hạn</title></head>
<body>
<h2>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</h2>
<p>Độc lập - Tự do - Hạnh phúc</p>
<h3>HỢP ĐỒNG LAO ĐỘNG KHÔNG XÁC ĐỊNH THỜI HẠN</h3>
<p>(Số: {{ contract_no }})</p>
<p><strong>BÊN A — NGƯỜI LAO ĐỘNG:</strong> {{ contract.party_name }} — CCCD {{ party_tax_code|default:"" }}</p>
<p><strong>BÊN B — NGƯỜI SỬ DỤNG LAO ĐỘNG:</strong> {{ company.name }} (MST {{ company.tax_code }})</p>
<p>Điều 1. Thời hạn: không xác định thời hạn, bắt đầu từ {{ start_date|date:"d/m/Y" }}.</p>
<p>Điều 2. Tiền lương: {{ value }} {{ currency_code }}.</p>
<p>Điều 3. Quyền, nghĩa vụ theo BLLĐ 2019, Luật BHXH 41/2024/QH15, Luật BHYT 51/2024/QH15.</p>
<p style="margin-top:40px"><em>Căn cứ pháp lý: %s</em></p>
</body></html>
""" % LEGAL_BASIS_LABOR

LABOR_PROBATION_HTML = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>Hợp đồng thử việc</title></head>
<body>
<h2>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</h2>
<p>Độc lập - Tự do - Hạnh phúc</p>
<h3>HỢP ĐỒNG THỬ VIỆC</h3>
<p>(Số: {{ contract_no }})</p>
<p><strong>Người lao động:</strong> {{ contract.party_name }}</p>
<p><strong>Người sử dụng lao động:</strong> {{ company.name }}</p>
<p>Điều 1. Vị trí thử việc: {{ contract.description|default:"" }}</p>
<p>Điều 2. Thời gian thử việc tối đa 60 ngày theo Điều 27 BLLĐ 2019 (hoặc 30 ngày đối với chuyên môn trung cấp, 180 ngày đối với đại từ trở lên).</p>
<p>Điều 3. Tiền lương thử việc: {{ value }} {{ currency_code }} (ít nhất 85%% mức lương chính thức).</p>
<p>Điều 4. Thời hạn: {{ start_date|date:"d/m/Y" }} đến {{ end_date|date:"d/m/Y" }}.</p>
<p style="margin-top:40px"><em>Căn cứ pháp lý: %s (Điều 24-27).</em></p>
</body></html>
""" % LEGAL_BASIS_LABOR

SALE_HTML = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>Hợp đồng mua bán hàng hóa</title></head>
<body>
<h2>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</h2>
<p>Độc lập - Tự do - Hạnh phúc</p>
<h3>HỢP ĐỒNG MUA BÁN HÀNG HÓA</h3>
<p>(Số: {{ contract_no }} — ngày {{ contract_date|date:"d/m/Y" }})</p>
<p><strong>BÊN BÁN:</strong> {{ company.name }} — MST {{ company.tax_code }} — {{ company.address }}</p>
<p><strong>BÊN MUA:</strong> {{ contract.party_name }} — MST {{ party_tax_code|default:"" }} — {{ party_address|default:"" }}</p>
<p>Điều 1. Đối tượng hợp đồng: {{ contract.description|default:"Hàng hóa" }}.</p>
<p>Điều 2. Giá trị hợp đồng: {{ value }} {{ currency_code }} (đã bao gồm VAT nếu có).</p>
<p>Điều 3. Thời hạn thực hiện: {{ start_date|date:"d/m/Y" }} đến {{ end_date|date:"d/m/Y" }}.</p>
<p>Điều 4. Thanh toán, giao nhận, phạt vi phạm theo BLDS 2015 và Luật Thương mại 2005.</p>
<p style="margin-top:40px"><em>Căn cứ pháp lý: %s</em></p>
</body></html>
""" % LEGAL_BASIS_CIVIL

SERVICE_HTML = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>Hợp đồng cung cấp dịch vụ</title></head>
<body>
<h2>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</h2>
<p>Độc lập - Tự do - Hạnh phúc</p>
<h3>HỢP ĐỒNG CUNG CẤP DỊCH VỤ</h3>
<p>(Số: {{ contract_no }} — ngày {{ contract_date|date:"d/m/Y" }})</p>
<p><strong>BÊN CUNG CẤP DỊCH VỤ:</strong> {{ company.name }} — MST {{ company.tax_code }}</p>
<p><strong>BÊN SỬ DỤNG DỊCH VỤ:</strong> {{ contract.party_name }}</p>
<p>Điều 1. Nội dung dịch vụ: {{ contract.description|default:"" }}</p>
<p>Điều 2. Giá trị: {{ value }} {{ currency_code }}.</p>
<p>Điều 3. Thời gian: {{ start_date|date:"d/m/Y" }} đến {{ end_date|date:"d/m/Y" }}.</p>
<p style="margin-top:40px"><em>Căn cứ pháp lý: %s</em></p>
</body></html>
""" % LEGAL_BASIS_CIVIL

CONSTRUCTION_HTML = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>Hợp đồng thi công xây dựng</title></head>
<body>
<h2>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</h2>
<p>Độc lập - Tự do - Hạnh phúc</p>
<h3>HỢP ĐỒNG THI CÔNG XÂY DỰNG</h3>
<p>(Số: {{ contract_no }} — ngày {{ contract_date|date:"d/m/Y" }})</p>
<p><strong>BÊN GIAO THẦU (CHỦ ĐẦU TƯ):</strong> {{ contract.party_name }}</p>
<p><strong>BÊN NHẬN THẦU (NHÀ THẦU):</strong> {{ company.name }} — MST {{ company.tax_code }}</p>
<p>Điều 1. Công trình: {{ contract.description|default:"" }}</p>
<p>Điều 2. Giá trị hợp đồng: {{ value }} {{ currency_code }}.</p>
<p>Điều 3. Thời gian thi công: {{ start_date|date:"d/m/Y" }} đến {{ end_date|date:"d/m/Y" }}.</p>
<p style="margin-top:40px"><em>Căn cứ pháp lý: Luật Xây dựng 50/2014/QH13; %s</em></p>
</body></html>
""" % LEGAL_BASIS_CIVIL

APPENDIX_HTML = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>Phụ lục hợp đồng</title></head>
<body>
<h2>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</h2>
<p>Độc lập - Tự do - Hạnh phúc</p>
<h3>PHỤ LỤC HỢP ĐỒNG</h3>
<p>(Số: {{ contract_no }} — ngày {{ today|date:"d/m/Y" }})</p>
<p>Hợp đồng chính: {{ contract.contract_no }} ký ngày {{ contract_date|date:"d/m/Y" }}.</p>
<p>Điều 1. Nội dung điều chỉnh: {{ contract.description|default:"" }}</p>
<p>Điều 2. Giá trị điều chỉnh: {{ value }} {{ currency_code }}.</p>
<p style="margin-top:40px"><em>Phụ lục này là phần không tách rời của hợp đồng chính.</em></p>
</body></html>
"""

TEMPLATES = [
    {
        "code": "labor_fixed",
        "name": "HĐLĐ xác định thời hạn",
        "contract_type": "labor_fixed",
        "template_html": LABOR_FIXED_HTML,
        "required_fields": ["company", "party_name", "value", "start_date", "end_date"],
        "legal_basis": LEGAL_BASIS_LABOR,
    },
    {
        "code": "labor_indefinite",
        "name": "HĐLĐ không xác định thời hạn",
        "contract_type": "labor_indefinite",
        "template_html": LABOR_INDEFINITE_HTML,
        "required_fields": ["company", "party_name", "value", "start_date"],
        "legal_basis": LEGAL_BASIS_LABOR,
    },
    {
        "code": "labor_probation",
        "name": "HĐ thử việc",
        "contract_type": "labor_probation",
        "template_html": LABOR_PROBATION_HTML,
        "required_fields": ["company", "party_name", "value"],
        "legal_basis": LEGAL_BASIS_LABOR,
    },
    {
        "code": "sale",
        "name": "HĐ mua bán hàng hóa",
        "contract_type": "sale",
        "template_html": SALE_HTML,
        "required_fields": ["company", "party_name", "value"],
        "legal_basis": LEGAL_BASIS_CIVIL,
    },
    {
        "code": "service",
        "name": "HĐ cung cấp dịch vụ",
        "contract_type": "service",
        "template_html": SERVICE_HTML,
        "required_fields": ["company", "party_name", "value"],
        "legal_basis": LEGAL_BASIS_CIVIL,
    },
    {
        "code": "construction",
        "name": "HĐ thi công xây dựng",
        "contract_type": "construction",
        "template_html": CONSTRUCTION_HTML,
        "required_fields": ["company", "party_name", "value"],
        "legal_basis": LEGAL_BASIS_CIVIL,
    },
    {
        "code": "appendix",
        "name": "Phụ lục hợp đồng",
        "contract_type": "appendix",
        "template_html": APPENDIX_HTML,
        "required_fields": ["company", "contract"],
        "legal_basis": "Phụ thuộc hợp đồng chính.",
    },
]


class Command(BaseCommand):
    help = "Seed 7 pre-built contract templates with full Vietnamese legal text."

    def handle(self, *args, **options):
        created_count = 0
        for tpl_def in TEMPLATES:
            _, created = ContractTemplate.objects.update_or_create(
                code=tpl_def["code"],
                defaults={
                    "name": tpl_def["name"],
                    "contract_type": tpl_def["contract_type"],
                    "template_html": tpl_def["template_html"],
                    "required_fields": tpl_def["required_fields"],
                    "legal_basis": tpl_def["legal_basis"],
                    "version": "2026",
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(TEMPLATES)} contract templates ({created_count} new)."
            )
        )
