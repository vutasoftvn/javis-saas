# Phase 11 — Business Feature Decision Tree & Smoke Test Cross-Domain

> Chi tiết thực thi cho Phase 11 của `docs/architecture/COSA_IMPLEMENTATION_ROADMAP_2026-08-22.md`. Mục tiêu: chốt quy trình bắt buộc cho mọi tính năng mới từ nay về sau, và chứng minh toàn bộ pipeline đã xây (Phase 1-10) hoạt động thật bằng smoke test end-to-end cross-domain — không chỉ unit test từng phần riêng lẻ.

## 11a. Business Feature Decision Tree (§18.1-18.2)

**Task:**
1. Viết `docs/architecture/COSA_FEATURE_IMPLEMENTATION_TREE.md`, nội dung tối thiểu — decision tree dạng có thể áp dụng trực tiếp (không chỉ mô tả lý thuyết):

```
Yêu cầu tính năng mới X
      │
      ▼
X chỉ thay đổi cách trình bày (UI/response format), không tạo/đổi business record?
      │YES → sửa ở Flutter (frontend/) hoặc Agent API event contract (agentos/api/) — KHÔNG chạm services/
      │NO
      ▼
X cần business record tồn tại lâu dài (đọc lại được, có lifecycle, cross-reference)?
      │YES → owner là 1 bounded context trong services/ đã có (control-plane/identity/operations/commercial/finance-legal)
      │        → schema + migration → service logic tất định → handler/API → domain event
      │        → chỉ tạo services/<new> mới nếu ĐỦ CẢ 3 điều kiện §18.2 (bounded context độc lập rõ ràng;
      │          lifecycle/data ownership khác biệt hẳn; mở rộng service hiện tại gây coupling xấu đáng kể)
      │NO
      ▼
X cần agent gọi 1 khả năng đã có ở services/ (đọc hoặc ghi)?
      │YES → tạo/tái dùng Tool (ToolSpecV2, Phase 3a) → không viết business logic trong tool handler
      │NO
      ▼
X cần agent biết "làm sao để" thực hiện 1 loại việc (quy trình, khi nào dùng tool nào)?
      │YES → Skill (skillpacks/, Phase 5a) — chỉ tạo Skill mới nếu KHÔNG phải chỉ là 1 API CRUD, 1 business rule,
      │        1 chuỗi retry/approval (đó là Workflow), hoặc 1 persona (đó là Agent Profile)
      │NO
      ▼
X cần nhiều bước tất định có thể fail/compensate/pause (không cần suy luận multi-agent)?
      │YES → Deterministic Workflow (agentos/workflows/, Phase 8b)
      │NO
      ▼
X cần nhiều specialist agent phối hợp/suy luận song song?
      │YES → ADK Orchestration (agentos/orchestration/adk/, Phase 9)
      │NO
      ▼
X đã có sẵn qua Agent API (chat/tool/skill đã tồn tại)?
      │YES → chỉ cần Text Chat/Voice expose nó — KHÔNG viết business logic mới trong voice_tools.py/chat handler
```

2. Thêm 1 checklist ngắn cuối tài liệu để dùng trong PR template (nếu repo có PR template, chèn link vào đó): "Trước khi merge tính năng mới, xác nhận đã đi đúng nhánh nào trong cây quyết định ở trên, ghi rõ trong PR description."
3. Rà lại toàn bộ tính năng đã xây ở Phase 2-10 (Strategy domain, ToolSpecV2, Skill, Workflow, ADK) — xác nhận từng cái khớp đúng nhánh cây quyết định tương ứng đã áp dụng khi implement (đối chiếu ngược, không sửa lại code nếu đã đúng nguyên tắc, chỉ cần liệt kê xác nhận trong tài liệu).

**Acceptance:**
- [ ] `COSA_FEATURE_IMPLEMENTATION_TREE.md` tồn tại, có sơ đồ quyết định như trên, không bị rút gọn mất nhánh nào.
- [ ] Rà soát ngược Phase 2-10 xác nhận không có tính năng nào đi sai nhánh (nếu phát hiện sai lệch, ghi vào tài liệu như "known deviation" kèm lý do, không im lặng bỏ qua).

## 11b. Smoke test — Strategy feature end-to-end (§5.2 startup flow đầy đủ)

**Task:**
1. Viết 1 test kịch bản đầy đủ, chạy qua **thật sự toàn bộ stack đã xây** (Text Chat API → Agent Runtime → Skill routing → Tool call → services/operations/strategy → DB → response), không mock ở tầng service:

