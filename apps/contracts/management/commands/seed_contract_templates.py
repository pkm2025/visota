"""Seed 13 contract templates with full Vietnamese legal text."""

from django.core.management.base import BaseCommand

from apps.contracts.models import ContractTemplate

LEGAL_BASIS_LABOR = (
    "Bộ luật Lao động 45/2019/QH14 (Điều 20, 21, 22, 23, 24, 25, 26, 27, 28); "
    "Luật Bảo hiểm xã hội 41/2024/QH15; Luật Bảo hiểm y tế (sửa đổi) 51/2024/QH15; "
    "Nghị định 74/2024/NĐ-CP (lương tối thiểu vùng); Nghị định 73/2024/NĐ-CP (lương cơ sở 2.340.000đ)."
)
LEGAL_BASIS_CIVIL = "Bộ luật Dân sự 91/2015/QH13 (Điều 388-410, 484-510, 528-547)."

LABOR_FIXED_HTML = (
    """<!DOCTYPE html>
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
"""
    % LEGAL_BASIS_LABOR
)

LABOR_INDEFINITE_HTML = (
    """<!DOCTYPE html>
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
"""
    % LEGAL_BASIS_LABOR
)

LABOR_PROBATION_HTML = (
    """<!DOCTYPE html>
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
"""
    % LEGAL_BASIS_LABOR
)

SALE_HTML = (
    """<!DOCTYPE html>
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
"""
    % LEGAL_BASIS_CIVIL
)

SERVICE_HTML = (
    """<!DOCTYPE html>
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
"""
    % LEGAL_BASIS_CIVIL
)

CONSTRUCTION_HTML = (
    """<!DOCTYPE html>
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
"""
    % LEGAL_BASIS_CIVIL
)

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

LEGAL_BASIS_BIDDING = (
    "Luật Đấu thầu 22/2023/QH15 (Điều 60, 64, 70, 75) + "
    "Nghị định 24/2024/NĐ-CP + Thông tư 02/2023/TT-BXD"
)

