"""Seed initial Knowledge Base articles for the in-app help center.

Creates BlogArticle entries with tags='help,<category>' for key topics
that startup founders need guidance on.

Usage:
    python manage.py seed_help_articles
"""
# ruff: noqa: E501

from django.core.management.base import BaseCommand

from apps.public.models import BlogArticle

HELP_ARTICLES = [
    {
        "title": "Hóa đơn điện tử (HĐĐT) là gì? Cấu hình lần đầu",
        "slug": "huong-dan-hoadt-cau-hinh",
        "excerpt": "Tìm hiểu về hóa đơn điện tử theo ND 254/2026 và cách cấu hình provider.",
        "tags": "help,hdtd,hoadon",
        "content": """<h2>Hóa đơn điện tử là gì?</h2>
<p>Hóa đơn điện tử (HĐĐT) là hóa đơn được tạo lập, xử lý trên máy tính và truyền qua mạng cho người mua và cơ quan thuế. Theo <strong>ND 254/2026/ND-CP</strong> (hướng dẫn bởi <strong>TT 91/2026/TT-BTC</strong> và <strong>Luật QLT 108/2025/QH15</strong>), doanh nghiệp phải sử dụng HĐĐT thay vì hóa đơn giấy.</p>

<h3>Các bước cấu hình</h3>
<ol>
<li>Vào <strong>Cài đặt → Cấu hình HĐĐT</strong></li>
<li>Chọn nhà cung cấp (MISA, VNPT, Viettel...)</li>
<li>Nhập mã số thuế, mẫu số (pattern), ký hiệu (serial)</li>
<li>Lưu và test kết nối</li>
</ol>

<h3>Phát hành HĐĐT</h3>
<ol>
<li>Tạo hóa đơn bán hàng (<strong>Bán hàng → Hóa đơn → Thêm</strong>)</li>
<li>Nhập khách hàng, hàng hóa, thuế suất</li>
<li>Bấm <strong>Phát hành HĐĐT</strong> để gửi lên provider</li>
<li>Tải PDF hóa đơn đã ký số</li>
</ol>

<div class="alert alert-info">
<strong>Lưu ý:</strong> HĐĐT đã phát hành không thể xóa, chỉ điều chỉnh/hủy.
</div>""",
    },
    {
        "title": "Hướng dẫn hạch toán theo TT133/2016",
        "slug": "huong-dan-hach-toan-tt133",
        "excerpt": "Cơ chế kế toán doanh nghiệp nhỏ và vừa theo Thông tư 133.",
        "tags": "help,ke-toan,tt133",
        "content": """<h2>Chế độ kế toán TT133/2016</h2>
<p>Thông tư 133/2016/TT-BTC áp dụng cho doanh nghiệp nhỏ và vừa. Hệ thống tài khoản (HTTK) gồm khoảng <strong>116 tài khoản</strong> ở 3 cấp.</p>

<h3>Nhóm tài khoản chính</h3>
<ul>
<li><strong>1</strong> — Tài sản (tiền, công nợ, hàng tồn kho, TSCĐ)</li>
<li><strong>2</strong> — Nợ phải trả (NCC, vay, thuế)</li>
<li><strong>3</strong> — Vốn chủ sở hữu</li>
<li><strong>4</strong> — Doanh thu (chưa dùng trong TT133)</li>
<li><strong>5</strong> — Doanh thu</li>
<li><strong>6</strong> — Chi phí</li>
<li><strong>7</strong> — Thu nhập khác</li>
<li><strong>8,9</strong> — Xác định kết quả</li>
</ul>

<h3>Bút toán cơ bản</h3>
<table class="table table-bordered">
<tr><th>Nghiệp vụ</th><th>Nợ</th><th>Có</th></tr>
<tr><td>Bán hàng</td><td>131</td><td>5111</td></tr>
<tr><td>Thu tiền KH</td><td>111/112</td><td>131</td></tr>
<tr><td>Mua hàng</td><td>156/152</td><td>331</td></tr>
<tr><td>Trả lương</td><td>622/334</td><td>111/112</td></tr>
</table>""",
    },
    {
        "title": "Nộp thuế GTGT — hướng dẫn từng bước",
        "slug": "huong-dan-nop-thue-gtgt",
        "excerpt": "Cách kê khai và nộp thuế giá trị gia tăng (VAT) hàng tháng.",
        "tags": "help,thue,vat,gtgt",
        "content": """<h2>Kê khai thuế GTGT hàng tháng</h2>
<p>Thuế GTGT (VAT) nộp hàng tháng, hạn nộp là <strong>ngày 20 tháng sau</strong>.</p>

<h3>Các bước</h3>
<ol>
<li>Vào <strong>Báo cáo → Tờ khai thuế GTGT</strong></li>
<li>Chọn kỳ (tháng/năm)</li>
<li>Hệ thống tự tính số thuế đầu ra (TK 33311 Có) và đầu vào (TK 1331 Nợ)</li>
<li>Kiểm tra số thuế phải nộp/thôi thu</li>
<li>Xuất XML nộp lên门户 Thuế điện tử</li>
</ol>

<h3>Công thức</h3>
<p><strong>Thuế GTGT phải nộp = Thuế đầu ra − Thuế đầu vào</strong></p>
<ul>
<li>Thuế đầu ra = Doanh thu × Thuế suất (thường 10%)</li>
<li>Thuế đầu vào = Tổng VAT trên hóa đơn mua vào</li>
</ul>

<div class="alert alert-warning">
<strong>Lưu ý:</strong> Nếu thuế đầu vào &gt; đầu ra → được khấu trừ/kéo sang kỳ sau.
Nộp muộn = phạt 0.03%/ngày.
</div>""",
    },
    {
        "title": "Thuê nhân viên đầu tiên — thủ tục gì?",
        "slug": "huong-dan-thue-nhan-vien-dau-tien",
        "excerpt": "Quy trình tuyển dụng, ký HĐLĐ, đăng ký BHXH cho nhân viên mới.",
        "tags": "help,nhan-su,hr",
        "content": """<h2>Quy trình thuê nhân viên đầu tiên</h2>

<h3>Bước 1: Tạo hồ sơ nhân viên</h3>
<ol>
<li>Vào <strong>Nhân sự → Danh sách NV → Thêm</strong></li>
<li>Nhập thông tin: Họ tên, CCCD, ngày sinh, địa chỉ</li>
<li>Chọn phòng ban, chức vụ</li>
</ol>

<h3>Bước 2: Ký hợp đồng lao động</h3>
<ol>
<li>Vào <strong>Hợp đồng → Tạo nhanh → Hợp đồng với nhân viên</strong></li>
<li>Chọn loại HĐLĐ (thử việc / xác định thời hạn / không xác định)</li>
<li>Nhập lương, phụ cấp, ngày bắt đầu</li>
<li>Điền thông tin và in hợp đồng</li>
</ol>

<h3>Bước 3: Đăng ký BHXH</h3>
<ol>
<li>Tạo bảng chấm công đầu tháng</li>
<li>Đăng ký BHXH tại cổng thông tin BHXH hoặc qua đại lý</li>
<li>Tỷ lệ đóng: <strong>BH bắt buộc 32.5%</strong> (DN 21.5% + NLĐ 11%)</li>
</ol>

<h3>Bước 4: Tính lương</h3>
<ol>
<li>Chấm công cuối tháng (<strong>Nhân sự → Chấm công</strong>)</li>
<li>Chạy tính lương (<strong>Tiền lương → Chạy kỳ</strong>)</li>
<li>Hệ thống tự tính: Lương gross − BHXH − PIT = Net</li>
</ol>""",
    },
    {
        "title": "Chốt sổ cuối tháng — checklist",
        "slug": "huong-dan-chot-so-cuoi-thang",
        "excerpt": "Danh sách công việc cần hoàn tất trước khi chốt kỳ kế toán.",
        "tags": "help,ke-toan,chot-so",
        "content": """<h2>Checklist chốt sổ cuối tháng</h2>

<h3>1. Hoàn tất chứng từ</h3>
<ul>
<li>Nhập tất cả phiếu thu/chi trong tháng</li>
<li>Ghi nhận hóa đơn mua/bán</li>
<li>Kiểm tra công nợ KH/NCC</li>
</ul>

<h3>2. Kiểm tra cân đối</h3>
<ul>
<li>Chạy <strong>Sổ cái</strong> — kiểm tra từng TK</li>
<li>Chạy <strong>Cân đối số phát sinh</strong> — Nợ = Có?</li>
<li>Đối chiếu số dư tiền mặt/tiền gửi</li>
</ul>

<h3>3. Phân bổ/Khấu hao</h3>
<ul>
<li>Tính khấu hao TSCĐ cuối tháng</li>
<li>Phân bổ chi phí trả trước (TK 242)</li>
<li>Phân bổ CCDC (TK 142)</li>
</ul>

<h3>4. Kê khai thuế</h3>
<ul>
<li>Tờ khai thuế GTGT (T01 → T15 tháng sau, nộp trước 20)</li>
<li>Tạm tính thuế TNDN (quý)</li>
</ul>

<h3>5. Chốt kỳ</h3>
<ul>
<li>Vào <strong>Kế toán → Chốt sổ kỳ</strong></li>
<li>Hệ thống khóa kỳ, chuyển số dư sang tháng sau</li>
</ul>""",
    },
]


class Command(BaseCommand):
    help = "Seed Knowledge Base help articles."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for article_data in HELP_ARTICLES:
            obj, created = BlogArticle.objects.update_or_create(
                slug=article_data["slug"],
                defaults={
                    "title": article_data["title"],
                    "excerpt": article_data["excerpt"],
                    "content": article_data["content"],
                    "tags": article_data["tags"],
                    "status": BlogArticle.Status.PUBLISHED,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Help articles: {created_count} created, {updated_count} updated "
                f"(total {len(HELP_ARTICLES)})."
            )
        )
