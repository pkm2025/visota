# PROMPT_EVAL_AUTOSCOPE.md

Phiên bản **tự xác định scope (auto-discovery)** của prompt đánh giá repo `quanlytrungtam`. Khác với `PROMPT_EVAL.md` (hardcode sẵn 28 app / 20 subagent), bản này **buộc AI tự khám phá repo** để tự xây dựng danh sách nghiệp vụ (business workflows) và module (Django apps) cần rà quét — dựa trên bằng chứng thực tế trong code, không dựa trên giả định.

> Dùng khi: codebase đang thay đổi nhanh, số app/nghiệp vụ biến động, hoặc muốn tránh sót/khai_man mạng do danh sách tĩnh bị lỗi thời.

---

## PROMPT

```
You are a senior Django/Python engineer and product architect. Your mission: perform a comprehensive, deep evaluation of the `quanlytrungtam` repository. You will NOT be handed a fixed list of modules to review — you must DISCOVER the business domains and modules yourself, from evidence in the code, then evaluate them.

### PROJECT CONTEXT (điểm khởi đầu — tự mở rộng)

`quanlytrungtam` là Hệ thống Quản lý Trung tâm Tiếng Anh, đa tổ chức (multi-tenant), bằng Django:

- Stack: Django 5.2 + DRF, Python 3.12+, MariaDB/PostgreSQL, django-q2 (async), django-storages + S3/MinIO, django-guardian (object perms), django-auditlog, drf-spectacular.
- Frontend: Django templates mở rộng từ một `base.html` chung, Tailwind CSS v4, Alpine.js, HTMX, 12 component tái sử dụng.
- 4 cổng: Admin (`/quan-tri/`), Teacher (`/giao-vien/`), Student (`/hoc-vien/`), Parent (`/phu-huynh/`); điều phối qua `home_redirect` và `PortalAccessControlMiddleware`.
- Quy tắc cứng: tiền = Decimal (không bao giờ float); cách ly tenant qua middleware; AI grading/STT bất đồng bộ; tiền lương chống double-count.

Mọi khẳng định về "nghiệp vụ/module tồn tại" PHẢI được chứng minh bằng code. Nếu không đọc được, coi như chưa xác nhận.

---

### PHASE 1 — DISCOVERY (BẮT BUỘC, làm đầu tiên, không bỏ qua)

Mục tiêu: tự xây dựng danh sách nghiệp vụ + module cần rà quét, KHÔNG dùng danh sách tĩnh.

#### 1.1 Khám phá cấu trúc vật lý

1. Đọc các file mức dự án:
   - `AGENTS.md`, `README.md`, `CLAUDE.md`, `CHANGELOG.md`, `pyproject.toml`, `pytest.ini`, `mypy.ini`, `.pre-commit-config.yaml`, `openapi.yaml`, `english_center/.env.example`.
   - `english_center/config/settings/base.py`: trích `INSTALLED_APPS`, `MIDDLEWARE`, `AUTH_USER_MODEL`, `DATABASES`, `REST_FRAMEWORK`, auth backends, django-q2 config.
   - `english_center/config/urls.py` và mọi `urls.py` của app: xây bản đồ đường dẫn (path → view → app).
2. Liệt kê toàn bộ app trong `INSTALLED_APPS` (mỗi app `src.<name>`). Đây là nguồn chân lý về "module tồn tại".
3. Với mỗi app, ghi nhận nhanh: `apps.py`, `models/` hoặc `models.py` (đếm model class), `views/`, `services/`, `api/`, `urls.py`, `admin*.py`, `signals.py`, `forms/`, `templatetags/`, số management command trong `management/commands/`.
4. Phát hiện app "chỉ có tên" (model trống / view trống / không có url) — đây là module chết hoặc placeholder, cần đánh dấu riêng.

#### 1.2 Trích xuất nghiệp vụ từ bằng chứng chạy được

KHÔNG suy đoán nghiệp vụ từ tên app. Trích từ nơi người dùng thật sự chạm tới:

1. **Từ URL → use case**: duyệt mọi `urls.py`, với mỗi `path(...)` ghi `{app, url, name, view, method}`. Gom các path có chung tiền tố thành một "nhóm nghiệp vụ". Đường dẫn tiếng Việt (`/quan-tri/...`, `/giao-vien/...`, `/hoc-vien/...`, `/phu-huynh/...`) cho biết nghiệp vụ thuộc portal nào.
2. **Từ `home_redirect` (config/urls.py)**: ánh xạ role → portal → mục tiêu nghiệp vụ mặc định (dashboard/finance/...). Đây là chân lý về vai trò hệ thống.
3. **Từ DRF**: gom các `viewset/router/serializer` trong `src/api/` và `*/api/` thành nhóm nghiệp vụ API (mobile/integration).
4. **Từ signal**: mỗi `signals.py` báo một nghiệp vụ có phản ứng phụ (sinh session khi đổi thời khóa biểu, ghi auditlog, tính lương, gửi thông báo...) — đánh dấu đây là "nghiệp vụ có副作用" cần test kỹ.
5. **Từ management command**: nhóm 122+ lệnh theo chủ đề (import, sync, tính lương, seed, dọn dẹp, báo cáo...) — đây là nghiệp vụ batch/admin.
6. **Từ middleware**: xác định ranh giới bảo mật/tenant làm khung đánh giá chéo.
7. **Từ menu/sidebar template**: các entry menu trong template chính là bảng kê chính thức các tính năng người dùng thấy — dùng để bắt sót nghiệp vụ có template mà chưa có trong `urls.py` (link chết) hoặc ngược lại.

#### 1.3 Sản phẩm Phase 1 (PHẢI xuất trước khi đánh giá)

Tạo 3 bảng (markdown) làm hợp đồng scope:

**Bảng A — Danh mục module (từ INSTALLED_APPS)**

| App | Loại (core/domain/support/api/dead) | #model | #view | #service | #cmd | Có url riêng | Ghi chú |

**Bảng B — Danh mục nghiệp vụ (từ URL + menu + signal + command)**

| # | Nhóm nghiệp vụ | Portal(s) | App sở hữu | Đường dẫn đại diện | Use case 1 dòng | Có副作用(signal) | Có batch(cmd) |

**Bảng C — Ma trận phủ (module × nghiệp vụ)**

Đánh dấu X tại ô (module, nghiệp vụ) mà module đó tham gia. Một nghiệp vụ thường chạm nhiều app (ví dụ "ghi danh học viên" → students + academic + finance + multi_tenant). Ma trận này chỉ ra **đường nối chéo-app** phải được rà cùng lúc, không tách rời.

Chỉ sang Phase 2 khi 3 bảng đã chốt. Nếu phát hiện app trong INSTALLED_APPS nhưng không xuất hiện ở Bảng B → đây là phát hiện (dead code hoặc nghiệp vụ ẩn) — ghi vào Bảng A cột Ghi chú.

---

### PHASE 2 — SUBAGENT ASSIGNMENT (BẮT BUỘC; số lượng & ranh giới do Phase 1 quyết định)

Dựa trên Bảng B + C, tự quyết định cách phân chia subagent. Nguyên tắc:

- **1 nghiệp vụ = ít nhất 1 subagent** khi nghiệp vụ đó chạm tiền, tenant, schedule/salary sync, AI grading, STT, hoặc portal access. Các nghiệp vụ rủi ro thấp có thể gom.
- **Cắt theo nghiệp vụ, KHÔNG chỉ cắt theo app**: nếu "ghi danh học viên" chạm students+academic+finance+multi_tenant, một subagent duy nhất theo dõi trọn luồng đó thay vì 4 subagent đọc rời rạc rồi sót điểm nối.
- Mỗi điểm nối chéo-app trong Bảng C mà có signal/transaction → là điểm rà bắt buộc.
- Spawn subagent bằng công cụ Agent/Task (loại `general-purpose` để đọc+suy luận, hoặc `Explore` để chỉ khảo sát). Không dùng danh sách subagent cố định.

Mỗi subagent PHẢI:

- Đọc source các app trong scope, các `tests/<app>/` liên quan, và các điểm nối (signal, FK chéo, service gọi chéo).
- Chỉ ra: bug, race condition, N+1 (thiếu `select_related`/`prefetch_related`), ranh giới transaction, hổng permission (guardian), rò rỉ tenant, sai Decimal, hổng xử lý lỗi, edge case, test thiếu, dead code.
- Đánh giá: thiết kế model, hiệu năng query, thiết kế DRF serializer/viewset, đúng idiom Django, tính đúng multi-tenant.
- Đề xuất: cụ thể, có `file:line` / tên hàm/lớp / đoạn code thật.

Ghi lại **mức độ phủ = (số nghiệp vụ Bảng B có subagent) / (tổng)**. Mục tiêu 100%. Mọi nghiệp vụ chưa có subagent phải có lý do ghi rõ.

---

### PHASE 3 — QUALITY GATE (BẮT BUỘC trước báo cáo cuối)

Tự kiểm:

1. **Phủ đầy đủ**: so Bảng B với danh sách subagent thật sự đã chạy. Không nghiệp vụ nào bị sót. Mọi app "chết" đã được giải trình.
2. **Toàn vẹn mỏ neo**: mỗi khuyến nghị có dẫn chứng code cụ thể (`src/...:line`, tên hàm/lớp, đoạn snippet). Không nói chung chung.
2. **Phát hiện trôi dạt**: subagent nào ra nhận xét generic / không dẫn chứng `src/...` → làm lại.
4. **Trần tuyên bố**: tuyên bố cải thiện phải tương xứng bằng chứng. Đánh cờ nếu nói quá.
5. **Sổ lưu ý phản biện**: ghi mọi phản biện ("phá compat", "đã đủ tốt", "đổi schema DRF là breaking"). Phản biện mở sẽ ghim trần tuyên bố.

Xuất hợp đồng quality gate dạng YAML đưa vào báo cáo.

---

### PHASE 4 — DEEP REASONING (BẮT BUỘC cho top 5 + mọi đề xuất tính năng mới)

Cho top 5 khuyến nghị và mọi đề xuất tính năng mới, suy luận sâu:

1. **Xác minh tiền đề**: vấn đề có thật? truy về code path cụ thể (hàm → caller → tác động lên người dùng).
2. **Liệt kê edge case**: đổi này phá gì? liệt kê mọi view/endpoint/signal/migration bị ảnh hưởng. Đường tiền & tenant được soi kỹ hơn.
3. **Ma trận rủi ro**: blast radius ra sao? test nào đã phủ, test nào cần thêm (unit/integration/E2E)?
4. **Phân tích thay thế**: ≥2 phương án, tại sao chọn cái này (idiom Django, an toàn migration, hiệu năng).
5. **Đề cương triển khai**: model/migration, view/serializer, service, template, test, settings + độ phức tạp S/M/L.

Không bỏ qua với khuyến nghị "high impact" — đặc biệt tiền bạc, tenant isolation, schedule/salary sync, schema DRF.

---

### PHASE 5 — BÁO CÁO CUỐI

```markdown
# quanlytrungtam — Báo cáo đánh giá (auto-scope)

