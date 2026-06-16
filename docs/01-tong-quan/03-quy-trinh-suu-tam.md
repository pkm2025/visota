# 03. Quy trình thu thập thông tin

> Tóm tắt phương pháp đã dùng để khám phá hệ thống SIS gốc và nguồn tài liệu.

## 1. Phương pháp thu thập

### 1.1. Khám phá hệ thống gốc

Hệ thống SIS Accounting Online (https://pkm.erpsme.vn/) đã được khám phá bằng:

- **Đăng nhập demo** với tài khoản SIS/123
- **Browser automation** qua Playwright MCP tools
- **DOM inspection** để lấy metadata và column headers
- **Tree navigation expansion** để map toàn bộ menu
- **Switch perspective** qua 11 company views để khám phá đầy đủ module

### 1.2. Nguồn thông tin bổ sung

- **WebSearch** cho văn bản pháp lý Việt Nam
- **Documentation chính thức** của:
  - Bộ Tài chính (mof.gov.vn)
  - Tổng cục Thuế (gdt.gov.vn)
  - Thư viện pháp luật (thuvienphapluat.vn)

## 2. Giới hạn quan sát

### 2.1. Những gì đã quan sát được

✅ Toàn bộ cấu trúc điều hướng (navigation tree)
✅ 11 góc nhìn nghiệp vụ (Tổng hợp, Vốn bằng tiền, ...)
✅ Cấu trúc màn hình list (grid columns, filter, actions)
✅ Form entry cho một số nghiệp vụ (Phiếu kế toán)
✅ Chart of accounts thực tế (127 TK, TT133)
✅ URL patterns (`/glctpk1/wg_ct_01`, `/dmtk/wg_dm_01`, ...)

### 2.2. Những gì chưa quan sát được

❌ Detail screens của tất cả nghiệp vụ (chỉ quan sát Phiếu KT)
❌ Report rendering actual (chỉ thấy menu)
❌ HĐĐT XML schema thực tế
❌ Tích hợp BKAV API thực
❌ Permission system chi tiết
❌ Workflow phê duyệt (nếu có)
❌ Audit log format

### 2.3. Giả định

Để tài liệu hoàn chỉnh, đã đưa ra các giả định hợp lý dựa trên:
- Quy định pháp luật VN (TT133, TT200, TT78, TT80)
- Best practices của phần mềm kế toán (MISA, FAST, Bravo)
- Sample forms chính thức của Bộ Tài chính
- Domain knowledge kế toán VN thông dụng

Các giả định được đánh dấu rõ trong từng tài liệu module.

## 3. Cách validate tài liệu khi tái hiện

### 3.1. Demo với khách hàng

1. Build MVP cho Phase 1 (Foundation + GL)
2. Setup công ty demo (PKM data)
3. Cho kế toán dùng thử 1-2 tuần
4. Thu feedback, so sánh với SIS
5. Điều chỉnh spec cho Phase 2+

### 3.2. So sánh feature checklist

Dùng [01-functional-requirements.md](../02-yeu-cau/01-functional-requirements.md) làm checklist để verify:
- Mỗi FR có trong SIS không?
- Nếu có → implement theo SIS
- Nếu không → đánh giá cần không (có thể là value-add)

### 3.3. Pilot migration

- Lấy dữ liệu thật từ 1-2 công ty dùng SIS
- Import vào PMKetoan
- Verify: số dư, BCTC, sổ sách phải khớp 100%
- Fix bất kỳ sai lệch nào

## 4. Các câu hỏi cần làm rõ với chủ đầu tư

Trước khi bắt đầu Phase 1, cần trả lời:

1. **Scope**: Có cần migrate dữ liệu từ SIS hoặc phần mềm khác?
2. **Users target**: SME (TT133) hay cả DN lớn (TT200)?
3. **Hosting**: Cloud (which?), on-premise, hybrid?
4. **Pricing model**: SaaS subscription, license, hybrid?
5. **Mobile**: Có cần mobile app không, khi nào?
6. **Integrations**: BKAV only, hay cả nhà cung cấp khác?
7. **Multi-currency**: Có cần hỗ trợ chi tiết (theo ngày, loại tỷ giá)?
8. **Customization**: Cho phép user thêm TK, field, report tùy chỉnh?
9. **Audit**: Có cần audit log export để đối phó kiểm tra thuế không?
10. **Backup**: RPO/RTO cụ thể?

## 5. Tài liệu tham khảo chính

### 5.0. Multi-UI & UX variants

- [07-mau-giao-dien/05-multi-ui-architecture.md](../07-mau-giao-dien/05-multi-ui-architecture.md) — Layout packs + Multi-tenant branding
- [07-mau-giao-dien/06-ux-variants-architecture.md](../07-mau-giao-dien/06-ux-variants-architecture.md) — Interaction styles + Workflows + Plugin registry

### 5.1. Văn bản pháp lý

| Văn bản | Link |
|---------|------|
| Luật Kế toán 88/2015/QH13 | https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Luat-Ke-toan-88-2015-QH13-296441.aspx |
| TT133/2016/TT-BTC | https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Thong-tu-133-2016-TT-BTC-huong-dan-che-do-ke-toan-doanh-nghiep-nho-va-vua-284997.aspx |
| TT200/2014/TT-BTC | https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Thong-tu-200-2014-TT-BTC-huong-dan-Che-do-ke-toan-Doanh-nghiep-263599.aspx |
| TT80/2021/TT-BTC | https://thuvienphapluat.vn/van-ban/Thue-Phi-Le-Phi/Thong-tu-80-2021-TT-BTC-ban-hanh-mau-to-khai-thue-502620.aspx |
| TT78/2021/TT-BTC | https://thuvienphapluat.vn/van-ban/Thue-Phi-Le-Phi/Thong-tu-78-2021-TT-BTC-huong-dan-Luat-Quan-ly-thue-Nghi-dinh-123-2020-ND-CP-hoa-don-chung-tu-477966.aspx |
| TT32/2025/TT-BTC | https://thuvienphapluat.vn/van-ban/Thue-Phi-Le-Phi/Thong-tu-32-2025-TT-BTC-huong-dan-thuc-hien-Luat-Quan-ly-thue-ve-hoa-don-chung-tu-659105.aspx |
| ND 80/2021/NĐ-CP | https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Nghi-dinh-80-2021-ND-CP-quan-dinh-tieu-chi-xac-dinh-doanh-nghiep-nho-vua-485068.aspx |

### 5.2. Hệ thống tài khoản

- [Hệ thống TK theo TT133](https://www.meinvoice.vn/tin-tuc/16900/bang-he-thong-tai-khoan-theo-thong-tu-133-day-du/)
- [Hệ thống TK theo TT200](https://docs.kreston.vn/vbpl/ke-toan/che-do-ke-toan/che-do-ke-toan-doanh-nghiep/tt-200-2014-tt-btc/phu-luc-1/)

### 5.3. Phần mềm kế toán VN tham khảo

- MISA AMIS: https://amis.misa.vn/
- FAST Accounting: https://www.fast.com.vn/
- Bravo: https://www.bravo.vn/
- SIS (gốc): https://www.sis.vn/

### 5.4. Hóa đơn điện tử

- Cổng thông tin HĐĐT TCT: https://hoadondientu.gdt.gov.vn/
- BKAV eInvoice: https://hoadondientu.bkav.com/
- Viettel eInvoice: https://hoadondientu.viettel.vn/

### 5.5. Tech stack documentation

- Django: https://docs.djangoproject.com/
- django-ninja: https://django-ninja.dev/
- HTMX: https://htmx.org/
- Alpine.js: https://alpinejs.dev/
- MariaDB: https://mariadb.com/kb/en/documentation/
- Tabulator: https://tabulator.info/

## 6. Kết luận

Bộ tài liệu này cung cấp nền tảng vững chắc để tái hiện phần mềm SIS Accounting Online bằng stack Django + django-ninja + HTMX + Alpine.js + MariaDB.

**Điểm mạnh**:
- Phân tích đầy đủ 13 module nghiệp vụ
- Đặc tả schema chi tiết cho MariaDB
- Architecture rõ ràng, modular
- Tuân thủ chế độ kế toán VN
- Documentation format dễ đọc, có code samples

**Điểm cần bổ sung khi triển khai**:
- Verify các giả định với stakeholder
- Build MVP để validate UX
- Migration strategy từ hệ thống cũ
- Training materials cho user

Mọi góp ý/câu hỏi xin liên hệ qua kênh phát hành.

---

**Trở về**: [README.md](../README.md)