BIDDING_CONSTRUCTION_HTML = (
    """<!DOCTYPE html>
<html lang="vi">
<head><meta charset="UTF-8"><title>Hợp đồng thi công xây dựng (đấu thầu)</title></head>
<style>
@page { size: A4; margin: 2.5cm; }
body { font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.6; }
.header { text-align: center; margin-bottom: 20px; }
.company-name { font-weight: bold; text-transform: uppercase; font-size: 13pt; }
.title { text-align: center; font-weight: bold; font-size: 14pt; margin: 25px 0; text-transform: uppercase; }
.section { margin: 15px 0; }
.signatures { margin-top: 50px; width: 100%%; }
.signatures td { text-align: center; width: 50%%; }
</style>
<body>
<div class="header">
  <div class="company-name">{{ company.name }}</div>
  <div style="font-size: 10pt">{{ company.address }} — MST: {{ company.tax_code }}</div>
</div>

<div class="title">
  CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM<br>
  Độc lập - Tự do - Hạnh phúc<br>
  ────────────────────<br><br>
  HỢP ĐỒNG THI CÔNG XÂY DỰNG<br>
  (Số: {{ contract.contract_no }})
</div>

<p style="text-align: right; font-style: italic; margin-bottom: 15px;">
  Hôm, ngày {{ today|date:"d" }} tháng {{ today|date:"m" }} năm {{ today|date:"Y" }}
</p>

<p><strong>BÊN A — CHỦ ĐẦU TƯ:</strong> {{ company.name }}</p>
<p>MST: {{ company.tax_code }} — Địa chỉ: {{ company.address }}</p>
<p>Đại diện: {{ company.legal_representative|default:"..." }} — Chức vụ: Giám đốc</p>

<p><strong>BÊN B — NHÀ THẦU:</strong> {{ contract.party_name|default:"..." }}</p>
<p>MST: {{ contract.party_tax_code|default:"..." }} — Địa chỉ: {{ contract.party_address|default:"..." }}</p>

<p>Hai bên đồng ý ký kết Hợp đồng thi công xây dựng với các điều khoản sau:</p>

<div class="section">
  <p><strong>Điều 1. Đối tượng hợp đồng</strong></p>
  <p>Thi công xây dựng công trình: <strong>{{ contract.description|default:"..." }}</strong></p>
  <p>Theo hồ sơ thiết kế đã được duyệt và hồ sơ mời thầu số {{ contract.contract_no }}.</p>
</div>

<div class="section">
  <p><strong>Điều 2. Giá trị hợp đồng</strong></p>
  <p>Tổng giá trị hợp đồng (chưa VAT): <strong>{{ contract.value }} {{ contract.currency_code }}</strong> VNĐ</p>
  <p>Loại hợp đồng: <strong>Hợp đồng trọn gói</strong> theo Điều 64 Luật Đấu thầu 2023.</p>
</div>

<div class="section">
  <p><strong>Điều 3. Thời gian thực hiện</strong></p>
  <p>Bắt đầu: {{ contract.start_date|date:"d/m/Y"|default:"..." }}</p>
  <p>Hoàn thành: {{ contract.end_date|date:"d/m/Y"|default:"..." }}</p>
</div>

<div class="section">
  <p><strong>Điều 4. Bảo lãnh thực hiện hợp đồng</strong></p>
  <p>Bên B nộp bảo lãnh thực hiện hợp đồng bằng <strong>10%%</strong> giá trị hợp đồng trước khi ký hợp đồng (Điều 70 Luật Đấu thầu 2023).</p>
</div>

<div class="section">
  <p><strong>Điều 5. Tạm ứng và Thanh toán</strong></p>
  <p>- Tạm ứng: <strong>≤ 30%%</strong> giá trị hợp đồng khi có bảo lãnh tạm ứng</p>
  <p>- Thanh toán: Theo tiến độ nghiệm thu các hạng mục (Điều 75 Luật Đấu thầu 2023)</p>
  <p>- Thanh toán cuối: Sau nghiệm thu bàn giao và nhận bảo hành</p>
</div>

<div class="section">
  <p><strong>Điều 6. Bảo hành</strong></p>
  <p>Thời gian bảo hành: <strong>12 tháng</strong> kể từ ngày nghiệm thu bàn giao.</p>
</div>

<div class="section">
  <p><strong>Điều 7. Trách nhiệm vi phạm hợp đồng</strong></p>
  <p>Phạt vi phạm: 8%% giá trị phần công trình vi phạm. Bồi thường thiệt hại thực tế.</p>
</div>

<div class="section">
  <p><strong>Điều 8. Giải quyết tranh chấp</strong></p>
  <p>Tranh chấp được giải quyết bằng thương lượng. Nếu không thỏa thuận được, đưa ra Tòa án/Trọng tài kinh tế có thẩm quyền.</p>
</div>

<div class="signatures">
<table>
<tr>
  <td><strong>BÊN A: CHỦ ĐẦU TƯ</strong><br>{{ company.name }}<br><br><br>(Ký, ghi rõ họ tên, đóng dấu)</td>
  <td><strong>BÊN B: NHÀ THẦU</strong><br>{{ contract.party_name|default:"..." }}<br><br><br>(Ký, ghi rõ họ tên, đóng dấu)</td>
</tr>
</table>
</div>

<p style="margin-top: 20px; font-size: 9pt; color: #666;">
  <em>Căn cứ pháp lý: %s</em>
</p>
</body></html>
"""
    % LEGAL_BASIS_BIDDING
)

LEGAL_BASIS_COMMERCE = (
    "Luật Thương mại 36/2005/QH11 (Điều 28, 29 — dịch vụ, đại lý, gia công); "
    "Bộ luật Dân sự 91/2015/QH13 (Điều 388-410, 528-547)."
)

LEGAL_BASIS_IT = (
    "Luật Công nghệ thông tin 67/2006/QH11 (sửa đổi 2025); "
    "Luật Thương mại 36/2005/QH11; Bộ luật Dân sự 91/2015/QH13; "
    "Luật Giao dịch điện tử 20/2023/QH15; Nghị định 13/2023/NĐ-CP (bảo vệ dữ liệu cá nhân)."
)

LEGAL_BASIS_LEASE = (
    "Bộ luật Dân sự 91/2015/QH13 (Điều 472-483 — hợp đồng thuê tài sản); "
    "Luật Nhà ở 65/2014/QH13 (sửa đổi 2020); Luật Kinh doanh bất động sản 66/2014/QH13; "
    "Nghị định 99/2015/NĐ-CP."
)