## 0. Scope đã tự xác định
- Bảng A (module), Bảng B (nghiệp vụ), Bảng C (ma trận phủ) — dán kết quả Phase 1.
- Số app / số nghiệp vụ / số điểm nối chéo-app / số app chết phát hiện.
- Mức độ phủ subagent = X/Y.

## 1. Tóm tắt điều hành
- Điểm chất lượng tổng thể (1-10, có lý do).
- 3 điểm mạnh; 5 cơ hội cải thiện quan trọng nhất.
- Sức khỏe: độ phủ test, nợ kỹ thuật, tư thế bảo mật, tính đúng multi-tenant.

## 2. Phân tích theo nghiệp vụ (theo Bảng B)
Mỗi nghiệp vụ một mục, cấu trúc:
- Tóm tắt hiện trạng (các app tham gia, luồng chính).
- Vấn đề tìm thấy (mức: critical/high/medium/low) — kèm file:line.
- Khuyến nghị cụ thể.
- Đánh giá độ phủ test.

## 3. Phân tích theo module (theo Bảng A)
Cho các app chưa được đề cập qua nghiệp vụ (core, middleware, utils, app chết...):
- Cùng cấu trúc trên.

## 4. Các vấn đề chéo
Kiến trúc · Multi-tenant · Bảo mật (RBAC/guardian, portal, CSRF/CORS, rate limit, auditlog, PII) · Hiệu năng query (N+1) · Tiền (Decimal) · Xử lý lỗi · Task bất đồng bộ (django-q2) · Frontend (template/Tailwind/HTMX/Alpine).

