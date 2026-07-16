# Nhiệm vụ: Sửa các bug phát hiện khi deploy PKM lên production

## Bối cảnh (KHÔNG cần điều tra lại)
Đợt deploy module PKM lên server production (commit e9320fd) đã bộc lộ 5 bug.
Tôi đã vá nóng trực tiếp trên server để deploy chạy được, nhưng các fix đó CHƯA
về repo. Cần commit + push lên main để: (a) lần deploy sau không bị lại, (b)
server mới deploy đúng. Đã verify tất cả fix dưới đây hoạt động trên prod.

Repo: github.com:pkm2025/visota.git (nhánh main). Đọc kỹ trước khi sửa.

## Fix 1 — Thêm 6 dependency thiếu cho module PKM
File: `requirements.txt`

PKM import 6 package chưa được khai báo trong requirements. Khi build image,
`pip install -r requirements.txt` không cài chúng → container crash với
ModuleNotFoundError. AST scan `apps/pkm/` cho ra các import bên thứ 3:
cryptography, litellm, docx (=python-docx, đã có), openpyxl (đã có),
langchain_text_splitters, pypdf, tiktoken.

Thêm vào `requirements.txt`, sau dòng `playwright>=1.40` (phần non-freeze):
```
cryptography>=43.0
markdown>=3.5
litellm>=1.40
langchain-text-splitters>=0.3
pypdf>=4.0
tiktoken>=0.7
```
Đã verify: diff chính xác là +6 dòng như trên. KHÔNG sửa phần "Full freeze" bên dưới.

Lý do từng package:
- `cryptography` — `apps/pkm/services/encryption_service.py` dùng Fernet.
- `litellm` — `apps/pkm/services/llm_service.py`, `qa_service.py`, `rag_pipeline.py`.
- `markdown` — `apps/ui_modern/views/pkm_views.py`.
- `langchain-text-splitters` — `apps/pkm/services/chunking_service.py`.
- `pypdf` — `apps/pkm/services/doc_parser.py` (PDF text extraction).
- `tiktoken` — `apps/pkm/services/chunking_service.py` (count tokens).

## Fix 2 — dexie.min.js thiếu sourcemap làm WhiteNoise crash
File: `static/vendor/js/dexie.min.js`

`dexie.min.js` (commit `2d7e142`, file vendored) kết thúc bằng:
`//# sourceMappingURL=dexie.min.js.map`
nhưng file `.map` KHÔNG tồn tại → `collectstatic` với
`whitenoise.storage.CompressedManifestStaticFilesStorage` raise
`MissingFileError` trong post-process → entrypoint die → container restart loop.

Fix đã verify trên prod: xóa dòng `//# sourceMappingURL=dexie.min.js.map` khỏi
cuối file. Lệnh đã chạy trên server:
```
sed -i 's|//# sourceMappingURL=dexie.min.js.map||g' static/vendor/js/dexie.min.js
```
(Kết quả: file từ 94277 bytes → 94240 bytes, md5 = 0e9fc2ec28bd295f93eb968678de42f5)

ĐỒNG THỜI sửa `scripts/install_vendor_assets.sh` để lần install sau không tái diễn:
hiện script không cài dexie (chỉ bootstrap/htmx/alpine), nhưng nếu sau này thêm
dexie thì phải strip sourcemap. Thêm hàm strip chung và gọi cho mỗi file copy
vào `static/vendor/js/`:
```bash
# Strip sourceMappingURL references — WhiteNoise CompressedManifestStaticFilesStorage
# fail collectstatic nếu .map không tồn tại. Vendor files vendored không cần sourcemap.
strip_sourcemap() { sed -i 's|//# sourceMappingURL=[^ ]*||g' "$1"; }
```
Gọi `strip_sourcemap` cho mỗi file JS vendor copy vào (an toàn, no-op nếu
không có reference).

## Fix 3 — docker-compose.yml trong repo là file DEV, gây nhầm với prod
File: `docker-compose.yml` → rename thành `docker-compose.dev.yml`

File `docker-compose.yml` trong repo (commit đợt PKM) chứa compose DEV:
container `pmketoan-mariadb`/`pmketoan-redis`, password `rootpass`/`devpass`,
KHÔNG có Traefik labels, KHÔNG có service `web`/`worker`/`db` của visota.
Trên production, file prod (visota-web/visota-db/Traefik) được `visota-ctl` sinh
riêng và là untracked → git pull không conflict, nhưng tên file trùng gây nhầm
lẫn nghiêm trọng khi vận hành.

Fix đã verify trên prod:
```
git mv docker-compose.yml docker-compose.dev.yml
```
Thêm nhận xét dòng đầu trong `docker-compose.dev.yml`:
```
# DEV ONLY — dùng cho local/dev. Production dùng compose do visota-ctl sinh
# (visota-web/visota-db/worker + Traefik labels). KHÔNG deploy file này lên prod.
```