LEGAL_BASIS_LABOR_DISPATCH = (
    "Bộ luật Lao động 45/2019/QH14 (Điều 22, 23, 199-207 — cho thuê lại lao động); "
    "Nghị định 145/2020/NĐ-CP; Luật BHXH 41/2024/QH15."
)

# Shared CSS for full Vietnamese contract documents (WeasyPrint-friendly).
_CONTRACT_CSS = """
@page { size: A4; margin: 2.5cm; }
body { font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.6; }
.header { text-align: center; margin-bottom: 20px; }
.title { text-align: center; font-weight: bold; font-size: 14pt; margin: 25px 0; text-transform: uppercase; }
.section { margin: 15px 0; }
.signatures { margin-top: 50px; width: 100%%; }
.signatures td { text-align: center; width: 50%%; }
"""

IT_SERVICE_HTML = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>Hợp đồng cung cấp dịch vụ IT/phần mềm</title>
<style>%s</style></head>
<body>
<div class="header">
  <strong style="font-size:13pt">{{ company.name }}</strong><br>
  <span style="font-size:10pt">{{ company.address }} — MST: {{ company.tax_code }}</span>
</div>

<div class="title">
  CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM<br>
  Độc lập - Tự do - Hạnh phúc<br>
  ────────────────────<br><br>
  HỢP ĐỒNG CUNG CẤP DỊCH VỤ CÔNG NGHỆ THÔNG TIN<br>
  (Số: {{ contract_no }} — ngày {{ contract_date|date:"d/m/Y" }})
</div>

<p><strong>BÊN A — BÊN CUNG CẤP DỊCH VỤ:</strong> {{ company.name }}</p>
<p>MST: {{ company.tax_code }} — Địa chỉ: {{ company.address }}</p>
<p>Đại diện: {{ company.legal_representative|default:"..." }} — Chức vụ: Giám đốc</p>

<p><strong>BÊN B — BÊN SỬ DỤNG DỊCH VỤ:</strong> {{ contract.party_name|default:"..." }}</p>
<p>MST: {{ contract.party_tax_code|default:"..." }} — Địa chỉ: {{ contract.party_address|default:"..." }}</p>

<p>Hai bên thoả thuận ký kết Hợp đồng cung cấp dịch vụ CNTT/phần mềm với các điều khoản sau:</p>

<div class="section">
  <p><strong>Điều 1. Đối tượng hợp đồng</strong></p>
  <p>Cung cấp dịch vụ CNTT/phần mềm: <strong>{{ contract.description|default:"Phát triển, bảo trì hệ thống phần mềm theo đặc tả kỹ thuật đính kèm" }}</strong>.</p>
  <p>Phạm vi công việc: phân tích, thiết kế, lập trình, kiểm thử, triển khai và bảo trì theo phụ lục kỹ thuật.</p>
</div>

<div class="section">
  <p><strong>Điều 2. Giá trị hợp đồng</strong></p>
  <p>Tổng giá trị (chưa VAT): <strong>{{ value }} {{ currency_code }}</strong>.</p>
  <p>VAT: 10%% theo Luật GTGT. Hình thức thanh toán: chuyển khoản theo里程碑 nghiệm thu.</p>
</div>

<div class="section">
  <p><strong>Điều 3. Thời gian thực hiện</strong></p>
  <p>Bắt đầu: {{ start_date|date:"d/m/Y"|default:"..." }} — Hoàn thành: {{ end_date|date:"d/m/Y"|default:"..." }}.</p>
</div>

<div class="section">
  <p><strong>Điều 4. Quyền sở hữu trí tuệ</strong></p>
  <p>Mã nguồn, tài liệu thiết kế do Bên A trực tiếp sáng tạo thuộc sở hữu của Bên B sau khi thanh toán đầy đủ, trừ các thành phần mã nguồn mở/thư viện bên thứ ba giữ nguyên quyền của tác giả.</p>
</div>

<div class="section">
  <p><strong>Điều 5. Bảo mật và bảo vệ dữ liệu cá nhân</strong></p>
  <p>Hai bên cam kết bảo mật thông tin kinh doanh, dữ liệu khách hàng theo NĐ 13/2023/NĐ-CP và Luật Giao dịch điện tử 20/2023/QH15. Vi phạm bồi thường thiệt hại thực tế.</p>
</div>

<div class="section">
  <p><strong>Điều 6. Bảo hành</strong></p>
  <p>Bảo hành phần mềm <strong>12 tháng</strong> kể từ nghiệm thu: sửa lỗi (bug), bản vá an ninh miễn phí.</p>
