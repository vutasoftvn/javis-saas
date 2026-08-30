# Data Egress Context — prerequisite cho Task 7 fail-closed hoàn toàn

**Ngày:** 2026-08-30

**Trạng thái:** Đặc tả prerequisite — chưa triển khai. Ghi nhận từ audit Task 7 ("feat: enforce source-grounded data access for model calls", commit 7a7435fb) và quyết định của người dùng cùng ngày (xem `task-7-report.md` trong cùng thư mục SDD).

**Phạm vi:** Điều kiện dữ liệu bắt buộc phải tồn tại TRƯỚC KHI `apps/cosa/compliance/data_model_gate.py` có thể enforce quan hệ category/provider/model mà không cần fallback nào cho MỌI request đi vào model. Đây không phải kế hoạch triển khai chi tiết (không có step/file/interface như Task 7) — đây là bản mô tả "cái gì phải có thật" để 1 plan triển khai sau này tham chiếu.

## 1. Vì sao tài liệu này tồn tại

Task 7 (2026-08-30) sửa 1 lỗ hổng cụ thể: `CosaDataModelGate` gọi `hasattr(self._client, "resolve_data_use")` để quyết định có enforce quan hệ dữ liệu hay không, nhưng `CompanyServiceClient` thật (client được wire trong `apps/cosa/composition/agent_plane.py`) không có method này — `hasattr` luôn `False` với client thật, nên toàn bộ enforcement rơi về `redactor.sanitize()` không kiểm tra gì (dead code). Audit xác nhận bằng cách đọc code, không phải suy đoán.

Task 7 đã sửa 2 việc an toàn: (a) thêm `resolve_data_use` thật vào `CompanyServiceClient`, (b) khi gate có client cấu hình (đường compliance-gated — con đường DUY NHẤT của runtime `openai_agents` production, xác nhận bằng cách đọc `agent_plane.py`: `compliance_resolver` và `model_input_guard` luôn được gán cùng nhau, không có nhánh nào bỏ qua compliance) mà KHÔNG có `DataAccessClaim` thật, gate DENY ngay thay vì suy đoán category/provider/model mặc định.

Nhưng Task 7 KHÔNG (và không nên) tự bịa ra nguồn dữ liệu thật cho `DataAccessClaim`. Grep toàn bộ `apps/cosa/` và `packages/agent/` tại thời điểm audit không tìm thấy bất kỳ capability/retrieval nào build `DataAccessClaim` thật — tài liệu này liệt kê chính xác cái gì cần tồn tại để việc đó khả thi mà không fallback.

## 2. Vấn đề cụ thể còn lại

### 2.1. `provider_key`/`model_key` không có nguồn thật đáng tin trong run

`ComplianceSnapshot` (`apps/cosa/compliance/contracts.py`, được `ComplianceResolver.resolve_for_run` — Task 4/5 — populate vào `run_context`) hiện có các trường: `workspace_id`, `deployment_id`, `assessment_id`, `mode`, `status`, `allowed_capabilities`, `provider_profile_version`, `data_profile_version`, `snapshot_hash`, `expires_at`, `policy_snapshot_hash`, `evidence_hashes`, `rule_version_ids`.

Không có trường nào trong số này là `provider_key`/`model_key` (ví dụ `"deepseek"`/`"deepseek-chat"`) — chỉ có `provider_profile_version` (1 chuỗi version như `"v3"`, không định danh provider/model nào). Nguồn thật duy nhất hiện có cho model là `AgentSpec.model_policy_ref` → `ModelPolicySpec.model` (ví dụ `"deepseek-chat"`, xem `packages/agent/contracts/model_policy.py`), nhưng giá trị này KHÔNG được thread vào `run_context` ở bất kỳ đâu trong `packages/agent_integrations/openai_agents_sdk/kernel.py` hiện tại — nó chỉ tồn tại trên `AgentSpec`/`ModelPolicySpec`, không tới tay `CosaDataModelGate`.

