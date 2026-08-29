# Thiết kế tuân thủ AI và dữ liệu cá nhân cho COSA

**Ngày:** 2026-08-29

**Trạng thái:** Đã chốt thiết kế, chờ duyệt đặc tả trước khi lập kế hoạch triển khai

**Phạm vi:** COSA phục vụ doanh nghiệp tư nhân; AI chỉ hỗ trợ tư vấn và soạn thảo.
**Trách nhiệm cuối cùng:** Founder/chủ workspace; có thể ủy quyền người phụ trách kỹ thuật nhưng không chuyển trách nhiệm quyết định cuối cùng.

## 1. Mục tiêu và quyết định ràng buộc

Mục tiêu là đưa kiểm soát pháp lý, quản trị AI và bảo vệ dữ liệu vào luồng vận hành sẵn có của COSA, không tạo hệ thống tuân thủ tách rời và không đưa business truth vào model hay agent runtime.

Các quyết định đã được chốt:

- COSA chỉ phục vụ doanh nghiệp tư nhân. Không cung cấp dịch vụ công và không triển khai năng lực y tế, giáo dục, sinh trắc học, tuyển dụng, chấm điểm tín dụng, xét điều kiện hưởng quyền lợi, hay quyết định có tác động đáng kể tương tự.
- Kết quả tài chính, pháp lý, nhân sự và vận hành do AI tạo ra luôn là đề xuất, dự thảo hoặc phân tích tham khảo. Người có thẩm quyền của workspace đưa ra quyết định cuối cùng và xác nhận mọi tác động ra bên ngoài.
- Thiết kế mở rộng **services/company/finance-legal** và catalog pháp lý trong schema **legal**. **apps/cosa** chỉ nhận snapshot tuân thủ để kiểm soát lúc chạy; không trở thành nguồn dữ liệu pháp lý hay chủ sở hữu hồ sơ đánh giá.
- Không policy tùy biến theo workspace nào được phép nới lỏng rào cản bắt buộc: cấm quyết định tự động trong các miền loại trừ, yêu cầu xác nhận người dùng với hành động bên ngoài, và chặn gửi dữ liệu khi không có điều kiện xử lý hợp lệ.
- Hệ thống cũ không tự động được gắn nhãn “đã tuân thủ”. Mỗi triển khai phải có đánh giá, bằng chứng và phê duyệt còn hiệu lực.

## 2. Cơ sở pháp lý và cách áp dụng

Các nguồn người dùng cung cấp được ghi nhận trong catalog pháp lý theo URL gốc, hash nội dung, ngày hiệu lực và tầng áp dụng. Nội dung pháp lý được triển khai theo quy tắc có kiểm soát, không suy diễn nghĩa vụ từ văn bản định hướng.

| Nguồn | Vai trò trong COSA | Cách áp dụng |
| --- | --- | --- |
| Luật Trí tuệ nhân tạo 134/2025/QH15, hiệu lực 01-03-2026 | Luật đang có hiệu lực | Nguồn cho catalog hệ thống AI, giới hạn mục đích, minh bạch, trách nhiệm và đánh giá lại rủi ro. |
| Nghị định 142/2026/NĐ-CP | Quản lý AI theo rủi ro | Dùng cho workflow phân loại, đánh giá, quản lý vòng đời và sự cố. |
| Quyết định 33/2026/QĐ-TTg | Danh mục hệ thống AI rủi ro cao | Dùng làm basis phân loại. COSA hiện ghi nhận kết luận ngoài danh mục theo phạm vi đã chốt, nhưng phải đánh giá lại khi năng lực thay đổi. |
| Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 | Luật đang có hiệu lực | Dùng cho mục đích xử lý, quyền của chủ thể dữ liệu, lưu giữ, rút đồng ý và xử lý sự cố dữ liệu cá nhân. |
| Thông tư 05/2026/TT-BKHCN | Chuẩn đạo đức AI | Dùng làm checklist an toàn, minh bạch, kiểm soát của con người, riêng tư, công bằng, cơ chế phản ánh và khắc phục. |
| Quyết định 804/QĐ-TTg, 367/QĐ-TTg, 1528/QĐ-TTg và Nghị quyết 86/NQ-CP | Định hướng/chính sách hoặc nghĩa vụ theo bối cảnh riêng | Ghi ở tầng POLICY_WATCH trừ khi chuyên gia xác định nghĩa vụ trực tiếp cho deployment cụ thể. Không tự áp dụng như nghĩa vụ chung đối với nhà cung cấp COSA. |