</div>

<div class="section">
  <p><strong>Điều 7. Trách nhiệm vi phạm</strong></p>
  <p>Phạt vi phạm <strong>8%%</strong> giá trị phần vi phạm. Quá hạn <strong>15 ngày</strong> có quyền đơn phương chấm dứt hợp đồng theo Điều 428 BLDS 2015.</p>
</div>

<div class="section">
  <p><strong>Điều 8. Giải quyết tranh chấp</strong></p>
  <p>Thương lượng trước; nếu không thỏa thuận, đưa ra Trung tâm Trọng tài Quốc tế Việt Nam (VIAC) hoặc Tòa án có thẩm quyền.</p>
</div>

<div class="signatures">
<table>
<tr>
  <td><strong>BÊN A</strong><br>{{ company.name }}<br><br><br>(Ký, ghi rõ họ tên, đóng dấu)</td>
  <td><strong>BÊN B</strong><br>{{ contract.party_name|default:"..." }}<br><br><br>(Ký, ghi rõ họ tên, đóng dấu)</td>
</tr>
</table>
</div>

<p style="margin-top: 20px; font-size: 9pt; color: #666;"><em>Căn cứ pháp lý: %s</em></p>
</body></html>
""" % (_CONTRACT_CSS, LEGAL_BASIS_IT)

LEASE_HTML = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>Hợp đồng thuê tài sản/mặt bằng</title>
<style>%s</style></head>
<body>
<div class="header">
  <strong style="font-size:13pt">{{ company.name }}</strong><br>
  <span style="font-size:10pt">{{ company.address }} — MST: {{ company.tax_code }}</span>
</div>

<div class="title">
  CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM<br>
  Độc lập - Tự do - Hạnh phúc<br>
  ────────────────────<br><br>
  HỢP ĐỒNG THUÊ TÀI SẢN / MẶT BẰNG<br>
  (Số: {{ contract_no }} — ngày {{ contract_date|date:"d/m/Y" }})
</div>

<p><strong>BÊN A — BÊN CHO THUÊ:</strong> {{ contract.party_name|default:"..." }}</p>
<p>MST/CCCD: {{ contract.party_tax_code|default:"..." }} — Địa chỉ: {{ contract.party_address|default:"..." }}</p>

<p><strong>BÊN B — BÊN THUÊ:</strong> {{ company.name }}</p>
<p>MST: {{ company.tax_code }} — Địa chỉ: {{ company.address }}</p>
<p>Đại diện: {{ company.legal_representative|default:"..." }}</p>

<p>Hai bên thoả thuận ký kết hợp đồng thuê tài sản với các điều khoản:</p>

<div class="section">
  <p><strong>Điều 1. Đối tượng thuê</strong></p>
  <p>Tài sản/mặt bằng: <strong>{{ contract.description|default:"Mặt bằng kinh doanh, văn phòng" }}</strong>.</p>
  <p>Diện tích, vị trí, tình trạng tài sản theo biên bản bàn giao đính kèm.</p>
</div>

<div class="section">
  <p><strong>Điều 2. Giá thuê và phương thức thanh toán</strong></p>
  <p>Tiền thuê: <strong>{{ value }} {{ currency_code }}</strong>/tháng (chưa VAT nếu áp dụng).</p>
  <p>Thanh toán: chuyển khoản trước ngày <strong>05</strong> hàng tháng.</p>
</div>

<div class="section">
  <p><strong>Điều 3. Thời hạn thuê</strong></p>
  <p>Từ {{ start_date|date:"d/m/Y"|default:"..." }} đến {{ end_date|date:"d/m/Y"|default:"..." }}.</p>
</div>

<div class="section">
  <p><strong>Điều 4. Đặt cọc</strong></p>
  <p>Bên B đặt cọc <strong>1 tháng</strong> tiền thuê. Cọc hoàn trả khi hết hạn nếu không vi phạm.</p>
</div>

<div class="section">
  <p><strong>Điều 5. Quyền và nghĩa vụ</strong></p>
  <p>Bên A: giao tài sản đúng tình trạng, sửa chữa cấu trúc chủ yếu.</p>
  <p>Bên B: sử dụng đúng mục đích, thanh toán đúng hạn, giữ gìn tài sản, không chuyển nhượng nếu chưa đồng ý bằng văn bản.</p>
</div>

<div class="section">
  <p><strong>Điều 6. Trách nhiệm vi phạm</strong></p>
  <p>Quá hạn thanh toán <strong>15 ngày</strong>: phạt 0,05%%/ngày. Quá <strong>30 ngày</strong>: Bên A có quyền đơn phương chấm dứt (Điều 428 BLDS 2015).</p>
</div>

<div class="section">
  <p><strong>Điều 7. Giải quyết tranh chấp</strong></p>
  <p>Thương lượng trước; nếu không thỏa thuận, đưa ra Tòa án nhân dân có thẩm quyền nơi có tài sản.</p>
</div>

<div class="signatures">
<table>
<tr>
  <td><strong>BÊN A — CHO THUÊ</strong><br>{{ contract.party_name|default:"..." }}<br><br><br>(Ký, ghi rõ họ tên, đóng dấu)</td>
  <td><strong>BÊN B — THUÊ</strong><br>{{ company.name }}<br><br><br>(Ký, ghi rõ họ tên, đóng dấu)</td>
</tr>
</table>
</div>

<p style="margin-top: 20px; font-size: 9pt; color: #666;"><em>Căn cứ pháp lý: %s</em></p>
</body></html>
""" % (_CONTRACT_CSS, LEGAL_BASIS_LEASE)