```
Bước 1: Founder gửi message qua POST /agent/conversations/{id}/messages:
        "Chúng tôi đang xây CRM cho agency. Bây giờ nên làm gì?"
Bước 2: Assert SSE stream phát đúng thứ tự event:
        run.started → tool.requested (strategy.project.get hoặc tương đương)
        → tool.completed → message.delta (nhiều lần) → run.completed
Bước 3: Assert skill được chọn đúng là `strategy.stage-assessment` (Phase 5b) — kiểm tra qua
        RunEvent/trace, không suy đoán từ response text.
Bước 4: Assert agent gọi tiếp `strategy.assumption-discovery` → tạo được ít nhất 1
        record `assumptions` thật trong DB (query trực tiếp bảng, Phase 2b).
Bước 5: Assert agent đề xuất experiment qua `strategy.experiment-design`, tool call
        `strategy.experiment.create` tạo record `experiments` thật, liên kết đúng
        `assumption_id`.
Bước 6: Giả lập tool risk đủ cao để trigger approval (hoặc chọn 1 action có risk_level=high
        trong chuỗi này) → assert event `approval.required` xuất hiện đúng.
Bước 7: Gọi POST /agent/approvals/{approval_id}/decision với APPROVED → assert cùng run_id
        tiếp tục (Phase 8a), record được tạo sau approval.
Bước 8: Assert `strategy.evidence.create` được gọi khi có evidence liên quan (interview
        trước đó nếu có sẵn trong fixture test).
Bước 9: Gọi GET /operations/strategy/projects/{id}/next-best-actions → assert trả về
        candidate hợp lý dựa trên state vừa tạo (assumption chưa giải quyết → NBA candidate
        liên quan tới assumption đó phải xuất hiện).
```
2. Test này chạy trong CI như 1 integration test riêng biệt (có thể chậm hơn unit test, chấp nhận được, đánh dấu `@pytest.mark.integration` hoặc tương đương convention repo đang dùng).
3. Chạy smoke test này mỗi lần release/merge vào nhánh chính (không nhất thiết mỗi commit, nhưng bắt buộc trước khi coi 1 release là "Strategy domain hoạt động").

**Acceptance:**
- [ ] Smoke test tồn tại, pass trên môi trường CI/staging thật (không chỉ chạy local).
- [ ] Test thất bại rõ ràng ở đúng bước nào khi có regression (không phải lỗi mơ hồ timeout chung chung) — mỗi bước có assertion message cụ thể.
- [ ] Xác nhận governance/approval hoạt động đúng trong chuỗi thật (không phải test approval riêng lẻ, mà đúng trong context của 1 flow nghiệp vụ dài).

## 11c. Smoke test — Commercial feature (§4.5 CRM + experiment linkage)

**Task:**
1. Viết test kịch bản: `Experiment (đã tạo ở 11b hoặc tạo mới) → liên kết Lead (services/commercial) → Evidence sourced từ Lead/Opportunity → Opportunity cập nhật trạng thái dựa evidence`.
2. Cụ thể:
   - Tạo 1 `Lead` qua `commercial.lead.create` (tool đã có từ trước Phase 2, xác nhận tool này tồn tại — nếu chưa, đây là gap cần bổ sung ở `services/commercial` trước khi viết test, không phải việc của Phase 11).
   - Tạo `Experiment` (Phase 2b) với field tham chiếu `sourceExperimentId`/`leadRef` trỏ tới Lead vừa tạo (theo đúng nguyên tắc §4.5 guide gốc: "Experiment → sourceExperimentId → Lead", không tạo bảng liên kết mới nếu field tham chiếu là đủ).
   - Ghi `Evidence` (Phase 2b) với `source_type` trỏ về Lead/Opportunity.
   - Assert: có thể truy vấn ngược từ Lead ra Experiment liên quan, và từ Experiment ra Evidence liên quan (đúng chuỗi nhân quả, không đứt gãy dữ liệu).

**Acceptance:**
- [ ] Test end-to-end: `experiment → lead → opportunity → evidence` chạy qua tool call thật (không mock DB), pass.
- [ ] Xác nhận không có bảng liên kết trùng lặp được tạo mới ngoài field tham chiếu id đã quy định trong §4.5.

## Dependency

11a có thể làm bất cứ lúc nào (là tài liệu, không phụ thuộc code), nhưng nên làm sau khi ít nhất Phase 2-9 đã ổn định để rà soát ngược có ý nghĩa. 11b phụ thuộc toàn bộ Phase 1, 2, 3, 4, 5, 8 (đúng nghĩa smoke test end-to-end, không thể chạy nếu 1 trong các phase đó chưa xong). 11c phụ thuộc 11b (dùng lại Experiment đã tạo) và cần xác nhận `services/commercial` đã có tool `lead.create` (nếu chưa, bổ sung tool đó trước — nằm ngoài phạm vi roadmap gốc, cần audit nhanh khi tới bước này).