**Yêu cầu:** `provider_key`/`model_key` gửi vào `resolve_data_use` phải đến từ 1 provider profile ĐÃ ĐƯỢC PHÊ DUYỆT (`ai_provider_profiles`, status `APPROVED`) và PIN vào `ComplianceSnapshot` tại thời điểm resolve (Task 4). Việc bổ sung field này vào `ComplianceSnapshot`/`resolve_snapshot` response (`services/company/finance-legal/handlers/ai-compliance-runtime.handler.ts` và `apps/cosa/compliance/company_client.py::AiComplianceClient.resolve_snapshot`) là việc của 1 task kế tiếp riêng — KHÔNG tự làm trong Task 7.

### 2.2. Không có capability/retrieval nào gắn nhãn dữ liệu tại nguồn

`DataAccessClaim` (`apps/cosa/compliance/data_access_claim.py`) yêu cầu `source_ref`, `source_hash`, `categories` (frozenset), `purpose_id`, `capability_id`, `retention_policy_id`. Các trường này chỉ có ý nghĩa nếu nguồn dữ liệu (tài liệu, bản ghi CRM, hồ sơ tài chính, …) tự biết nó là gì — gate không được phép tự đoán category từ nội dung raw input.

`apps/cosa/capabilities/knowledge_read.py` (`knowledge.profile.read`) là ứng viên gần nhất về mặt hình dạng (đọc "profile tri thức doanh nghiệp") nhưng: (a) trả dữ liệu mẫu tĩnh (`insights: []`, không phải nguồn thật), (b) output đi qua `prepare_tool_output` (chỉ sanitize string/dict, không đọc `DataAccessClaim` nào), không phải qua `prepare_initial_input` (nơi enforce quan hệ dữ liệu thật). Không có capability nào khác trong `apps/cosa/capabilities/` build `DataAccessClaim`.

**Yêu cầu:** mỗi capability đọc dữ liệu nghiệp vụ thật trước khi đưa vào prompt (tài liệu, hồ sơ khách hàng, dữ liệu tài chính, …) phải tự đính kèm `DataAccessClaim` — nguồn nào biết dữ liệu là gì thì nguồn đó gắn nhãn, KHÔNG suy đoán ở gate.

### 2.3. User input (prompt trực tiếp) chưa có cơ chế gắn nhãn

Khi người dùng gõ prompt trực tiếp (không qua capability retrieval nào), hiện không có bước nào hỏi/xác nhận loại dữ liệu họ vừa nhập (có chứa dữ liệu cá nhân/nhạy cảm không). Đây là khoảng trống khác với 2.2 — 2.2 là dữ liệu do hệ thống lấy hộ, còn đây là dữ liệu do chính người dùng gõ vào.

**Cần có** 1 cơ chế intake/attestation — có thể là 1 bước hỏi/xác nhận category khi phát hiện prompt có khả năng chứa dữ liệu nhạy cảm (heuristic hoặc classifier nhẹ, không phải suy đoán chắc chắn), hoặc annotation tường minh từ UI (người dùng tự chọn "dữ liệu này chứa thông tin cá nhân của khách hàng X" trước khi gửi). Cơ chế chính xác (heuristic detection vs UI annotation bắt buộc vs cả hai) là quyết định thiết kế của task triển khai kế tiếp, không chốt ở đây.

## 3. Nguyên tắc bắt buộc khi thiết kế Data Egress Context

- Category `UNKNOWN`, hoặc category `PERSONAL`/`SENSITIVE_PERSONAL` không có `data_processing_authorizations` còn hiệu lực (GRANTED, không WITHDRAWN/RESTRICTED) → PHẢI DENY. Không có "coi như BUSINESS_CONFIDENTIAL cho an toàn" hay bất kỳ suy đoán ngầm nào thay thế authorization thật.
- `provider_key`/`model_key` phải khớp chính xác 1 `ai_provider_profiles` đã APPROVED, PIN vào snapshot tại thời điểm resolve — không đọc từ biến môi trường hay default runtime.
- `source_ref`/`source_hash` phải trỏ được về đúng bản ghi/tài liệu nguồn — đủ để audit truy vết ngược khi cần, nhưng KHÔNG lưu nội dung dữ liệu cá nhân/nhạy cảm vào audit trail (giữ nguyên nguyên tắc đã có ở `docs/superpowers/specs/2026-08-29-ai-compliance-design.md` §4.1: "Không lưu prompt, tài liệu gốc... làm evidence").
- Claim phải bind đúng `capability_id` đã thực thi — không phải 1 giá trị chung `"model.input"` cho mọi trường hợp một khi đã có capability retrieval thật (giá trị `"model.input"` hiện tại là placeholder tạm, không phải target cuối).