AGENCY_HTML = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>Hợp đồng đại lý/phân phối</title>
<style>%s</style></head>
<body>
<div class="header">
  <strong style="font-size:13pt">{{ company.name }}</strong><br>
  <span style="font-size:10pt">{{ company.address }} — MST: {{ company.tax_code }}</span>
</div>

<div class="title">
  CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM<br>
  Độc lập - Tự do - Hạnh phúc<br>
  ────────────────────<br><br>
  HỢP ĐỒNG ĐẠI LÝ / PHÂN PHỐI<br>
  (Số: {{ contract_no }} — ngày {{ contract_date|date:"d/m/Y" }})
</div>

<p><strong>BÊN A — NGUYÊN ĐỐN:</strong> {{ company.name }}</p>
<p>MST: {{ company.tax_code }} — Địa chỉ: {{ company.address }}</p>
<p>Đại diện: {{ company.legal_representative|default:"..." }} — Chức vụ: Giám đốc</p>

<p><strong>BÊN B — ĐẠI LÝ / NHÀ PHÂN PHỐI:</strong> {{ contract.party_name|default:"..." }}</p>
<p>MST: {{ contract.party_tax_code|default:"..." }} — Địa chỉ: {{ contract.party_address|default:"..." }}</p>

<p>Hai bên thoả thuận ký kết Hợp đồng đại lý/phân phối theo các điều khoản:</p>

<div class="section">
  <p><strong>Điều 1. Đối tượng hợp đồng</strong></p>
  <p>Hàng hoá/phạm vi phân phối: <strong>{{ contract.description|default:"Hàng hoá của Bên A" }}</strong>.</p>
  <p>Loại đại lý: <strong>đại lý độc quyền / đại lý uỷ quyền</strong> theo Điều 29 Luật Thương mại 2005.</p>
</div>

<div class="section">
  <p><strong>Điều 2. Doanh số và giá trị hợp đồng</strong></p>
  <p>Giá trị hợp đồng (dự kiến/năm): <strong>{{ value }} {{ currency_code }}</strong>.</p>
  <p>Mục tiêu doanh số tối thiểu theo quý/năm quy định tại phụ lục.</p>
</div>

<div class="section">
  <p><strong>Điều 3. Thời hạn</strong></p>
  <p>Từ {{ start_date|date:"d/m/Y"|default:"..." }} đến {{ end_date|date:"d/m/Y"|default:"..." }}.</p>
</div>

<div class="section">
  <p><strong>Điều 4. Hoa hồng</strong></p>
  <p>Hoa hồng đại lý: <strong>5%%–15%%</strong> giá trị giao dịch thực tế theo chính sách riêng.</p>
</div>

<div class="section">
  <p><strong>Điều 5. Quyền và nghĩa vụ</strong></p>
  <p>Bên A: cung cấp hàng đúng chất lượng, số lượng, hỗ trợ marketing, đào tạo.</p>
  <p>Bên B: bảo vệ thương hiệu, không bán sản phẩm cạnh tranh cùng nhóm, báo cáo định kỳ.</p>