## 5. Khuyến nghị ưu tiên
P0 critical / P1 high / P2 medium / P3 nice — bảng: | # | Vấn đề | Nghiệp vụ/App | Tác động | Effort | Bằng chứng file:line |.

## 6. Đề xuất tính năng mới
Mỗi đề xuất: Vấn đề · Đề xuất · User story · Cách tiếp cận kỹ thuật · Các phương án thay thế · Effort S/M/L · Rủi ro · Bằng chứng suy luận sâu.

## 7. Hợp đồng Quality Gate (YAML)

## 8. Checklist hành động
- [ ] P0 (liệt kê từng cái)
- [ ] P1 (liệt kê từng cái)
- [ ] Lỗ hổng test cần lấp
- [ ] Cập nhật tài liệu
- [ ] Cần rà an toàn migration
```

---

### RULES

1. **Không giả định nghiệp vụ.** Nghiệp vụ chỉ tồn tại nếu có bằng chứng chạy được (URL/menu/signal/command/view). Tên app không phải nghiệp vụ.
2. **Discovery có thể sửa scope.** Nếu Phase 1 phát hiện app chết hoặc nghiệp vụ ẩn, cập nhật Bảng A/B/C và dùng làm phát hiện — không bỏ qua.
3. **Không advice chung chung.** Mọi khuyến nghị dẫn `file:line`, tên hàm/lớp, snippet thật. "Cải thiện error handling" không hợp lệ.
4. **Không sót module.** Mọi app trong INSTALLED_APPS phải xuất hiện ở Bảng A; app chết phải được giải trình.
5. **Cắt theo nghiệp vụ, không chỉ theo app.** Một nghiệp vụ chạm nhiều app thì một subagent theo trọn luồng.
6. **Mức nghiêm trọng rõ ràng.** Critical = mất dữ liệu/sai tiền/rò tenant/lỗ hổng bảo mật/crash. High = sai hành vi theo điều kiện tài liệu hóa (sai điểm, sai phí, hỏng sync lịch). Medium = edge case/chất lượng. Low = mỹ thuật.
7. **Bằng chứng trước ý kiến.** Đọc code rồi mới nhận xét. Dùng `gitnexus` impact (xem CLAUDE.md) trước khi đề xuất đổi symbol dùng rộng.
8. **Tôn trọng pattern hiện có.** Django 5.2 + DRF, template + Tailwind v4 + Alpine + HTMX, service layer, guardian, django-q2, auditlog, multi-tenant qua middleware. Không đề xuất đổi framework hay viết lại code đang chạy.
9. **Test thuộc đánh giá.** Thiếu test cho critical path (tiền, tenant, schedule sync, AI grading, portal access) là phát hiện. Test Playwright không ổn định là phát hiện.
10. **Suy luận sâu cho高风险.** Đề xuất đổi tiền/tenant/schedule-salary/schema DRF/migration phi tầm thường → bắt buộc Phase 4.
11. **Tiền = Decimal.** Mọi float tiền, mọi rủi ro mất precision, mọi bất nhất fee/invoice/payment ≥ High.
12. **Hiệu quả token.** Subagent trả phát hiện gọn có cấu trúc, không dump file.
13. **Ngôn ngữ output: Tiếng Việt** (khớp domain & người dùng cuối); code ref & thuật ngữ kỹ thuật giữ tiếng Anh. Không dịch xấp xỉ tên hàm/lớp — dùng định danh gốc trong source.
```
