"""Load TT133/2016 chart of accounts for a company."""
from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Company
from apps.master_data.models import AccountType, ChartOfAccounts


ACCOUNT_TYPES = [
    (1, 'Tài sản ngắn hạn', 'debit', 'asset'),
    (2, 'Tài sản dài hạn', 'debit', 'asset'),
    (3, 'Nợ phải trả', 'credit', 'liability'),
    (4, 'Vốn chủ sở hữu', 'credit', 'equity'),
    (5, 'Doanh thu', 'credit', 'revenue'),
    (6, 'Chi phí sản xuất kinh doanh', 'debit', 'expense'),
    (7, 'Thu nhập khác', 'credit', 'other_income'),
    (8, 'Chi phí khác', 'debit', 'other_expense'),
    (9, 'Xác định kết quả kinh doanh', 'credit', 'off_balance'),
    (0, 'Tài khoản ngoài bảng', 'debit', 'off_balance'),
]


# (code, name, parent_code, level, type_code, is_posting, is_gl, allows_object, allows_cost_center)
ACCOUNTS = [
    # Type 1 - Tài sản ngắn hạn
    ('111', 'Tiền mặt', None, 1, 1, False, True, False, False),
    ('1111', 'Tiền Việt Nam', '111', 2, 1, True, False, False, False),
    ('1112', 'Ngoại tệ', '111', 2, 1, True, False, False, False),
    ('1113', 'Vàng bạc, đá quý', '111', 2, 1, True, False, False, False),

    ('112', 'Tiền gửi ngân hàng', None, 1, 1, False, True, False, False),
    ('1121', 'Tiền Việt Nam', '112', 2, 1, True, False, False, False),
    ('1122', 'Ngoại tệ', '112', 2, 1, True, False, False, False),
    ('1123', 'Vàng bạc, đá quý', '112', 2, 1, True, False, False, False),

    ('113', 'Tiền đang chuyển', None, 1, 1, True, True, False, False),

    ('121', 'Đầu tư tài chính ngắn hạn', None, 1, 1, False, True, False, False),
    ('1211', 'Chứng khoán kinh doanh', '121', 2, 1, True, False, False, False),
    ('1212', 'Đầu tư nắm giữ đến ngày đáo hạn', '121', 2, 1, True, False, False, False),
    ('1213', 'Đầu tư khác', '121', 2, 1, True, False, False, False),

    ('128', 'Đầu tư nắm giữ đến ngày đáo hạn', None, 1, 1, False, True, False, False),
    ('1281', 'Tiền gửi có kỳ hạn', '128', 2, 1, True, False, False, False),
    ('1288', 'Đầu tư khác nắm giữ đến ngày đáo hạn', '128', 2, 1, True, False, False, False),

    ('129', 'Dự phòng giảm giá chứng khoán kinh doanh', None, 1, 1, True, True, False, False),

    ('131', 'Phải thu khách hàng', None, 1, 1, False, True, True, False),
    ('133', 'Thuế GTGT được khấu trừ', None, 1, 1, False, True, False, False),
    ('1331', 'Thuế GTGT được khấu trừ của HHDV', '133', 2, 1, True, False, False, False),
    ('1332', 'Thuế GTGT được khấu trừ của TSCĐ', '133', 2, 1, True, False, False, False),

    ('136', 'Phải thu nội bộ', None, 1, 1, False, True, True, False),
    ('1361', 'Vốn kinh doanh ở đơn vị trực thuộc', '136', 2, 1, True, False, True, False),
    ('1368', 'Phải thu nội bộ khác', '136', 2, 1, True, False, True, False),

    ('138', 'Phải thu khác', None, 1, 1, False, True, False, False),
    ('1381', 'Tài sản thiếu chờ xử lý', '138', 2, 1, True, False, False, False),
    ('1386', 'Phải thu cổ đông', '138', 2, 1, True, False, False, False),
    ('1388', 'Phải thu khác', '138', 2, 1, True, False, False, False),

    ('141', 'Tạm ứng', None, 1, 1, True, True, True, False),

    ('152', 'Nguyên liệu, vật liệu', None, 1, 1, False, True, False, False),
    ('153', 'Công cụ, dụng cụ', None, 1, 1, False, True, False, False),
    ('154', 'Chi phí SXKD dở dang', None, 1, 1, False, True, False, False),
    ('155', 'Thành phẩm', None, 1, 1, False, True, False, False),
    ('156', 'Hàng hóa', None, 1, 1, False, True, False, False),
    ('1561', 'Giá mua hàng hóa', '156', 2, 1, True, False, False, False),
    ('1562', 'Chi phí thu mua hàng hóa', '156', 2, 1, True, False, False, False),

    ('159', 'Dự phòng giảm giá HTK', None, 1, 1, True, True, False, False),

    # Type 2 - Tài sản dài hạn
    ('211', 'Tài sản cố định hữu hình', None, 1, 2, False, True, False, False),
    ('2111', 'Nhà cửa, vật kiến trúc', '211', 2, 2, True, False, False, False),
    ('2112', 'Máy móc, thiết bị', '211', 2, 2, True, False, False, False),
    ('2113', 'Phương tiện vận tải, truyền dẫn', '211', 2, 2, True, False, False, False),
    ('2114', 'Thiết bị, dụng cụ quản lý', '211', 2, 2, True, False, False, False),
    ('2115', 'Cây lâu năm, súc vật', '211', 2, 2, True, False, False, False),
    ('2118', 'TSCĐ khác', '211', 2, 2, True, False, False, False),

    ('212', 'TSCĐ thuê tài chính', None, 1, 2, False, True, False, False),

    ('213', 'TSCĐ vô hình', None, 1, 2, False, True, False, False),
    ('2131', 'Quyền sử dụng đất', '213', 2, 2, True, False, False, False),
    ('2132', 'Quyền phát hành', '213', 2, 2, True, False, False, False),
    ('2133', 'Bản quyền, bằng sáng chế', '213', 2, 2, True, False, False, False),
    ('2134', 'Phần mềm máy tính', '213', 2, 2, True, False, False, False),
    ('2136', 'Bản quyền phần mềm', '213', 2, 2, True, False, False, False),
    ('2138', 'TSCĐ vô hình khác', '213', 2, 2, True, False, False, False),

    ('214', 'Hao mòn TSCĐ', None, 1, 2, False, True, False, False),
    ('2141', 'Hao mòn TSCĐ hữu hình', '214', 2, 2, True, False, False, False),
    ('2142', 'Hao mòn TSCĐ thuê TC', '214', 2, 2, True, False, False, False),
    ('2143', 'Hao mòn TSCĐ vô hình', '214', 2, 2, True, False, False, False),

    ('217', 'Tài sản cố định khác', None, 1, 2, True, True, False, False),

    ('221', 'Bất động sản đầu tư', None, 1, 2, False, True, False, False),
    ('2211', 'Chi phí BĐS đầu tư hình thành', '221', 2, 2, True, False, False, False),
    ('2212', 'BĐS đầu tư hoàn thành', '221', 2, 2, True, False, False, False),

    ('228', 'Đầu tư dài hạn khác', None, 1, 2, False, True, False, False),
    ('229', 'Dự phòng tổn thất đầu tư TC dài hạn', None, 1, 2, True, True, False, False),

    ('241', 'Chi phí xây dựng cơ bản dở dang', None, 1, 2, False, True, False, False),
    ('242', 'Chi phí trả trước', None, 1, 2, True, True, False, False),

    # Type 3 - Nợ phải trả
    ('311', 'Vay và nợ thuê tài chính ngắn hạn', None, 1, 3, False, True, False, False),
    ('331', 'Phải trả cho người bán', None, 1, 3, False, True, True, False),
    ('333', 'Thuế và các khoản phải nộp nhà nước', None, 1, 3, False, True, False, False),
    ('3331', 'Thuế GTGT', '333', 2, 3, False, True, False, False),
    ('33311', 'Thuế GTGT đầu ra', '3331', 3, 3, True, False, False, False),
    ('33312', 'Thuế GTGT hàng nhập khẩu', '3331', 3, 3, True, False, False, False),
    ('3332', 'Thuế tiêu thụ đặc biệt', '333', 2, 3, True, False, False, False),
    ('3333', 'Thuế TNDN', '333', 2, 3, True, False, False, False),
    ('3334', 'Thuế nhà thầu', '333', 2, 3, True, False, False, False),
    ('3335', 'Thuế môn bài', '333', 2, 3, True, False, False, False),
    ('3336', 'Thuế TNCN', '333', 2, 3, True, False, False, False),
    ('33381', 'Phí, lệ phí', '333', 2, 3, True, False, False, False),
    ('3339', 'Khoản phải nộp khác', '333', 2, 3, True, False, False, False),

    ('334', 'Phải trả người lao động', None, 1, 3, False, True, False, False),
    ('335', 'Chi phí phải trả', None, 1, 3, False, True, False, False),
    ('336', 'Phải trả nội bộ', None, 1, 3, False, True, True, False),
    ('338', 'Phải trả, phải nộp khác', None, 1, 3, False, True, False, False),
    ('3381', 'Tài sản thừa chờ xử lý', '338', 2, 3, True, False, False, False),
    ('3382', 'Kinh phí công đoàn', '338', 2, 3, True, False, False, False),
    ('3383', 'Bảo hiểm xã hội', '338', 2, 3, True, False, False, False),
    ('3384', 'Bảo hiểm y tế', '338', 2, 3, True, False, False, False),
    ('3386', 'Bảo hiểm thất nghiệp', '338', 2, 3, True, False, False, False),
    ('3389', 'Quỹ khen thưởng, phúc lợi', '338', 2, 3, True, False, False, False),

    ('341', 'Vay và nợ thuê TC dài hạn', None, 1, 3, False, True, False, False),

    # Type 4 - Vốn CSH
    ('411', 'Vốn đầu tư của chủ sở hữu', None, 1, 4, False, True, False, False),
    ('4111', 'Vốn góp của chủ sở hữu', '411', 2, 4, True, False, False, False),
    ('4112', 'Thunk vốn góp', '411', 2, 4, True, False, False, False),
    ('4118', 'Vốn khác của chủ sở hữu', '411', 2, 4, True, False, False, False),

    ('412', 'Chênh lệch đánh giá lại tài sản', None, 1, 4, True, True, False, False),
    ('413', 'Chênh lệch tỷ giá hối đoái', None, 1, 4, True, True, False, False),
    ('418', 'Quỹ khen thưởng, phúc lợi', None, 1, 4, True, True, False, False),
    ('421', 'Lợi nhuận chưa phân phối', None, 1, 4, False, True, False, False),

    # Type 5 - Doanh thu
    ('511', 'Doanh thu', None, 1, 5, False, True, False, False),
    ('5111', 'Doanh thu bán hàng', '511', 2, 5, True, False, False, False),
    ('5112', 'Doanh thu cung cấp dịch vụ', '511', 2, 5, True, False, False, False),
    ('5113', 'Doanh thu trợ cấp, tài trợ', '511', 2, 5, True, False, False, False),
    ('5117', 'Doanh thu kinh doanh BĐS đầu tư', '511', 2, 5, True, False, False, False),
    ('5118', 'Doanh thu khác', '511', 2, 5, True, False, False, False),

    ('515', 'Doanh thu hoạt động tài chính', None, 1, 5, False, True, False, False),

    # Type 6 - Chi phí
    ('621', 'Chi phí NVL trực tiếp', None, 1, 6, False, True, False, False),
    ('622', 'Chi phí nhân công trực tiếp', None, 1, 6, False, True, False, False),
    ('627', 'Chi phí sản xuất chung', None, 1, 6, False, True, False, False),
    ('632', 'Giá vốn hàng bán', None, 1, 6, False, True, False, False),
    ('635', 'Chi phí tài chính', None, 1, 6, False, True, False, False),
    ('641', 'Chi phí bán hàng', None, 1, 6, False, True, False, False),
    ('642', 'Chi phí QLDN', None, 1, 6, False, True, False, False),

    # Type 7 - Thu nhập khác
    ('711', 'Thu nhập khác', None, 1, 7, False, True, False, False),

    # Type 8 - Chi phí khác
    ('811', 'Chi phí khác', None, 1, 8, False, True, False, False),
    ('821', 'Chi phí thuế TNDN', None, 1, 8, False, True, False, False),
    ('8211', 'Chi phí thuế TNDN hiện hành', '821', 2, 8, True, False, False, False),
    ('8212', 'Chi phí thuế TNDN hoãn lại', '821', 2, 8, True, False, False, False),

    # Type 9 - XĐKQ
    ('911', 'Xác định kết quả kinh doanh', None, 1, 9, False, True, False, False),
]