</div>

<div class="section">
  <p><strong>Điều 6. Bảo lãnh và độc quyền</strong></p>
  <p>Bên B được độc quyền khu vực quy định. Nếu vi phạm doanh số tối thiểu 2 quý liên tiếp, Bên A có quyền thu hồi độc quyền.</p>
</div>

<div class="section">
  <p><strong>Điều 7. Trách nhiệm vi phạm và giải quyết tranh chấp</strong></p>
  <p>Phạt vi phạm <strong>8%%</strong> giá trị vi phạm theo Điều 266 BLDS 2015. Tranh chấp giải quyết bằng thương lượng, trọng tài VIAC hoặc Tòa án kinh tế có thẩm quyền.</p>
</div>

<div class="signatures">
<table>
<tr>
  <td><strong>BÊN A — NGUYÊN ĐỐN</strong><br>{{ company.name }}<br><br><br>(Ký, ghi rõ họ tên, đóng dấu)</td>
  <td><strong>BÊN B — ĐẠI LÝ</strong><br>{{ contract.party_name|default:"..." }}<br><br><br>(Ký, ghi rõ họ tên, đóng dấu)</td>
</tr>
</table>
</div>

<p style="margin-top: 20px; font-size: 9pt; color: #666;"><em>Căn cứ pháp lý: %s</em></p>
</body></html>
""" % (_CONTRACT_CSS, LEGAL_BASIS_COMMERCE)

PROCESSING_HTML = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>Hợp đồng gia công/uỷ quyền</title>
<style>%s</style></head>
<body>
<div class="header">
  <strong style="font-size:13pt">{{ company.name }}</strong><br>
  <span style="font-size:10pt">{{ company.address }} — MST: {{ company.tax_code }}</span>
</div>

<div class="title">
  CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM<br>
  Độc lập - Tự do - Hạnh phúc<br>
  ────────────────────<br><br>
  HỢP ĐỒNG GIA CÔNG / UỶ QUYỀN<br>
  (Số: {{ contract_no }} — ngày {{ contract_date|date:"d/m/Y" }})
</div>

<p><strong>BÊN A — BÊN GIA CÔNG (THỤ UỶ QUYỀN):</strong> {{ company.name }}</p>
<p>MST: {{ company.tax_code }} — Địa chỉ: {{ company.address }}</p>
<p>Đại diện: {{ company.legal_representative|default:"..." }} — Chức vụ: Giám đốc</p>

<p><strong>BÊN B — BÊN ĐẶT GIA CÔNG (UỶ QUYỀN):</strong> {{ contract.party_name|default:"..." }}</p>
<p>MST: {{ contract.party_tax_code|default:"..." }} — Địa chỉ: {{ contract.party_address|default:"..." }}</p>

<p>Hai bên thoả thuận ký kết Hợp đồng gia công/uỷ quyền với các điều khoản:</p>

<div class="section">
  <p><strong>Điều 1. Đối tượng gia công</strong></p>
  <p>Sản phẩm/công việc: <strong>{{ contract.description|default:"Gia công hàng hoá theo bản vẽ, đặc tả đính kèm" }}</strong>.</p>
  <p>Quy cách, số lượng, chất lượng, yêu cầu kỹ thuật theo phụ lục.</p>
</div>

<div class="section">
  <p><strong>Điều 2. Giá trị và thanh toán</strong></p>
  <p>Giá trị hợp đồng: <strong>{{ value }} {{ currency_code }}</strong> (chưa VAT).</p>
  <p>Tạm ứng <strong>30%%</strong> khi ký. Thanh toán phần còn lại theo里程碑 nghiệm thu.</p>
</div>

<div class="section">
  <p><strong>Điều 3. Thời gian thực hiện</strong></p>
  <p>Từ {{ start_date|date:"d/m/Y"|default:"..." }} đến {{ end_date|date:"d/m/Y"|default:"..." }}.</p>
</div>

<div class="section">
  <p><strong>Điều 4. Nguyen vật liệu</strong></p>
  <p>Bên B cung cấp nguyên vật liệu chính; Bên A cung cấp lao động, máy móc, năng lực sản xuất.</p>
</div>

<div class="section">
  <p><strong>Điều 5. Nghiệm thu và bàn giao</strong></p>
  <p>Bên A bàn giao theo đúng tiến độ, chất lượng. Bên B nghiệm thu trong <strong>10 ngày</strong>, quá hạn mặc nhiên chấp nhận.</p>
</div>

<div class="section">
  <p><strong>Điều 6. Sở hữu và bảo mật</strong></p>
  <p>Sản phẩm, bản vẽ, đặc tả thuộc sở hữu trí tuệ của Bên B. Bên A bảo mật thông tin kỹ thuật, không sản xuất cho bên thứ ba.</p>
</div>

<div class="section">
  <p><strong>Điều 7. Trách nhiệm vi phạm và tranh chấp</strong></p>
  <p>Phạt vi phạm <strong>8%%</strong> giá trị phần vi phạm. Tranh chấp giải quyết bằng thương lượng, trọng tài VIAC hoặc Tòa án có thẩm quyền.</p>
</div>

<div class="signatures">
<table>
<tr>
  <td><strong>BÊN A — GIA CÔNG</strong><br>{{ company.name }}<br><br><br>(Ký, ghi rõ họ tên, đóng dấu)</td>
  <td><strong>BÊN B — ĐẶT GIA CÔNG</strong><br>{{ contract.party_name|default:"..." }}<br><br><br>(Ký, ghi rõ họ tên, đóng dấu)</td>
</tr>
</table>
</div>

<p style="margin-top: 20px; font-size: 9pt; color: #666;"><em>Căn cứ pháp lý: %s</em></p>
</body></html>
""" % (_CONTRACT_CSS, LEGAL_BASIS_COMMERCE)