## Fix 4 — visota-ctl: bug mask password trong _dv (deploy server mới)
File: `scripts/server/visota-ctl`, hàm `_dv` (khoảng dòng 165)

Commit `e9320fd` ("fix(ops): visota-ctl auto-enables podman pod autostart") đã
làm hỏng dòng sinh `.env` khi deploy visota lần đầu. Dòng hiện tại:
```bash
printf 'DJANGO_SETTINGS_MODULE=config.settings.prod\nSECRET_KEY=%s\nDB_ROOT_PASSWORD=%s\nDB_NAME=visota\nDB_USER=visota\nDB_PASSWORD=********************************************************************************alhost\nGUNICORN_WORKERS=4\n' "$s" "$dp" "$dp" "$d" "$ap" "$d" "$d">.env
```
Hai vấn đề:
1. Placeholder `%s` cho DB_PASSWORD/SUPERUSER_PASSWORD/ALLOWED_HOSTS bị thay
   bằng chuỗi `*****...alhost` → các biến `%s` cuối không còn placeholder khớp.
2. Mất dòng `SUPERUSER_EMAIL`, `SUPERUSER_PASSWORD`, `ALLOWED_HOSTS`.

Đây có vẻ là lỗi editor/regex khi agent trước mask secret nhưng vô tình đè cả
template. CHỈ ảnh hưởng khi deploy server mới (server hiện tại đã có .env nên
không sai), nhưng nhất định phải sửa.

Dòng đúng (khôi phục từ `git show 3abb9dd:scripts/server/visota-ctl`):
```bash
printf 'DJANGO_SETTINGS_MODULE=config.settings.prod\nSECRET_KEY=%s\nDB_ROOT_PASSWORD=%s\nDB_NAME=visota\nDB_USER=visota\nDB_PASSWORD=%s\nSUPERUSER_EMAIL=admin@%s\nSUPERUSER_PASSWORD=%s\nALLOWED_HOSTS=%s,www.%s,localhost\nGUNICORN_WORKERS=4\n' "$s" "$dp" "$dp" "$d" "$ap" "$d" "$d">.env
```
Verify: số `%s` = 7, số arg = 7 (`$s $dp $dp $d $ap $d $d`).

## Fix 5 — prod compose: upgrade MariaDB 11.4 → 11.8 LTS
File: `scripts/server/visota-ctl`, hàm `_wvc` (sinh docker-compose prod)

Module PKM dùng `VECTOR(1536)` type + `VEC_FromText`/`VEC_DISTANCE_COSINE`
(`apps/pkm/services/vector_store.py`). VECTOR chỉ có từ MariaDB 11.7, và 11.8
LTS mới phù hợp production. MariaDB 11.4 (LTS cũ, đang được _wvc sinh) KHÔNG
hỗ trợ VECTOR → migration PKM fail: `ERROR 4161: Unknown data type: 'VECTOR'`.

Đã verify trên prod: 11.8.8 hỗ trợ đầy đủ VECTOR + VEC_FromText +
VEC_DISTANCE_COSINE, in-place upgrade từ 11.4 sạch (117 bảng data nguyên vẹn).

Sửa trong `_wvc` (hàm sinh docker-compose.yml prod): dòng image của service db:
```
    image: docker.io/library/mariadb:11.4
```
thành:
```
    image: docker.io/library/mariadb:11.8
```
(Cũng có file `docker-compose.yml` prod ở working tree trên server đã sửa —
nhưng đó là untracked, cần sửa ở _wvc trong visota-ctl để lần deploy sau đúng.)

## Ràng buộc & deliverable
- Mỗi fix là 1 commit riêng, conventional commits, scope hợp lý:
  - `fix(deps): add missing PKM dependencies (cryptography, litellm, markdown, pypdf, tiktoken, langchain-text-splitters)`
  - `fix(static): strip sourceMappingURL from dexie.min.js (WhiteNoise MissingFileError)`
  - `refactor(deploy): rename dev docker-compose to docker-compose.dev.yml to avoid prod confusion`
  - `fix(ops): restore .env template placeholders in visota-ctl _dv`
  - `fix(ops): bump MariaDB to 11.8 LTS in visota-ctl prod compose (VECTOR type for PKM)`
- Commit trực tiếp lên nhánh `main` rồi push origin main.
- KHÔNG động đến: hàm `dk()`, menu, `_ensure_autostart`, hoặc code Django.
- Test trước khi push: `bash -n scripts/server/visota-ctl`; `pip install -r
  requirements.txt` trong venv sạch (verify 6 package cài được); `python -c
  "import cryptography, litellm, markdown, pypdf, tiktoken; from
  langchain_text_splitters import RecursiveCharacterTextSplitter"`.
- Báo lại 5 commit hash trên main.
