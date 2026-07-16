"""Static Vietnamese role-based note templates used by ``seed_pkm_templates``.

Each entry is a tuple of ``(role_code, title, markdown_body)``. The
``role_code`` is stored on ``KnowledgeNote.role_context`` so the
``PKMDashboardView`` and ``/api/v1/pkm/stats/`` endpoints can surface the
note to users whose ``UserCompanyRole.role__code`` matches.

The bodies are intentionally practical Vietnamese checklists / procedures
for each role. They are seeded as shared, pinned templates (owned by the
first superuser, attached to the first company) so that every user with
the matching role sees them in their dashboard's role-based suggestions.

Roles covered (matching the mission spec):
  * ``accountant``  — quy trình ghi sổ, đối chiếu công nợ
  * ``sales``       — quy trình xuất hóa đơn, theo dõi công nợ khách hàng
  * ``hr_officer``  — quy trình tính lương, kê khai BHXH
  * ``viewer``      — cách đọc báo cáo tài chính
"""

from __future__ import annotations

#: Prefix stored in the title to make template notes identifiable and idempotent.
TEMPLATE_TITLE_PREFIX = "[mẫu]"

#: Stable slug marker used to look up an existing template note by slug.
SLUG_MARKER = "tpl:"


ACCOUNTANT_GHI_SO_BODY = """\
# Quy trình ghi sổ kế toán cuối tháng

## 1. Tổng hợp chứng từ
- Thu thập đầy đủ hóa đơn, phiếu thu/chi, giấy báo Nợ/Có trong tháng.
- Kiểm tra tính hợp lệ, hợp lệ của hóa đơn điện tử (mã CQT, chữ ký số).
- Sắp xếp theo ngày và loại nghiệp vụ.

## 2. Định khoản và ghi sổ
- Định khoản từng chứng từ theo hệ thống tài khoản TT133/TT200.
- Ghi sổ nhật ký chung, sổ cái và sổ chi tiết các tài khoản.
- Kiểm tra đối ứng Nợ/Có, số tiền, ngày hạch toán.

## 3. Đối chiếu công nợ
- Đối chiếu số dư TK 131 (phải thu khách hàng) và TK 331 (phải trả người bán)
  với xác nhận công nợ của đối tác.
- Điều chỉnh chênh lệch (tiền hàng đang đi đường, chiết khấu, bù trừ).
- Lập bảng tổng hợp công nợ theo tuổi nợ để trích lập dự phòng.

## 4. Khóa sổ và lập báo cáo
- Khóa sổ kế toán, tính giá xuất kho, phân bổ chi phí.
- Lập Bảng cân đối số phát sinh, Bảng cân đối kế toán, Kết quả HĐKD.
- Nộp báo cáo tài chính theo quy định (TT133/TT200/TT58).
"""


ACCOUNTANT_CONG_NO_BODY = """\
# Cách đối chiếu công nợ với khách hàng và nhà cung cấp

## Đối chiếu công nợ phải thu (TK 131)
1. Xuất sổ chi tiết TK 131 theo từng khách hàng tại thời điểm đối chiếu.
2. Gửi bảng đối chiếu công nợ cho khách hàng (email hoặc thư từ).
3. Khách hàng xác nhận số dư hoặc ghi rõ khoản chênh lệch.
4. Điều tra các khoản chênh lệch: hóa đơn chưa gửi, hàng đang đi đường,
   thanh toán chưa ghi nhận, chiết khấu chưa phản ánh.
5. Hạch toán điều chỉnh sau khi thống nhất, lưu trữ xác nhận công nợ.

## Đối chiếu công nợ phải trả (TK 331)
1. Xuất sổ chi tiết TK 331 theo từng nhà cung cấp.
2. Đối chiếu với hóa đơn, hợp đồng và giấy báo Nợ của ngân hàng.
3. Xác nhận số dư với nhà cung cấp, điều chỉnh chênh lệch.

## Tần suất
- Đối chiếu định kỳ: hàng quý (tối thiểu) và cuối năm tài chính.
- Đối chiếu đột xuất khi có giao dịch lớn hoặc nghi ngờ sai sót.
"""