LABOR_DISPATCH_HTML = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>Hợp đồng cho thuê lại lao động</title>
<style>%s</style></head>
<body>
<div class="header">
  <strong style="font-size:13pt">{{ company.name }}</strong><br>
  <span style="font-size:10pt">{{ company.address }} — MST: {{ company.tax_code }}</span>
</div>

<div class="title">
  CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM<br>
  Độc lập - Tự do - Hạnh phúc<br>
  ────────────────────<br><br>
  HỢP ĐỒNG CHO THUÊ LẠI LAO ĐỘNG<br>
  (Số: {{ contract_no }} — ngày {{ contract_date|date:"d/m/Y" }})
</div>

<p><strong>BÊN A — ĐƠN VỊ CHO THUÊ LẠI LAO ĐỘNG:</strong> {{ company.name }}</p>
<p>MST: {{ company.tax_code }} — Địa chỉ: {{ company.address }}</p>
<p>Đại diện: {{ company.legal_representative|default:"..." }} — Chức vụ: Giám đốc</p>
<p>Giấy phép hoạt động cho thuê lại lao động số: .../GP-BLĐTBXH (theo Điều 22-23 BLLĐ 2019).</p>

<p><strong>BÊN B — ĐƠN VỊ NHẬN LAO ĐỘNG:</strong> {{ contract.party_name|default:"..." }}</p>
<p>MST: {{ contract.party_tax_code|default:"..." }} — Địa chỉ: {{ contract.party_address|default:"..." }}</p>

<p>Hai bên thoả thuận ký kết Hợp đồng cho thuê lại lao động:</p>

<div class="section">
  <p><strong>Điều 1. Đối tượng hợp đồng</strong></p>
  <p>Cung ứng lao động cho vị trí: <strong>{{ contract.description|default:"Theo phụ lục danh sách người lao động" }}</strong>.</p>
  <p>Số lượng, vị trí, bằng cấp quy định tại phụ lục — tuân thủ Điều 23 BLLĐ 2019.</p>
</div>

<div class="section">
  <p><strong>Điều 2. Thời hạn</strong></p>
  <p>Từ {{ start_date|date:"d/m/Y"|default:"..." }} đến {{ end_date|date:"d/m/Y"|default:"..." }} (tối đa 06 tháng theo Điều 23(2) BLLĐ 2019).</p>
</div>

<div class="section">
  <p><strong>Điều 3. Giá trị hợp đồng và đơn giá</strong></p>
  <p>Tổng giá trị: <strong>{{ value }} {{ currency_code }}</strong>.</p>
  <p>Đơn giá/người/tháng bao gồm lương, BHXH, BHYT, BHTN, phí quản lý.</p>
</div>