class Command(BaseCommand):
    help = 'Load TT133/2016 chart of accounts for a company'

    def add_arguments(self, parser):
        parser.add_argument('--company-code', required=True, help='Company code')

    def handle(self, *args, **options):
        code = options['company_code']
        try:
            company = Company.objects.get(code=code)
        except Company.DoesNotExist:
            raise CommandError(f'Company not found: {code}')

        # 1. Create account types
        types_created = 0
        type_map = {}
        for t_code, name, bal, cat in ACCOUNT_TYPES:
            at, created = AccountType.objects.update_or_create(
                code=t_code,
                defaults={'name': name, 'balance_type': bal, 'category': cat},
            )
            type_map[t_code] = at
            if created:
                types_created += 1

        # 2. Create accounts
        accounts_created = 0
        for acc_code, name, parent, level, t_code, is_posting, is_gl, allows_obj, allows_cc in ACCOUNTS:
            _, created = ChartOfAccounts.objects.update_or_create(
                company=company, account_code=acc_code,
                defaults={
                    'account_name': name,
                    'parent_account_code': parent or '',
                    'account_level': level,
                    'account_type': type_map[t_code],
                    'is_posting_account': is_posting,
                    'is_general_ledger_account': is_gl,
                    'allows_object_code': allows_obj,
                    'allows_cost_center': allows_cc,
                },
            )
            if created:
                accounts_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Loaded TT133: {types_created} types, {accounts_created} accounts for {code}'
        ))