SALES_XUAT_HOA_DON_BODY = """\
# Quy trình xuất hóa đơn điện tử (HĐĐT)

## 1. Kiểm tra thông tin đơn hàng
- Xác nhận mã khách hàng, tên, mã số thuế, địa chỉ, email nhận HĐĐT.
- Kiểm tra mặt hàng, đơn giá, số lượng, thuế suất GTGT.

## 2. Lập hóa đơn điện tử
- Chọn loại hóa đơn (có mã CQT hoặc không có mã) theo quy định NĐ 254/2026.
- Ghi đầy đủ nội dung: hàng hóa/dịch vụ, đơn vị tính, số lượng, đơn giá,
  thành tiền, tiền thuế GTGT, tổng tiền thanh toán.
- Kiểm tra lại số tiền và đối ứng trước khi phát hành.

## 3. Phát hành và gửi
- Truyền hóa đơn cho CQT (loại có mã) và cấp mã.
- Gửi hóa đơn cho khách hàng qua email/hệ thống.
- Lưu trữ hóa đơn XML/PDF theo yêu cầu lưu trữ.

## 4. Xử lý sai sót
- Chưa gửi cho người mua: lập lại hóa đơn mới.
- Đã gửi: lập hóa đơn điều chỉnh (tăng/giảm) hoặc thay thế (theo TT 91/2026).
- Ghi rõ lý do điều chỉnh, số hóa đơn bị điều chỉnh.

## 5. Theo dõi và báo cáo
- Báo cáo tình hình sử dụng hóa đơn theo kỳ (theo TT 91/2026).
- Lưu ý hóa đơn hủy, hóa đơn lỗi phải báo cáo CQT.
"""


SALES_THEO_DOI_CONG_NO_BODY = """\
# Cách theo dõi công nợ khách hàng

## 1. Theo dõi trong hệ thống
- Cập nhật từng khoản thanh toán vào TK 131 của khách hàng tương ứng.
- Bám sát hạn thanh toán theo hợp đồng (ngày, tuần, tháng).

## 2. Báo cáo công nợ
- Xuất sổ cái TK 131 và sổ chi tiết theo từng khách hàng.
- Lập bảng tổng hợp công nợ theo tuổi nợ (0-30, 31-60, 61-90, > 90 ngày).
- Báo cáo cho quản lý các khoản quá hạn để có biện pháp thu hồi.

## 3. Đôn đốc thu hồi
- Nhắc nhở khách hàng qua email, điện thoại khi tới hạn.
- Gửi thư đòi nợ cho khoản quá hạn (lưu dấu vết).
- Báo cáo nợ xấu, nợ khó đòi để trích lập dự phòng.

## 4. Đối chiếu
- Đối chiếu công nợ định kỳ với khách hàng (xác nhận số dư).
- Điều chỉnh chênh lệch kịp thời, tránh thất thoát.
"""


HR_TINH_LUONG_BODY = """\
# Quy trình tính lương hàng tháng

## 1. Dữ liệu đầu vào
- Chấm công (ngày công, giờ làm thêm, nghỉ phép, nghỉ ốm).
- Hợp đồng lao động, thang bảng lương, phụ cấp.
- Thông tin giảm trừ gia cảnh (bản thân, người phụ thuộc).

## 2. Tính lương
- Lương thực tế = Lương cơ bản x (số ngày làm việc thực tế / tổng ngày).
- Cộng phụ cấp (ăn ca, điện thoại, xăng xe, trách nhiệm).
- Tính lương làm thêm giờ theo hệ số (ngày thường, cuối tuần, lễ).
- Trừ các khoản: BHXH (10,5%), BHYT (1,5%), BHTN (1%) người lao động đóng.

## 3. Tính thuế TNCN (theo NĐ 253/2026 + TT 87/2026)
- Thu nhập chịu thuế = Tổng thu nhập - Các khoản không chịu thuế
  - BHXH/BHYT/BHTN bắt buộc - Giảm trừ gia cảnh.
- Giảm trừ bản thân: 15.500.000 VND/tháng.
- Giảm trừ NPT: 6.200.000 VND/tháng (thu nhập NPT <= 3.000.000 VND/tháng).
- Áp biểu lũy tiến 5 bậc (5% - 35%).

## 4. Trích đóng BHXH (ND 161/2026)
- NSD lao động đóng: 21,5% quỹ lương (BHXH 17% + BHYT 3% + BHTN 1%
  + BHTNLĐ-BNN 0,5%).
- Trần đóng: 50.600.000 VND/tháng (20 x lương cơ sở).

## 5. Thanh toán và lưu trữ
- Lập bảng lương, gửi thông báo lương cho người lao động.
- Thanh toán qua ngân hàng hoặc tiền mặt (có chữ ký xác nhận).
- Lưu hồ sơ lương, chấm công theo quy định.
"""