<div class="section">
  <p><strong>Điều 4. Nghĩa vụ của Bên A</strong></p>
  <p>Chi trả lương, đóng BHXH/BHYT/BHTN đầy đủ theo Luật BHXH 41/2024/QH15; áp dụng chế độ lao động, an toàn vệ sinh; không thu phí của người lao động.</p>
</div>

<div class="section">
  <p><strong>Điều 5. Nghĩa vụ của Bên B</strong></p>
  <p>Bảo đảm điều kiện làm việc, an toàn lao động, không chuyển người lao động cho bên thứ ba, không tuyển dụng người lao động làm việc cho mình trong vòng 12 tháng sau khi hết HĐ (trừ thoả thuận).</p>
</div>

<div class="section">
  <p><strong>Điều 6. Chấm dứt hợp đồng</strong></p>
  <p>Theo Điều 25, 207 BLLĐ 2019. Người lao động được bảo lưu việc làm với Bên A sau khi hết hạn.</p>
</div>

<div class="section">
  <p><strong>Điều 7. Trách nhiệm vi phạm và tranh chấp</strong></p>
  <p>Phạt vi phạm <strong>8%%</strong> giá trị phần vi phạm. Tranh chấp lao động giải quyết theo BLLĐ 2019, Luật BHXH, hoặc Tòa án lao động có thẩm quyền.</p>
</div>

<div class="signatures">
<table>
<tr>
  <td><strong>BÊN A — CHO THUÊ LẠI</strong><br>{{ company.name }}<br><br><br>(Ký, ghi rõ họ tên, đóng dấu)</td>
  <td><strong>BÊN B — NHẬN LAO ĐỘNG</strong><br>{{ contract.party_name|default:"..." }}<br><br><br>(Ký, ghi rõ họ tên, đóng dấu)</td>
</tr>
</table>
</div>

<p style="margin-top: 20px; font-size: 9pt; color: #666;"><em>Căn cứ pháp lý: %s</em></p>
</body></html>
""" % (_CONTRACT_CSS, LEGAL_BASIS_LABOR_DISPATCH)

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
    {
        "code": "bidding_construction",
        "name": "Hợp đồng thi công xây dựng (đấu thầu)",
        "contract_type": "bidding_lump_sum",
        "template_html": BIDDING_CONSTRUCTION_HTML,
        "required_fields": [
            "project_name",
            "contractor_name",
            "contractor_tax_code",
            "value",
            "duration",
            "warranty_period",
            "performance_guarantee",
            "advance_payment",
        ],
        "legal_basis": LEGAL_BASIS_BIDDING,
    },
    {
        "code": "it_service",
        "name": "HĐ cung cấp dịch vụ IT/phần mềm",
        "contract_type": "it_service",
        "template_html": IT_SERVICE_HTML,
        "required_fields": [
            "company",
            "party_name",
            "value",
            "start_date",
            "end_date",
        ],
        "legal_basis": LEGAL_BASIS_IT,
    },
    {
        "code": "lease",
        "name": "HĐ thuê tài sản/mặt bằng",
        "contract_type": "lease",
        "template_html": LEASE_HTML,
        "required_fields": ["company", "party_name", "value", "start_date", "end_date"],
        "legal_basis": LEGAL_BASIS_LEASE,
    },
    {
        "code": "agency",
        "name": "HĐ đại lý/phân phối",
        "contract_type": "agency",
        "template_html": AGENCY_HTML,
        "required_fields": ["company", "party_name", "value", "start_date", "end_date"],
        "legal_basis": LEGAL_BASIS_COMMERCE,
    },
    {
        "code": "processing",
        "name": "HĐ gia công/uỷ quyền",
        "contract_type": "processing",
        "template_html": PROCESSING_HTML,
        "required_fields": ["company", "party_name", "value"],
        "legal_basis": LEGAL_BASIS_COMMERCE,
    },
    {
        "code": "labor_dispatch",
        "name": "HĐ cho thuê lại lao động",
        "contract_type": "labor_dispatch",
        "template_html": LABOR_DISPATCH_HTML,
        "required_fields": ["company", "party_name", "value", "start_date", "end_date"],
        "legal_basis": LEGAL_BASIS_LABOR_DISPATCH,
    },
]


class Command(BaseCommand):
    help = "Seed 13 pre-built contract templates with full Vietnamese legal text."

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
            self.style.SUCCESS(f"Seeded {len(TEMPLATES)} contract templates ({created_count} new).")
        )
