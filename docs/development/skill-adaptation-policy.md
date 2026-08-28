# Chính Sách Thích Ứng & Quản Trị Nguồn Gốc Skillpack (Skill Adaptation Policy)

**Ngày ban hành:** 2026-08-28  
**Tài liệu tham chiếu:** `skillpacks/platform/skill-adaptation/SKILL.md`  
**Chương trình:** [Chương trình tích hợp marketingskills + makerskills vào COSA](../integrations/2026-08-28-marketingskills-makerskills-program.md)  
**Mục đích:** Quy định các tiêu chuẩn bắt buộc khi tiếp nhận, chuyển đổi (adaptation), theo dõi nguồn gốc và quản trị các gói kỹ năng (Skillpacks) từ bên ngoài vào kho mã nguồn COSA.

---

## 1. Nguyên Tắc Cốt Lõi (Core Principles)

1. **Source Material Only (Chỉ là tài liệu tham chiếu):** Mọi skillpack nằm trong `skillpacks/` là tài liệu tham chiếu tĩnh, cung cấp hướng dẫn (guidelines) và cấu trúc mẫu. Skillpack **tuyệt đối không** được coi là quyền thực thi mã tự do và không được tự động cấp quyền runtime.
2. **Không Auto-Discovery Runtime:** `build_cosa_agent_plane()` chỉ đăng ký các capability được định nghĩa tường minh bằng mã nguồn Python trong `apps/cosa/capabilities/`. Nghiêm cấm quét thư mục `skillpacks/` lúc khởi động agent plane.
3. **Bất Biến & Truy Xuất Nguồn Gốc (Immutability & Provenance):** Mọi nội dung thích ứng từ bên ngoài phải được gắn với một commit SHA 40 ký tự bất biến và ghi nhận vào sổ cái `docs/integrations/skill-source-attribution.md`.
4. **Không Git Submodule / Không Auto-Sync ngầm:** Nghiêm cấm dùng submodule hoặc cron bot tự động kéo mã nguồn từ upstream. Mọi cập nhật phải qua quy trình review thủ công có kiểm soát.

---

## 2. Cổng Kiểm Soát Giấy Phép Bản Quyền (License Gating)

Mọi mã nguồn bên ngoài trước khi được đưa vào quy trình thích ứng phải vượt qua bước kiểm tra giấy phép:

| Loại Giấy Phép | Trạng Thái | Điều Kiện & Xử Lý |
| --- | --- | --- |
| **MIT, Apache 2.0, BSD-3-Clause, ISC** | **ĐƯỢC DUYỆT (Approved)** | Giữ nguyên thông báo bản quyền gốc, ghi rõ URL dẫn chiếu và commit SHA trong phần `## Nguồn`. |
| **GPL v2/v3, AGPL, SSPL** | **TỪ CHỐI (Rejected)** | Không được sao chép hoặc chuyển đổi trực tiếp do xung đột điều khoản copyleft với kiến trúc phần mềm độc quyền của COSA. |
| **Không rõ giấy phép / All Rights Reserved** | **TỪ CHỐI (Rejected)** | Không tiếp nhận khi chưa có thỏa thuận cấp phép bằng văn bản từ tác giả gốc. |

---

## 3. Khung Phân Loại Chuyển Đổi (Keep / Adapt / Add / Exclude Framework)

Mọi quá trình thích ứng một skillpack phải được phân loại thành 4 nhóm hành động rõ ràng trong section `## Nguồn` của `SKILL.md`:

```yaml
adaptation:
  kept:
    - [Các nguyên lý cốt lõi, công thức, framework đã được kiểm chứng từ skill gốc]
  changed:
    - [Đường dẫn file, thuật ngữ chuẩn hóa COSA, định dạng markdown tiếng Việt]
  added:
    - [Cấu trúc 10 mục bắt buộc, phân định Facts vs Inference, Evidence vs Assumption, Safe Fallback, Phòng vệ Prompt Injection]
  excluded:
    - [Các hành vi gây side-effect tự do, outbound spam, nạp động runtime, tự động commit ngầm]
```

### Các Thành Phần Bị Loại Bỏ Vĩnh Viễn (Permanently Excluded)
- **Outbound Spam:** Gửi cold email tự động, SMS marketing hàng loạt, spam bot mạng xã hội (loại bỏ từ `ads`, `cold-email`, `emails`, `sms`, `social`).
- **Uncontrolled Local Execution:** Tự động gọi shell cron local, self-wakeup vô hạn trong prompt, tự động commit/push git không qua human review.
- **Direct Database Mutation:** Tự động sửa giá trong cổng thanh toán, tự động trừ tiền ngân hàng hoặc thay đổi quyền truy cập hệ thống khi chưa qua cổng phê duyệt (Approval Gate).

---

## 4. Cấu Trúc Bắt Buộc Của Một Skillpack (10-Section Contract)

Mỗi skillpack tại `skillpacks/<domain>/<id>/` bắt buộc phải có 2 file:
1. `manifest.yaml`: Đúng schema `apiVersion: agentos.ai/v1`, `kind: Skill`, đầy đủ các mục `metadata`, `publisher`, `source`, `capability`, `runtime`, `permissions`, `risk`, `trust`.
2. `SKILL.md`: Chứa YAML frontmatter (`name: normalize_discovery_name(metadata.id)`, `description`) và 10 phần nội dung chuẩn:
   - `## 1. Mục Tiêu (Objective)`
   - `## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)`
   - `## 3. Điều Kiện Tiên Quyết (Prerequisites)`
   - `## 4. Các Bước Tất Định (Deterministic Steps)`
   - `## 5. Tool Calls Được Phép (Allowed Tool Calls)` — Khớp chính xác với `manifest.runtime.tools`.
   - `## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)` — Phân định rõ Facts vs Inference, Evidence vs Assumption; cấm bịa đặt.
   - `## 7. Safe Fallback` — Kế hoạch non-mutating khi capability runtime chưa khả dụng.
   - `## 8. Định Dạng Đầu Ra (Output Format)`
   - `## 9. Xử Lý Lỗi & Phòng Vệ Prompt Injection (Security & Edge Cases)`
   - `## 10. Nguồn (Review Record)` — Khối YAML `upstream` và `adaptation`.

---

## 5. Quy Tắc Đánh Số Phiên Bản (Versioning Rules)

- **Khởi tạo mới (New Skillpack):** Phiên bản bắt đầu là `1.0.0`.
- **Thích ứng nâng cấp tại chỗ (In-Place Adaptation):** Nâng phiên bản `1.0.0 -> 1.1.0`.
- **Bổ sung Capability runtime mới (Phase B):** Nâng phiên bản `1.1.0 -> 2.0.0` (yêu cầu tạo immutable `SkillSpec` và tính toán lại `definition_hash`).

---

## 6. Quy Trình Rà Soát Tác Động Phụ Thuộc Chéo (Cross-Skill Impact Review)

Khi một skillpack được tạo mới hoặc cập nhật:
1. Kiểm tra các recipe hoặc skillpack khác có tham chiếu tới `metadata.id` của pack này không.
2. Mọi tham chiếu liên-skill bắt buộc dùng định danh chuẩn dạng `domain.name` (ví dụ: `marketing.positioning`), tuyệt đối không dùng tên tự do hoặc đường dẫn file tương đối.
3. Chạy toàn bộ bộ kiểm tra tự động trước khi tạo Pull Request:
   ```bash
   python scripts/validate_skillpacks.py
   pytest tests/agent_core/skills/test_skillpack_contract.py tests/apps/cosa/test_agent_plane_skillpack_boundary.py -q
   ```
