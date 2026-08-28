---
name: platform-skill-adaptation
description: Hướng dẫn quy trình tiếp nhận, đánh giá bản quyền, chuyển đổi nội dung (Keep/Adapt/Add/Exclude) và quản trị nguồn gốc skillpack theo chính sách COSA.
---

# Quy Trình Thích Ứng & Quản Trị Nguồn Gốc Skillpack (Skillpack Adaptation & Governance)

## 1. Mục Tiêu (Objective)
Chuẩn hóa quy trình chuyển đổi tài liệu kỹ năng từ các kho mã nguồn bên ngoài vào COSA, kiểm soát chặt chẽ giấy phép bản quyền (License Gate), duy trì sổ cái nguồn gốc (Attribution Ledger), tuân thủ quy tắc đánh số phiên bản và bảo vệ ranh giới an toàn của COSA Agent Plane. Chính sách chi tiết được quy định tại `docs/development/skill-adaptation-policy.md`.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi tiếp nhận và thích ứng (adapt) một kỹ năng hoặc công thức mới từ cộng đồng nguồn mở vào thư mục `skillpacks/`.
  - Khi cần cập nhật phiên bản hoặc đánh giá lại giấy phép và tác động phụ thuộc của một skillpack hiện hữu.
  - Khi xác thực hợp đồng tĩnh giữa `manifest.yaml`, `SKILL.md` và sổ cái `docs/integrations/skill-source-attribution.md`.
- **Khi nào KHÔNG dùng**:
  - Khi trực tiếp đăng ký một capability runtime trong backend Python (`apps/cosa/capabilities/`).
  - Khi viết tài liệu hướng dẫn kỹ thuật thông thường không phải là skillpack (dùng `docs/`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
- Kho mã nguồn gốc có giấy phép tương thích (MIT, Apache 2.0 hoặc BSD).
- Mã băm SHA commit 40 ký tự bất biến từ kho nguồn bên ngoài.

## 4. Các Bước Tất Định (Deterministic Steps)
1. **Kiểm Tra Cổng Giấy Phép Bản Quyền (License Gating)**:
   - Chỉ chấp nhận các mã nguồn có giấy phép tương thích (MIT, Apache 2.0, BSD-3-Clause).
   - Tuyệt đối từ chối các mã nguồn có giấy phép copyleft nghiêm ngặt (GPL, AGPL) hoặc không rõ giấy phép.
2. **Khung Phân Loại 4 Nhóm (Keep / Adapt / Add / Exclude)**:
   - **Kept (Giữ nguyên)**: Các nguyên lý cốt lõi, công thức, framework đã được kiểm chứng từ skill gốc.
   - **Changed (Sửa đổi)**: Thuật ngữ, đường dẫn file, định dạng markdown tiếng Việt, data model chuẩn hóa theo COSA.
   - **Added (Bổ sung)**: 10 mục cấu trúc chuẩn, phân định Facts vs Inference, Evidence vs Assumption, Safe fallback, phòng vệ Prompt Injection, Review record.
   - **Excluded (Loại bỏ)**: Các hành động có side-effect tự do, công cụ outbound spam, cơ chế nạp động hoặc tự động commit.
3. **Chuẩn Hóa Cấu Trúc File & Hợp Đồng Tĩnh**:
   - `manifest.yaml`: Khai báo đầy đủ `apiVersion`, `kind: Skill`, `metadata.{id, name, version, description}`, `source.path`, `capability`, `runtime`, `permissions`, `risk`, `trust`.
   - `SKILL.md`: Frontmatter `name: normalize_discovery_name(metadata.id)`, đầy đủ 10 mục cấu trúc bắt buộc và mục `## Nguồn` dạng YAML block.
4. **Cập Nhật Sổ Cái Nguồn Gốc (Attribution Ledger)**:
   - Ghi nhận một dòng tương ứng vào `docs/integrations/skill-source-attribution.md` với commit SHA 40 ký tự, giấy phép, ngày review và trạng thái `adapted`.
5. **Đánh Số Phiên Bản (Versioning Rules)**:
   - Skillpack mới: Khởi tạo ở phiên bản `1.0.0`.
   - Skillpack nâng cấp nội dung thích ứng: Tăng phiên bản `1.0.0 -> 1.1.0`.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
Không có tool call runtime nào được khai báo cho skillpack này.
Quy trình thực hiện thông qua công cụ dòng lệnh xác thực hợp đồng scripts/validate_skillpacks.py.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- Mọi skillpack có nguồn gốc bên ngoài bắt buộc phải có commit SHA 40 ký tự bất biến để đảm bảo khả năng tái lập và truy xuất nguồn gốc.
- Không chấp nhận branch name hoặc tag động (như `main`, `master`, `latest`) làm tham chiếu commit.

## 7. Safe Fallback & Ranh Giới An Toàn (Source-Only Policy)
- **Ranh giới bảo mật:** Mọi skillpack trong `skillpacks/` là **tài liệu tham chiếu tĩnh (Source-only / Reference material)**.
- **Không thực thi tự do:** Skillpack tuyệt đối KHÔNG tự động đăng ký capability vào agent plane lúc runtime mà không qua các bước thẩm định và đăng ký tường minh trong `build_cosa_agent_plane()`.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Báo Cáo Thích Ứng Skillpack (Skillpack Adaptation Summary)

## 1. Thông Tin Nguồn & Bản Quyền
- **Skillpack ID**: `[domain].[name]`
- **Upstream Repository**: `[org/repo]` (Commit: `[40-char SHA]`)
- **Giấy phép**: `MIT / Apache 2.0` - `[License Gate: PASSED]`

## 2. Bảng Phân Loại Thay Đổi
- **Kept**: [Các nguyên lý giữ nguyên]
- **Changed**: [Các phần chuyển đổi sang COSA]
- **Added**: [Bổ sung governance, safe fallback, prompt injection defense]
- **Excluded**: [Loại bỏ side-effect tự do, outbound spam]

## 3. Kết Quả Xác Thực Hợp Đồng (Contract Validation)
- `validate_skillpacks.py`: **0 violation**
- `test_skillpack_contract.py`: **PASSED**
```

## 9. Xử Lý Lỗi & Edge Cases (Failure & Edge Case Handling)
- **Tên skill không được chuẩn hóa**: Sử dụng `normalize_discovery_name(metadata.id)` để tự động chuyển thành chữ thường, dấu gạch ngang (ví dụ: `platform.skill-adaptation` -> `platform-skill-adaptation`).
- **Thiếu dòng ledger**: Chặn quá trình merge cho tới khi bổ sung đầy đủ thông tin vào `docs/integrations/skill-source-attribution.md`.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: coreyhaines31/makerskills
  commit: 33cb3870685a34522d91287869aef62170bdbcf7
  skill: skillify, pm, toolify
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - Khung đóng gói kỹ năng, Checklist chuẩn bị và chuẩn hóa hướng dẫn
  changed:
    - Chuyển đổi từ cơ chế tự động commit sang quy trình rà soát quản trị con người
    - Chuẩn hóa sang cấu trúc hợp đồng tĩnh COSA (manifest.yaml + SKILL.md)
  added:
    - Chính sách quản trị chuyển đổi (Keep/Adapt/Add/Exclude)
    - Cổng kiểm soát giấy phép bản quyền và sổ cái nguồn gốc bất biến
    - Quy tắc cấm nạp động runtime
  excluded:
    - Loại bỏ tính năng tự động tạo mã và tự động commit ngầm vào git
```
