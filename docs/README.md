# Bộ tài liệu tái hiện phần mềm SIS Accounting Online

> **Mục tiêu**: Cung cấp bộ đặc tả đầy đủ để tái hiện phần mềm kế toán SIS Accounting Online (pkm.erpsme.vn) bằng stack **Django + django-ninja + HTMX + Alpine.js + MariaDB**.

## Đối tượng sử dụng

- **Kỹ sư phần mềm / Architect**: đọc phần kiến trúc và mô hình dữ liệu
- **Backend developer**: đọc phần module và API
- **Frontend developer**: đọc phần UI/UX và mẫu giao diện
- **Kế toán / Domain expert**: đọc phần module và tuân thủ kế toán
- **Project manager**: đọc phần tổng quan và kế hoạch triển khai

## Thông tin hệ thống gốc

| Hạng mục | Giá trị |
|---|---|
| **URL** | https://pkm.erpsme.vn/ |
| **Tên sản phẩm** | SIS Accounting Online |
| **Đơn vị phát triển** | Công ty Cổ phần S.I.S Việt Nam (sis.vn) |
| **Đơn vị bản quyền demo** | Công ty CP Công nghệ PKM |
| **Chế độ kế toán áp dụng** | **TT133/2016** (doanh nghiệp nhỏ và vừa) |
| **Hình thức ghi sổ hỗ trợ** | Nhật ký chung (S03a-DN/DNN), Chứng từ ghi sổ (S02a-DN/DNN) |
| **Mã công ty** | SISMACOL2026_TT133_PKM |
| **Phiên bản dữ liệu** | Năm tài chính 2026 |

## Cấu trúc tài liệu

```
docs/
├── README.md                                  ← file này (mục lục)
├── 01-tong-quan/
│   ├── 01-system-overview.md                  Tổng quan hệ thống
│   ├── 02-phan-tich-nguoi-dung.md             Phân tích người dùng & vai trò
│   └── 03-quy-trinh-suu-tam.md                Quy trình thu thập thông tin
├── 02-yeu-cau/
│   ├── 01-functional-requirements.md          Yêu cầu chức năng
│   └── 02-non-functional-requirements.md      Yêu cầu phi chức năng
├── 03-phan-tich-module/
│   ├── 00-tong-quan-module.md                 Tổng quan 13 module
│   ├── 01-ke-toan-tong-hop.md                 Kế toán tổng hợp
│   ├── 02-von-bang-tien.md                    Vốn bằng tiền
│   ├── 03-ban-hang.md                         Bán hàng
│   ├── 04-mua-hang.md                         Mua hàng
│   ├── 05-ton-kho.md                          Tồn kho
│   ├── 06-tai-san-co-dinh.md                  Tài sản cố định
│   ├── 07-cong-cu-dung-cu.md                  Công cụ dụng cụ
│   ├── 08-chi-phi-gia-thanh.md                Chi phí, giá thành
│   ├── 09-quan-ly-nhan-su.md                  Quản lý nhân sự
│   ├── 10-tien-luong-cham-cong.md             Tiền lương, chấm công
│   ├── 11-bao-cao-tai-chinh.md                Báo cáo tài chính
│   ├── 12-bao-cao-thue.md                     Báo cáo thuế
│   └── 13-he-thong.md                         Hệ thống (admin)
├── 04-mo-hinh-du-lieu/
│   ├── 01-erd-tong-quan.md                    Sơ đồ thực thể quan hệ tổng quát
│   ├── 02-schema-khoi-chinh.md                Lược đồ khối chính (master)
│   ├── 03-schema-chung-tu.md                  Lược đồ chứng từ & bút toán
│   ├── 04-schema-danh-muc.md                  Lược đồ danh mục từ điển
│   └── 05-bang-tinh-gia-ton-kho.md            Bảng tính giá tồn kho
├── 05-kien-truc-ky-thuat/
│   ├── 01-kien-truc-tong-the.md               Kiến trúc tổng thể
│   ├── 02-django-apps.md                      Phân chia Django apps
│   ├── 03-django-ninja-api.md                 Lớp API django-ninja
│   ├── 04-htmx-alpine-frontend.md             Frontend HTMX + Alpine.js
│   ├── 05-mariadb-design.md                   Thiết kế MariaDB
│   └── 06-deployment.md                       Triển khai & vận hành
├── 06-tai-lieu-api/
│   ├── 01-api-conventions.md                  Quy ước REST API
│   ├── 02-endpoints-master-data.md            API danh mục
│   ├── 03-endpoints-vouchers.md               API chứng từ
│   └── 04-endpoints-reports.md                API báo cáo
├── 07-mau-giao-dien/
│   ├── 01-layout-overview.md                  Layout tổng thể
│   ├── 02-grid-master-detail.md               Mẫu lưới master-detail
│   ├── 03-form-chung-tu.md                    Form chứng từ
│   ├── 04-form-danh-muc.md                    Form danh mục
│   ├── 05-multi-ui-architecture.md            **Đa giao diện song song (multi-UI)** — Layout packs
│   └── 06-ux-variants-architecture.md         **Đa luồng thao tác (UX variants)** — Plugin registry cho Interaction styles + Workflows
├── 08-tuan-thu-ke-toan/
│   ├── 01-cac-che-do-ke-toan-vn.md            Các chế độ kế toán VN
│   ├── 02-tt133-2016.md                       Chi tiết TT133
│   ├── 03-tt200-2014.md                       Chi tiết TT200
│   ├── 04-tt78-2021-va-tt32-2025.md           Hóa đơn điện tử
│   ├── 05-tt80-2021-to-khai-gtgt.md           Tờ khai thuế GTGT
│   ├── 06-luat-ke-toan-2015.md                Luật Kế toán 2015
│   └── 07-bao-cao-tai-chinh-bctc.md           Mẫu BCTC theo TT133/TT200
└── 09-ke-hoach-trien-khai/
    ├── 01-roadmap.md                          Lộ trình phát triển
    ├── 02-tech-stack.md                       Stack công nghệ chi tiết
    ├── 03-folder-structure.md                 Cấu trúc thư mục code
    └── 04-testing-strategy.md                 Chiến lược kiểm thử
```