Nguồn chính thức:

- [Luật Trí tuệ nhân tạo 134/2025/QH15](https://vanban.chinhphu.vn/?docid=216334&pageid=27160&typegroupid=3)
- [Nghị định 142/2026/NĐ-CP](https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/142-2026-ndcp.signed.pdf)
- [Quyết định 33/2026/QĐ-TTg](https://congbao.chinhphu.vn/van-ban/quyet-dinh-so-33-2026-qd-ttg-469951.htm)
- [Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15](https://vanban.chinhphu.vn/?classid=1&docid=214590&pageid=27160&typegroup=)
- [Thông tư 05/2026/TT-BKHCN](https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/3/05-bkhcn.pdf)

## 3. Hiện trạng liên quan

Các thành phần hiện hữu sẽ được kế thừa:

- **services/company/shared/db/schema/legal.ts** có catalog nguồn, phiên bản văn bản, rule áp dụng, nghĩa vụ và phê duyệt xác minh pháp nhân.
- **legal-applicability.service.ts** tạo nghĩa vụ từ nguồn pháp lý nhưng hiện chỉ đối chiếu cơ bản theo entity status; chưa có dữ liệu AI deployment, mục đích, nhà cung cấp hoặc loại dữ liệu.
- **apps/cosa/policies/snapshot.py** và **evaluator.py** có workspace/principal snapshot, rule tenant và emergency lock. Rule tenant hiện được xét trước hard-code, nên cần statutory floor đứng trước tenant override.
- Capability tài chính và gửi tin nhắn đã có mô hình phê duyệt. Ví dụ finance write và engagement message send yêu cầu phê duyệt cho hành động tác động cao.
- **apps/cosa/composition/model_provider.py** hiện cấu hình DeepSeek trực tiếp từ biến môi trường, chưa kiểm tra hồ sơ xử lý dữ liệu hoặc trạng thái phê duyệt nhà cung cấp trước khi gửi payload ra ngoài.
- **apps/cosa/observability/logging.py** che secret/token nhưng chưa có hợp đồng cấm ghi nội dung dữ liệu cá nhân hoặc bí mật kinh doanh vào log.
- Retention bộ nhớ agent có tồn tại nhưng chưa thống nhất với hội thoại, file, object storage và chỉ mục tri thức.

## 4. Kiến trúc đích

Luồng nguồn sự thật và kiểm soát:

1. Catalog pháp lý và bản ghi quản trị AI trong Company service.
2. Workspace AI deployment cùng assessment và evidence đã phê duyệt.
3. Compliance snapshot có hash, dùng khi bắt đầu/resume run.
4. Runtime COSA kiểm statutory floor, data-model gate, rồi policy/approval.
5. Capability/model adapter thực thi hoặc chặn; audit chỉ lưu metadata.

Company service là nguồn sự thật về triển khai, đánh giá, bằng chứng, sự cố và hồ sơ xử lý. COSA chỉ tiêu thụ snapshot phiên bản hóa tại lúc bắt đầu hoặc tiếp tục run, rồi tái quan sát cờ dừng khẩn cấp trước cổng quan trọng. Snapshot hỗ trợ truy vết và replay, nhưng không biến một phê duyệt cũ thành quyền tiếp tục chạy sau khi đã tạm dừng.

### 4.1. Bảng mới trong schema legal

Các migration mới thêm thực thể sau. Mọi bản ghi theo workspace phải có workspace id, audit fields chuẩn và truy vấn dịch vụ luôn scope tenant.

| Bảng | Mục đích | Trường thiết yếu |
| --- | --- | --- |
| ai_system_catalog | Danh mục nền tảng các hệ thống/agent COSA | system key, tên, mục đích được phép/bị cấm, chủ sở hữu kỹ thuật, trạng thái vòng đời. |
| ai_system_versions | Cố định nội dung phiên bản có thể đánh giá | catalog id, version, hash cấu hình agent/capability, model profile ref, ngày phát hành/ngừng dùng. |
| workspace_ai_deployments | Một workspace bật một phiên bản hệ thống | workspace id, system version, mode bắt buộc ADVISORY_ONLY, Founder chịu trách nhiệm, technical owner, trạng thái. |
| ai_system_capability_bindings | Khai báo tác động từng capability theo phiên bản | capability id, lớp READ/DRAFT/EXTERNAL, miền quyết định, có cần xác nhận người dùng hay không. |
| ai_risk_assessments | Đánh giá rủi ro và kết luận áp dụng | deployment id, OUT_OF_CATALOG/REQUIRES_REVIEW/HIGH_RISK, mục đích, đối tượng ảnh hưởng, kiểm soát, reviewer. |
| ai_compliance_evidence | Bằng chứng không thể thay thế âm thầm | assessment id, loại evidence, URI/ref, hash, ngày kiểm tra, reviewer. Không lưu nội dung dữ liệu cá nhân. |
| ai_provider_profiles | Hồ sơ nhà cung cấp/model dùng chung | provider/model key, trạng thái, khu vực xử lý khai báo, DPA/contract ref, nhóm dữ liệu được phép, ngày rà soát. Secret vẫn chỉ ở secret manager/biến runtime. |
| ai_data_processing_profiles | Ràng buộc dữ liệu của deployment/capability | deployment/binding id, purpose id, nhóm dữ liệu, recipient/provider profile, retention policy, điều kiện chuyển dữ liệu, trạng thái. |
| data_processing_authorizations | Bằng chứng đồng ý/cơ sở xử lý theo mục đích | workspace id, subject ref đã giả danh, purpose/version, authority type, proof ref/hash, trạng thái grant/withdraw/restrict. |
| data_subject_requests | Xử lý quyền của chủ thể dữ liệu | subject ref, request type, deadline, trạng thái, kết quả, lý do ngoại lệ lưu giữ nếu có. |
| ai_incidents và ai_incident_actions | Sự cố, cô lập, quyết định thông báo, khắc phục | deployment id, thời điểm phát hiện, phạm vi/nhóm dữ liệu, severity, trạng thái, deadline rule, action/evidence refs. |
| ai_compliance_snapshots | Bản chụp đầu vào của run | deployment/assessment/provider/data profile version, legal-source versions, policy hash, hash riêng và thời điểm cấp. |

Các bảng không lưu prompt, tài liệu gốc, số giấy tờ, nội dung hội thoại hay giá trị nhạy cảm làm evidence. Chúng chỉ lưu định danh nội bộ, URI có phân quyền, hash, category và metadata cần thiết để chứng minh kiểm soát.

### 4.2. Trạng thái và phê duyệt

Trạng thái deployment chỉ cho phép chuyển theo chuỗi:

**DRAFT → ASSESSED → APPROVED_FOR_USE → SUSPENDED → RETIRED**

Từ ASSESSED có thể chuyển REJECTED. REJECTED và RETIRED không được tenant policy tự kích hoạt lại.

- DRAFT: đã đăng ký nhưng không xử lý dữ liệu thật hay gọi model thật.
- ASSESSED: có assessment/evidence nhưng chưa được Founder phê duyệt.
- APPROVED_FOR_USE: assessment, provider profile và data-processing profile còn hiệu lực; là trạng thái duy nhất runtime được phép.
- SUSPENDED: chặn run mới, resume, model call và external capability. Chỉ người có thẩm quyền khôi phục sau quyết định có evidence.
- REJECTED/RETIRED: chỉ lưu lịch sử/audit.

Phê duyệt gắn đúng deployment version, assessment version, snapshot hash, người đề nghị, người quyết định, thời hạn và lý do. Không dùng chuỗi approval tự do hay một approval chung cho nhiều action.

### 4.3. Mở rộng catalog pháp lý

Nguồn và version mới được seed vào regulation sources và regulation versions. Rule predicate được nâng cấp từ check entity status đơn giản thành input có kiểu gồm:

- loại khách hàng là doanh nghiệp tư nhân;
- deployment mode, intended purpose và prohibited purpose;
- capability effect class và decision domain;
- data category, provider profile và trạng thái xử lý;
- risk classification và ngày đánh giá lại.

CURRENT_LAW có thể tạo control bắt buộc hoặc block. POLICY_WATCH chỉ hiển thị cảnh báo/rà soát, không block độc lập. PROFESSIONAL_REVIEW tạo yêu cầu review của người có thẩm quyền, không để model tự xác nhận nghĩa vụ.

## 5. Runtime controls

### 5.1. Snapshot và thứ tự kiểm soát

Khi bắt đầu hoặc resume agent run, COSA lấy compliance snapshot từ Company service và persist tối thiểu deployment id, assessment id, compliance snapshot hash, provider/data profile version, model id/version và policy snapshot hash vào context/audit của run.

Trước model call hoặc capability tác động, runtime kiểm tra theo thứ tự:

1. Xác thực workspace/principal và tenant isolation hiện có.
2. Tái quan sát deployment status và emergency suspension. Thiếu snapshot, trạng thái khác APPROVED_FOR_USE hoặc lỗi tra cứu đều từ chối an toàn.
3. Áp dụng **statutory floor**: từ chối mục đích cấm, autonomous decision, capability không khai báo, action external không human confirmation và mọi use case cần review/rủi ro cao ngoài scope COSA.
4. Chạy data-model gate trước khi dựng payload cho provider.
5. Áp dụng policy workspace, quota và requirement approval. Các rule này chỉ có thể siết chặt statutory floor.
6. Thực thi capability qua approval đã bind action/checkpoint; ghi event cấu trúc gồm ID, version/hash, decision và reason code.

CosaPolicyEngine đổi thứ tự để statutory floor được đánh giá trước PolicySnapshot match. Một rule tenant ALLOW không thể vượt qua cổng này.

### 5.2. Capability contract

Mỗi capability trong một deployment phải có binding versioned với:

- effect class: READ, DRAFT hoặc EXTERNAL;
- decision domain: GENERAL, LEGAL, FINANCE, HR hoặc domain khác;
- requires human confirmation;
- may send to model và data category maximum;
- action/recipient scope nếu có tác động bên ngoài.

Binding thiếu, mismatch với runtime registry, hoặc capability mới chưa được đánh giá đều DENY với reason code. Capability DRAFT không được xác nhận giao dịch, nộp hồ sơ, gửi thông báo pháp lý, quyết định tuyển dụng hay kích hoạt action có hệ quả bên ngoài. Capability EXTERNAL tiếp tục dùng approval gateway hiện có, nhưng approval được bổ sung compliance context.

### 5.3. Audit và quan sát

Mỗi kết quả cổng ghi event structured với run/workspace/deployment ID, capability/model ID, snapshot hashes, outcome, reason code, approver ID và timestamp. Không log prompt, completion, evidence content hoặc payload nguồn.

Logging chuyển từ chỉ che API key sang hợp đồng allowlist metadata: log application không nhận raw model input/output theo default. Một redactor phòng thủ bổ sung chỉ là lớp dự phòng, không phải căn cứ cho phép ghi dữ liệu nhạy cảm.

## 6. Dữ liệu cá nhân, bí mật kinh doanh và nhà cung cấp model

### 6.1. Data-model gate

Trước khi dựng request cho LitellmModel hoặc provider khác, một cổng dữ liệu thực hiện:

1. Nhận classification chủ yếu từ metadata nguồn, capability binding và hồ sơ xử lý; scanner mẫu chỉ là lớp cảnh báo hỗ trợ, không phải cơ chế phân loại pháp lý duy nhất.
2. Kiểm tra purpose, authorization/cơ sở xử lý, restriction/withdraw và retention/legal hold.
3. Kiểm tra provider/model chính xác có trong provider profile và được data-processing profile cho phép với data category đó.
4. Tạo bản sao tối thiểu đã redaction/tokenization theo profile. Văn bản gốc ở kho nội bộ phân quyền; cổng không phát sinh raw payload trong log/audit.
5. Nếu bất kỳ check nào lỗi hoặc thiếu, trả DENY và không gọi network provider.

DeepSeek chuyển từ đường cấu hình trực tiếp thành provider adapter có provider profile do runtime cấp. API key vẫn đọc từ secret config tại composition root, nhưng profile/phiên bản/quyền xử lý do Company service quyết định. Default an toàn: DeepSeek chỉ nhận nội dung được phân loại không cá nhân, không nhạy cảm và không bí mật kinh doanh cho đến khi Founder phê duyệt provider profile và deployment phù hợp.

### 6.2. Đồng ý, quyền dữ liệu và retention

Authorization được ghi theo purpose/version, subject reference giả danh và proof reference. Rút đồng ý hoặc hạn chế xử lý có hiệu lực cho xử lý tương lai ngay khi record đổi trạng thái; cổng dữ liệu chặn provider call kế tiếp.

Data subject request quản lý access, correction, deletion và restriction. Xóa không âm thầm: retention service xác định object, memory, conversation artifact và retrieval index; thực hiện deletion hoặc giữ lại do legal hold/nghĩa vụ lưu trữ; sau đó ghi tombstone/evidence không chứa nội dung gốc.

Một lifecycle coordinator áp dụng chính sách retention chung lên:

- conversation/run artifacts;
- agent memory;
- file/object storage và bản chuyển đổi tài liệu;
- knowledge index/vector/retrieval references;
- metadata audit tối thiểu theo thời hạn riêng.

## 7. Trải nghiệm, trách nhiệm và sự cố

### 7.1. Compliance Center

Mở rộng khu vực pháp lý hiện có bằng Compliance Center theo workspace. Founder xem và điều khiển:

- deployment, mục đích, người chịu trách nhiệm và trạng thái;
- assessment, evidence, legal sources và thời điểm đánh giá lại;
- provider/data-processing profile, hạn lưu trữ và authorization summaries;
- queue phê duyệt, exception có ngày hết hạn và action khắc phục;
- sự cố, deadline áp dụng và quyết định thông báo.

Trang không hiển thị dữ liệu gốc chỉ để tiện audit. Thao tác Founder gồm approve deployment, suspend/resume, approve provider/data profile, quyết định exception có hạn, approve corrective action và close incident. Mỗi thao tác yêu cầu lý do và tạo audit record.

### 7.2. Minh bạch trong trải nghiệm AI

Chat, AI Legal Contract Auditor và các bề mặt pháp lý/tài chính phải hiển thị:

- nội dung do AI hỗ trợ, chỉ có tính tham khảo và không thay thế quyết định của người có thẩm quyền/chuyên gia;
- nguồn, layer, giả định, giới hạn và confidence của câu trả lời;
- cảnh báo trước khi gửi tài liệu có dữ liệu cá nhân, tài chính hoặc bí mật kinh doanh;
- cách báo lỗi/khiếu nại và yêu cầu rà soát con người.

Giao diện thay cách diễn đạt “an toàn” tuyệt đối hoặc điểm an toàn chung bằng kết quả có nguồn, phạm vi, giới hạn và trạng thái review. Confidence không được dùng để tự động quyết định thay con người.

### 7.3. Sự cố và phản ánh

Sự cố có vòng đời: OPEN → CONTAINED → ASSESSING → NOTIFICATION_DECISION_PENDING → REMEDIATING → CLOSED.

Incident lưu phạm vi, deployment, category dữ liệu, thời điểm phát hiện, action cô lập, deadline rule, quyết định của người có thẩm quyền và evidence khắc phục — không lưu payload nhạy cảm.

Khi điều kiện pháp lý có thể phát sinh nghĩa vụ thông báo, hệ thống hiển thị deadline cấu hình từ rule và nhắc Founder. COSA không tự gửi thông báo tới cơ quan hoặc chủ thể dữ liệu; Founder/người được ủy quyền quyết định và lưu evidence thực hiện. Kênh phản ánh của người dùng tạo ticket có tracking và không tự đóng chỉ vì model đưa ra câu trả lời.

## 8. API và ranh giới dịch vụ

Company service sở hữu các service nội bộ sau. Tên HTTP route không phải là contract của thiết kế này; kế hoạch triển khai sẽ đặt tên theo convention endpoint hiện hữu của Company service, còn ownership và input/output ở dưới là bất biến:

- đăng ký/version hệ thống AI và workspace deployment;
- tạo, submit, review assessment và evidence;
- resolve ComplianceSnapshot cho run, capability hoặc model call;
- kiểm tra data-model authorization theo purpose/provider/category;
- quản lý provider profile, data subject request, retention action và incident;
- trả Compliance Center view đã scope workspace.

COSA chỉ gọi API nội bộ đã xác thực và không ghi chéo database workspace. Nếu Company service không khả dụng, cache snapshot hết hiệu lực hoặc response không xác thực, runtime từ chối model/external action thay vì fallback sang ALLOW.

## 9. Chuyển đổi theo giai đoạn

### Giai đoạn A — nền tảng và nguồn pháp lý

1. Migration cho schema, index, constraint trạng thái và audit fields.
2. Seed nguồn, version và template/rule AI từ nguồn chính thức; phân tầng CURRENT_LAW và POLICY_WATCH rõ ràng.
3. Đăng ký catalog các agent/capability hiện hữu ở trạng thái DRAFT.

### Giai đoạn B — assessment và statutory floor

1. Tạo assessment/evidence cho từng deployment đang dùng; không backdate hoặc ngầm suy diễn evidence.
2. Thêm snapshot resolver, status gate và statutory floor trước tenant policy.
3. Bind capability hiện hữu; binding chưa có dẫn đến fail-closed cho production path được bảo vệ.

### Giai đoạn C — data-model gate và retention

1. Provider profile/approved model adapter thay DeepSeek direct path.
2. Thêm redaction/minimization, authorization check và quy tắc log metadata.
3. Hợp nhất lifecycle và thực thi quyền dữ liệu trên memory, artifact, file và knowledge index.

### Giai đoạn D — trải nghiệm và vận hành

1. Compliance Center, approval/exception queue và incident workflow.
2. Disclosure, legal/finance advisory envelope và report-a-problem trên UI.
3. Dashboard trạng thái, deadline alert và runbook cho Founder/technical owner.

Dev/test chỉ dùng fake provider hoặc dữ liệu giả khi deployment chưa phê duyệt. Production không dùng bypass cờ cấu hình để bỏ qua gate với dữ liệu thật.

## 10. Kiểm thử và tiêu chí hoàn thành

### Kiểm thử bắt buộc

- Migration trên database trống và kiểm tra constraint/status transition.
- Unit/service test: legal source, predicate AI, assessment approval, expiry, tenant isolation, provider profile và incident state machine.
- Runtime integration: snapshot thiếu/hết hạn/suspended bị chặn; tenant ALLOW không vượt statutory floor; approval bind đúng run/capability.
- Data gate: rút authorization chặn network call kế tiếp; provider chưa duyệt không được gọi; payload nhạy cảm bị chặn hoặc giảm thiểu theo profile.
- Observability: log/audit không chứa raw prompt, completion, file text hoặc thông tin định danh giả định trong fixture.
- Retention: hết hạn xóa object + conversion + memory + index liên quan; legal hold giữ đúng phần cần giữ và tạo evidence.
- UI/E2E: disclosure hiển thị, external action yêu cầu xác nhận, Founder suspend deployment được và incident mở tạo nhắc việc đúng trạng thái.
- Process-level smoke: run với provider fake chứng minh Company snapshot → COSA gate → capability/model adapter → audit metadata.

### Definition of done

Một deployment chỉ được coi là sẵn sàng dùng khi đồng thời có:

1. owner và technical owner;
2. mục đích được phép, mode ADVISORY_ONLY và capability binding đầy đủ;
3. assessment đã phê duyệt, evidence còn hiệu lực và nguồn luật/version rõ ràng;
4. provider/data-processing/retention profile hợp lệ;
5. disclosure, human approval và incident/complaint route hoạt động;
6. test mục tiêu và smoke đường thực thi xanh;
7. snapshot/audit chứng minh runtime đã áp dụng đúng control.

## 11. Ngoài phạm vi

- Cung cấp dịch vụ AI cho cơ quan nhà nước hoặc xử lý dữ liệu nhà nước.
- Tự động đưa ra/thực thi quyết định tín dụng, tuyển dụng, y tế, giáo dục, sinh trắc học, quyền lợi hoặc quyết định tác động đáng kể đến cá nhân.
- Tự động gửi thông báo pháp lý/sự cố ra bên ngoài.
- Lưu prompt/completion/tài liệu thô trong audit log để tiện debug.
- Tuyên bố COSA đáp ứng toàn bộ nghĩa vụ pháp lý chỉ bằng việc triển khai mã; việc áp dụng thực tế phải được Founder và, khi cần, chuyên gia pháp lý đánh giá.