## 4. Tiêu chí nghiệm thu: khi nào coi là "đã có Data Egress Context thật"

Task kế tiếp được coi là hoàn thành — đủ điều kiện tắt fallback ở Task 7 — khi TẤT CẢ các điều sau đúng, có test chứng minh (không phải tuyên bố):

1. `ComplianceSnapshot`/response `resolve_snapshot` có `provider_key`/`model_key` lấy từ 1 `ai_provider_profiles` APPROVED thật, không phải string hard-code hay biến môi trường đọc trực tiếp trong runtime path.
2. Có ít nhất 1 capability retrieval thật (không phải `knowledge_read.py` placeholder hiện tại) build `DataAccessClaim` với `source_ref`/`source_hash`/`categories` lấy từ chính dữ liệu nó đọc — có test xác nhận category sai/thiếu ở nguồn → claim không được tạo → model call bị chặn.
3. Có cơ chế intake/attestation cho user input trực tiếp — ít nhất with 1 luồng xác nhận category rõ ràng khi hệ thống không tự tin về category (không phải luôn mặc định 1 category cố định).
4. `data_processing_authorizations` được tra cứu thật cho mọi category `PERSONAL`/`SENSITIVE_PERSONAL` trước khi model call, với test chứng minh: rút authorization (`WITHDRAWN`) → model call kế tiếp bị chặn ngay, 0 network call ra provider.
5. Test end-to-end (không phải chỉ unit test gate) chứng minh: 1 run thật đi qua ít nhất 1 capability retrieval + 1 user-input path, cả 2 đều mang claim thật, và quan sát được `resolve_data_use` gọi đúng field cho từng loại nguồn.

## 5. Cờ chuyển tiếp (feature flag) để tắt fallback có kiểm soát

Đến khi tiêu chí ở §4 đạt đủ, `CosaDataModelGate` vẫn cần 1 con đường vận hành cho các run không kiểm thử data governance (test suite hiện tại, môi trường dev chưa cấu hình Company thật) — đây chính là nhánh `self._client is None` giữ hành vi `redactor.sanitize()` cũ trong `apps/cosa/compliance/data_model_gate.py` (Task 7).

Khi Data Egress Context thật đã sẵn sàng (§4 đạt đủ), task kế tiếp phải:

- Thêm 1 cờ tường minh — đề xuất: field `data_egress_context_ready: bool` trên `workspace_ai_deployments` (Company DB, migrate có kiểm soát theo workspace, không phải global env var duy nhất — vì các workspace có thể chuyển đổi ở thời điểm khác nhau), HOẶC (nếu muốn global trước khi per-workspace) 1 biến môi trường rõ ràng theo cùng convention với `COSA_COMPLIANCE_MOCK` đã có trong `agent_plane.py` (ví dụ `COSA_DATA_EGRESS_CONTEXT_READY=1`), nhưng phải ghi rõ trong code đây CHỈ là bước trung gian trước khi chuyển hẳn sang per-workspace field.
- Khi cờ bật cho 1 workspace/deployment: xoá hẳn nhánh `self._client is None → sanitize-only` cho workspace đó (hoặc toàn cục nếu dùng biến môi trường global) — không để fallback tồn tại song song vô thời hạn không ai theo dõi.
- Ghi log/metric mỗi lần fallback path được dùng (workspace nào, khi nào) trong giai đoạn chuyển tiếp, để có dữ liệu quyết định khi nào an toàn tắt cờ toàn cục.

## 6. Việc KHÔNG nằm trong phạm vi tài liệu này

- Không tự làm ngay việc thêm `provider_key`/`model_key` vào `ComplianceSnapshot` (đó là việc của task kế tiếp, cần sửa cả Company API response lẫn `AiComplianceClient.resolve_snapshot`).
- Không tự chọn cơ chế intake/attestation cụ thể (heuristic vs UI bắt buộc) — đó là quyết định thiết kế UX/product cần bàn riêng.
- Không mở rộng phạm vi sang các miền COSA không phục vụ (y tế, giáo dục, tuyển dụng, …) — giữ nguyên phạm vi đã chốt ở `docs/superpowers/specs/2026-08-29-ai-compliance-design.md` §1.