## Nguyen lý tái hiện

Bộ tài liệu này áp dụng các nguyên tắc sau:

1. **Phân tích từ ngoài vào trong (top-down)**: bắt đầu từ tổng quan nghiệp vụ, đi sâu đến schema và API.
2. **Tuân thủ chế độ kế toán**: toàn bộ chứng từ, sổ sách, BCTC bám sát **TT133/2016/TT-BTC** (mặc định) và có mở rộng tùy chọn **TT200/2014/TT-BTC**.
3. **Domain-Driven Design**: chia Django apps theo bounded context nghiệp vụ chứ không theo table.
4. **Single Source of Truth**: mỗi nghiệp vụ kế toán chỉ có một entity nắm giữ真相 (journal entry line là nguồn dữ liệu kế toán; các báo cáo là projection).
5. **Tái sử dụng sample forms**: các sample (S03a-DN, S02a-DN, B01-DN...) trong TT133/TT200 được tham chiếu rõ ràng.

## Kết luận

Bộ tài liệu này cung cấp nền tảng để:
- **Build from scratch**: lập team và xây dựng phần mềm từ đầu theo đặc tả
- **Audit so sánh**: đối chiếu phần mềm kế toán khác có cùng phạm vi
- **Migrate**: chuyển dữ liệu từ SIS hoặc phần mềm khác sang hệ thống mới

Mọi câu hỏi/kết luận trong tài liệu đều dựa trên dữ liệu quan sát được bằng cách đăng nhập hệ thống với tài khoản demo (SIS/123) và đối chiếu với các văn bản pháp luật kế toán Việt Nam đính kèm.

---

**Ngày tạo**: 2026-06-16  
**Phiên bản**: 1.0  
**Tác giả**: Claude Code (tài liệu được tổng hợp từ quá trình khám phá thực tế)