HR_BHXH_BODY = """\
# Cách kê khai và nộp BHXH hàng tháng

## 1. Chuẩn bị dữ liệu
- Danh sách lao động tham gia BHXH, BHYT, BHTN.
- Biến động tháng (tăng/giảm lao động, thay đổi mức đóng).
- Bảng chấm công và quỹ tiền lương đóng BHXH.

## 2. Tính toán
- Tiền đóng NSDLĐ = 21,5% quỹ lương đóng BHXH (nếu >= 2 lao động).
- Tiền đóng người lao động = 10,5% mức đóng (BHXH 8% + BHYT 1,5% + BHTN 1%).
- Trần đóng: 50.600.000 VND/tháng (NĐ 161/2026, lương cơ sở 2.530.000 VND).

## 3. Lập hồ sơ khai
- Bảng chấm công, bảng thanh toán tiền lương.
- Danh sách tham gia BHXH (D02-TS) cho biến động tăng/giảm.
- Báo cáo tình hình sử dụng lao động (nếu có).

## 4. Nộp hồ sơ và tiền
- Nộp hồ sơ qua Cổng dịch vụ BHXH hoặc cơ quan BHXH trực tiếp.
- Chuyển khoản tiền đóng BHXH theo tháng (chậm nhất ngày cuối cùng tháng sau).
- Lưu biên lai nộp tiền, mã giao dịch.

## 5. Theo dõi và giải quyết chế độ
- Cập nhật sổ BHXH (điện tử) cho người lao động.
- Giải quyết chế độ ốm đau, thai sản, tai nạn lao động theo quy định.
"""


VIEWER_DOC_BAO_CAO_BODY = """\
# Cách đọc báo cáo tài chính (BCTC) cơ bản

## 1. Báo cáo tình hình tài chính (Bảng cân đối kế toán)
- Tổng tài sản = Nợ phải trả + Vốn chủ sở hữu.
- Tài sản ngắn hạn (tiền, phải thu, hàng tồn kho) cho biết thanh khoản.
- Tỷ lệ thanh toán hiện hành = Tài sản ngắn hạn / Nợ ngắn hạn (lý tưởng > 1.5).
- Nợ phải trả: chú ý khoản vay ngắn hạn, phải trả người bán.

## 2. Báo cáo kết quả hoạt động kinh doanh
- Doanh thu thuần = Doanh thu - Các khoản giảm trừ (chiết khấu, hàng bán bị trả lại).
- Lợi nhuận gộp = Doanh thu thuần - Giá vốn hàng bán.
- Lợi nhuận trước thuế = LNTT (thu nhập khác) - Chi phí khác.
- Biên lợi nhuận ròng = LNST / Doanh thu thuần (càng cao càng tốt).

## 3. Báo cáo lưu chuyển tiền tệ (LCTT)
- Dòng tiền từ HĐKD, HĐ đầu tư, HĐ tài chính.
- Dòng tiền HĐKD dương là tín hiệu tích cực (tự tạo tiền).
- Dòng tiền âm kéo dài cần xem xét khả năng thanh toán.

## 4. Một số tỷ lệ quan trọng
- Tỷ suất lợi nhuận trên vốn chủ sở hữu (ROE) = LNST / Vốn chủ sở hữu.
- Vòng quay hàng tồn kho = Giá vốn / Tồn kho bình quân.
- Hiệu quả sử dụng tài sản (ROA) = LNST / Tổng tài sản.

## 5. Lưu ý khi đọc
- So sánh nhiều kỳ để thấy xu hướng.
- Đọc kèm thuyết minh BCTC để hiểu chính sách kế toán.
- Chú ý các sự kiện sau ngày khóa sổ, các khoản ngoại bảng.
"""


#: Registry of role-based note templates to seed.
#: Each entry: (role_code, slug, title, body_markdown).
ROLE_TEMPLATES: list[tuple[str, str, str, str]] = [
    (
        "accountant",
        "accountant-ghi-so-cuoi-thang",
        "Quy trình ghi sổ kế toán cuối tháng",
        ACCOUNTANT_GHI_SO_BODY,
    ),
    (
        "accountant",
        "accountant-doichieu-cong-no",
        "Cách đối chiếu công nợ với khách hàng và nhà cung cấp",
        ACCOUNTANT_CONG_NO_BODY,
    ),
    (
        "sales",
        "sales-xuat-hoa-don",
        "Quy trình xuất hóa đơn điện tử (HĐĐT)",
        SALES_XUAT_HOA_DON_BODY,
    ),
    (
        "sales",
        "sales-theo-doi-cong-no",
        "Cách theo dõi công nợ khách hàng",
        SALES_THEO_DOI_CONG_NO_BODY,
    ),
    (
        "hr_officer",
        "hr-tinh-luong",
        "Quy trình tính lương hàng tháng",
        HR_TINH_LUONG_BODY,
    ),
    (
        "hr_officer",
        "hr-khai-bao-bxhh",
        "Cách kê khai và nộp BHXH hàng tháng",
        HR_BHXH_BODY,
    ),
    (
        "viewer",
        "viewer-doc-bao-cao-tai-chinh",
        "Cách đọc báo cáo tài chính cơ bản",
        VIEWER_DOC_BAO_CAO_BODY,
    ),
]


__all__ = [
    "ROLE_TEMPLATES",
    "TEMPLATE_TITLE_PREFIX",
    "SLUG_MARKER",
]
