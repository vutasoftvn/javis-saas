# Dự án B — Verifier bắt buộc trước cổng duyệt

Ngày: 2026-10-05 · Trạng thái: DRAFT chờ duyệt · Phụ thuộc: Dự án A (cần `DoneCriteria`)

Tương ứng bước "DOT / KIỂM TRA: gom kết quả, đối chiếu mục tiêu" trong ảnh OpenAI Dots, đứng giữa thực hiện và "Bạn duyệt".

> Số dòng lấy từ khảo sát ngày 2026-10-05, cần xác minh lại trước khi sửa.

## 1. Bối cảnh và vấn đề

- `verifier_step_id` (`packages/agent/workflows/schema.py:56`) chỉ là khai báo. `_validate_dag` và `engine.py` không thực thi. Chỉ `loop_doctor.py:69-92` đọc, và chỉ khuyến nghị.
- `StepType` (schema.py:25) chưa có VERIFIER; `build_steps_from_spec` (engine.py ~L110-250) ném `UnsupportedWorkflowStepError` cho loại lạ.
- Hash của approval (`approval_step.py`) chỉ buộc `state[subject_key]`, **không buộc verdict**; founder có thể duyệt một artifact khác bản đã kiểm.
- Founder nhìn thấy rất ít khi duyệt: `gateway_internals.py` tạo approval chỉ với capability id và 8 ký tự hash.
- Luồng chat T2 (ADR-CHAT-ACTIONS-001) đi qua gateway, không qua workflow, nên một verifier chỉ ở workflow sẽ bỏ sót luồng này.
- `BudgetGate` chỉ in-memory và chưa nối runtime (`scheduled_tasks.py:~334`); chi tiêu thật nằm ở `models.run_usage` (migration 017).
- `ApprovalGateStep` định tuyến vai `operator`, trong khi ADR ghi founder. Cần chốt.

## 2. Quyết định thiết kế (đề xuất)

1. **Ép ở thời điểm biên dịch DAG:** mọi bước `APPROVAL_GATE` phải `depends_on` một bước `VERIFIER`; thiếu thì từ chối spec (hoặc tự chèn nếu cờ cho phép). Verifier ≠ producer (khác deployment/spec và khuyến nghị khác model).
2. **Verifier có hai tầng:** (a) tầng xác định, kiểm các `check: deterministic` của `DoneCriteria` và ánh xạ claim→evidence (tái dùng mẫu trong `executive_board/runner.py::_run_analysis` L57-150 và `DisconfirmingEvidenceChecker`); (b) tầng judge LLM cho các mục `rubric`, chạy bằng `AgentWorkflowStep` với deployment riêng.
3. **Verdict gắn vào hash duyệt:** `verification_report` hash đưa vào `subject_hash_key` của `ApprovalGateStep`, nên founder duyệt đúng bản đã được kiểm.
4. **Hiển thị cho founder:** tóm tắt verdict, tiêu chí đạt/không đạt, bằng chứng, chi phí, đưa vào `requirement`/subject của approval.
5. **Fail-closed mặc định:** FAIL ⇒ không bao giờ tới cổng duyệt (trả `FAILED` hoặc quay vòng qua `RETRY` tối đa N lần, rồi leo thang). INCONCLUSIVE ⇒ chuyển cho founder với nhãn rõ "chưa kiểm được", không coi là PASS.
6. **Phân loại theo tier:** bắt buộc cho T2/T3 và mọi approval gate; T0/T1 chỉ chạy tầng xác định (rẻ).
7. **Không trộn vào điểm kinh doanh:** verdict không tính vào `scorecard` (chỉ tính kết quả đã được người review). Ghi riêng như tín hiệu "verifier vs founder" để hiệu chuẩn verifier.

## 3. Các bước triển khai

### B1. Schema và bảng
- Migration Agent Core `020_verification_reports.sql` + `.down.sql` (idempotent, expand-only, cập nhật `migrations/README.md`):
  `agent.verification_reports(report_id, workspace_id, run_id, step_id, subject_hash, verdict PASS|FAIL|INCONCLUSIVE, criteria jsonb, evidence_refs jsonb, verifier_spec_hash, cost_usd, created_at)`, lọc/RLS theo `workspace_id`.
- Model `VerificationReport` (dataclass + `to_dict`, theo mẫu `EvidenceBalanceReport`).

### B2. Bước VERIFIER trong engine
- Thêm `StepType.VERIFIER` (schema.py) và nhánh builder trong `build_steps_from_spec` (engine.py).
- `VerifierStep.run`: đọc output producer từ `state[output_key]`, `DoneCriteria` từ `state["_manifest"]`/state (do A cung cấp), ghi `state["verification_report"]`; FAIL → `StepOutcome(FAILED)`.
- Thêm trạng thái "cần làm lại" nếu muốn vòng lặp: hiện `StepStatus` chỉ có COMPLETED/WAITING_APPROVAL/FAILED, nên dùng bước `RETRY` bao ngoài producer+verifier thay vì thêm status.
- `_validate_dag` (schema.py ~L83-150): luật "approval gate phải phụ thuộc verifier" và "verifier ≠ producer".
- `_execute_dag` chạy theo wave song song; xác nhận verifier là phụ thuộc cứng của gate.
- Test: `tests/agent/workflows/test_schema.py`, `test_dag_validation.py`, `test_dag_engine.py`, `test_approval_step.py`.

### B3. Buộc verdict vào approval
- `approval_step.py`: truyền hash của `verification_report` qua `subject_hash_key`; đưa tóm tắt verdict vào `requirement` JSONB (không bị `chk_agent_approvals_binding` chạm).
- `DurableApprovalService.verify_change_execution` (approval_service.py L219) kiểm lại hash khi resume.
- Test: `tests/agent/workflows/test_approval_step.py`.

### B4. Luồng chat T2 / gateway
- Trước khi `ApprovalGateDecider.decide` tạo approval (gateway_internals.py ~L395-500), chạy tầng xác định cho capability T2 (kiểm payload theo tiêu chí task nếu có); lưu báo cáo vào subject/requirement.
- Test: `tests/agent/capabilities/test_gateway_internals.py`.

### B5. Ngân sách
- Verifier ghi chi phí như một sub-record dưới run cha trong `models.run_usage`.
- Dự trữ cố định một phần ngân sách run cho verifier (tham số, ví dụ 10-15%) để executor tiêu hết cũng không bỏ qua kiểm tra.
- Nối `BudgetGate.evaluate_budget` với `run_usage` thật cho pre-check (hiện chưa nối). Hết ngân sách ⇒ theo chính sách đã chọn (mục 5).

### B6. Governance và loop_doctor
- `loop_doctor.py`: nâng "thiếu verifier" từ khuyến nghị lên CRITICAL cho workflow có approval gate hoặc side effect.
- `governance/floor.py`: verdict FAIL là đầu vào `conjoin` (strictest-wins, không nới).

### B7. Eval và rollout
- Thêm case eval với đầu ra xấu cố ý (phải FAIL) vào `evals/` (BUSINESS_CORRECTNESS / SECURITY_GOVERNANCE).
- Cờ `WORKFLOW_VERIFIER_ENFORCED`: mặc định tắt cho workflow hiện có (`strategy_gate_evaluation_flow.yaml` chưa có gate), bật mặc định cho workflow mới, rồi bật toàn bộ sau khi soak.
- Lưu ý: thêm trường vào schema workflow đổi `definition_hash` của spec đã pin; cần plan tương thích.

## 4. Rủi ro

- Verifier là LLM ⇒ không xác định. Tiêu chí `deterministic` phải chiếm đa số; judge chỉ cho phần rubric.
- Tự chấm (self-grading): `loop_doctor` hiện chỉ so id; cần so cả deployment/spec.
- Chi phí và độ trễ tăng; kiểm soát bằng tier và dự trữ ngân sách.
- Verdict cũ ghép với artifact đã sửa: giải bằng hash binding (B3).
- Hiện không có workflow nào có approval gate để bật thử; B có thể cần một workflow mẫu để chứng minh vòng đời đầu-cuối.

## 5. Xác minh

```bash
make agent-test
make apps-cosa-test
make lint typecheck-py
make migration-check
make boundary-check
```

Kiểm tra: workflow mẫu `producer → verifier → approval_gate`; (1) đầu ra đúng ⇒ tới cổng duyệt với verdict hiển thị; (2) đầu ra xấu ⇒ dừng ở verifier; (3) sửa artifact sau khi kiểm ⇒ approve bị từ chối do lệch hash; (4) hết ngân sách ⇒ hành vi đúng chính sách.

## 6. Quyết định cần chủ dự án chốt

1. Hết ngân sách verifier: **chặn hẳn (fail-closed, đề xuất)** hay trình founder với nhãn "CHƯA KIỂM TRA"?
2. Cổng duyệt định tuyến `operator` hay `founder`? (ADR-CHAT-ACTIONS-001 ghi founder.)
3. Có cần 2 verifier đồng thuận (dùng `quorum.py`) cho T3 không, hay một là đủ?
