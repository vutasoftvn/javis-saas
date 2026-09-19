---
name: ai-ai-product-craft
description: Thiết kế sản phẩm AI thực chiến theo chuẩn AI-Shaped, Context Engineering (ngăn context rot qua chu trình Research-Plan-Reset-Implement), 5 loại PoL Probes và cẩm nang xử lý Hallucination / Latency.
---

# AI Product Craft & Context Engineering

## 1. Mục đích & Giới hạn Quyền hạn
Cung cấp khung phương pháp luận chuyên sâu cho Product Manager và kỹ sư khi xây dựng các tính năng ứng dụng Trí tuệ Nhân tạo (GenAI / Agents) trên nền tảng COSA:
- Chuyển đổi tư duy từ **AI-First** (dùng AI để tự động hóa tác vụ sẵn có) sang **AI-Shaped** (tái cấu trúc cách thức công việc được hoàn thành để tạo hào phòng thủ cạnh tranh).
- Chuẩn hóa kiến trúc ngữ cảnh (**Context Engineering**), chống nhồi nhét ngữ cảnh (**Context Stuffing**) và triệt tiêu thoái hóa ngữ cảnh (**Context Rot**).
- Thiết kế thử nghiệm kiểm chứng sự sống (**Proof of Life - PoL Probes**) với chi phí thấp nhất để thu về sự thật trần trụi nhất.

> **Quy tắc an toàn & Quản trị vòng đời:**
> Skillpack này CHỈ đưa ra kiến trúc, đánh giá và đề xuất thiết kế thử nghiệm (L1_PROPOSE). Quyết định đưa mô hình vào phục vụ người dùng cuối hoặc thay đổi ngân sách inference thuộc thẩm quyền của Founder / Tech Lead con người.

## 2. Triggers
- Kích hoạt khi lập kế hoạch, đặc tả hoặc đánh giá một tính năng/sản phẩm mới có sử dụng LLM hoặc Agentic Workflow.
- Kích hoạt khi gặp sự cố về chất lượng AI trong sản phẩm: ảo giác (Hallucination), độ trễ cao (Latency), hoặc đầu ra bất định (Inconsistency).
- Kích hoạt khi chi phí token tăng vọt hoặc context window bị quá tải làm giảm độ chính xác.

## 3. Anti-triggers & 10 AI Product Anti-Patterns
- **Chặn Prompt-and-Pray:** Cấm phát hành tính năng AI với prompt viết đại, không có khung đánh giá (Evals) và không đo lường tỷ lệ lỗi trên mẫu thực tế.
- **Chặn Context Stuffing:** Cấm nhét toàn bộ cơ sở dữ liệu vào prompt với suy nghĩ "càng nhiều token càng thông minh". Hiệu ứng Lost in the Middle sẽ làm suy giảm nghiêm trọng độ chính xác.
- **Chặn Bỏ Qua Reset (Skipping the Reset):** Không bao giờ giữ nguyên context rác sau pha nghiên cứu để bước vào pha lập trình. Phải thực thi chu trình: Research ➔ Plan ➔ Reset ➔ Implement.
- **Chặn Testing Multiple Variables:** Mỗi thử nghiệm PoL probe chỉ được kiểm chứng 1 biến số duy nhất. Không kiểm chứng đồng thời UX + Prompt + Định giá trong 1 probe.
- Không kích hoạt khi thiếu `workspace_id` hoặc `project_id`.

## 4. Required Context
- `workspace_id`: Định danh workspace bắt buộc.
- `project_id`: Định danh dự án bắt buộc.
- `problem_hypothesis`: Giả định bài toán khách hàng cần giải quyết bằng AI.

## 5. Evidence Rules & Giao Thức Phản Chứng (Falsification Protocol)
Đối với mọi quyết định đưa thêm dữ liệu hoặc tính năng AI vào hệ thống, bắt buộc phải hoàn thành câu phản chứng:
> *"Nếu chúng ta loại bỏ [context/tính năng/bài test này], thì [hậu quả cụ thể nào] sẽ chắc chắn xảy ra trong [kịch bản cụ thể nào]?"*
- Nếu không thể hoàn thành câu trên bằng một hậu quả cụ thể và đo lường được, dứt khoát LOẠI BỎ thành phần đó khỏi prompt/context.

## 6. Khung Năng Lực & Quy Trình Vận Hành

### 6.1. Năm Năng Lực Cốt Lõi Của Tổ Chức AI-Shaped
1. **Context Design (Nền tảng):** Xây dựng tầng thực tại bền vững mà cả con người và AI đều tin cậy. Coi sự chú ý của AI là tài nguyên khan hiếm.
2. **Agent Orchestration:** Luồng tác vụ lặp lại, có thể truy vết: `Research ➔ Synthesis ➔ Critique ➔ Decision ➔ Log Rationale`.
3. **Outcome Acceleration:** Nén ngắn chu kỳ học hỏi (PoL probe trong vài ngày, không phải vài tuần).
4. **Team-AI Facilitation:** Coi đầu ra của AI là bản nháp, con người nắm quyền phê duyệt, văn hóa an toàn tâm lý để phản biện AI.
5. **Strategic Differentiation:** Tạo ra năng lực giải quyết vấn đề mà đối thủ không thể sao chép chỉ bằng cách tuyển thêm nhân sự.

### 6.2. Context Engineering vs Context Stuffing
Áp dụng 5 câu hỏi chẩn đoán ngữ cảnh:
1. *Ngữ cảnh này trực tiếp hỗ trợ cho quyết định cụ thể nào?* (Không trả lời được = Loại bỏ).
2. *Truy xuất (Retrieval) có thể thay thế việc duy trì liên tục (Persistence) không?* (Ưu tiên Just-In-Time qua RAG/Tools).
3. *Ai là người sở hữu ranh giới ngữ cảnh?* (Không có chủ sở hữu = Ngữ cảnh sẽ phình vô tội vạ).
4. *Hệ thống sẽ gãy đổ như thế nào nếu loại bỏ ngữ cảnh này?*
5. *Chúng ta đang cải thiện kiến trúc thông tin hay đang dùng token để che đậy sự lộn xộn?*

**Quy tắc Chu trình Ngăn Chặn Thoái Hóa Ngữ Cảnh (Context Rot):**
```
1. Research  : Thu thập dữ liệu, phân tích tài liệu (Context mở rộng và lộn xộn - chấp nhận).
2. Plan      : Cô đọng thành tài liệu kế hoạch SPEC.md / PLAN.md mật độ thông tin cao.
3. RESET     : Xóa sạch toàn bộ context window (Bắt buộc, không thương lượng).
4. Implement : Bắt đầu phiên thực thi mới chỉ với duy nhất bản SPEC/PLAN làm nguồn chân lý.
```

### 6.3. Năm Loại Thử Nghiệm Kiểm Chứng Sự Sống (PoL Probes)
| Loại Probe | Câu hỏi cốt lõi | Thời gian | Trường hợp ứng dụng |
|---|---|---|---|
| **1. Feasibility Check** | Chúng ta có thể dựng được bằng AI không? | 1-2 ngày | Chạy chuỗi prompt trên 100 mẫu thật, đo tỷ lệ lỗi và latency. |
| **2. Task-Focused Test** | Người dùng có hoàn thành tác vụ mượt mà không? | 2-5 ngày | Thử nghiệm giao diện do AI tạo ra, luồng chatbot, chất lượng gợi ý. |
| **3. Narrative Prototype** | Có thuyết phục được các bên liên quan không? | 1-3 ngày | Video Loom/demo tường thuật giả lập luồng AI trước khi code. |
| **4. Synthetic Simulation** | Mô phỏng được mà không gây rủi ro production? | 2-4 ngày | Chạy Monte Carlo trên dữ liệu tổng hợp để kiểm tra edge cases. |
| **5. Vibe-Coded Probe** | Tính năng có sống sót khi chạm người dùng thật? | 2-3 ngày | Ghép nối công cụ nhanh (Replit, Airtable, Webhook) để đo mức độ sử dụng. |

### 6.4. Xử Lý Sự Cố Chất Lượng AI Trong Sản Phẩm
- **Ảo giác (Hallucination):** Rút gọn context window về mức tối thiểu, bổ sung Grounding/Retrieval bắt buộc trích dẫn nguồn, thiết lập ngưỡng tin cậy (nếu điểm tự tin thấp -> trả lời "Tôi không biết").
- **Độ trễ cao (Latency):** Giảm token đầu vào (áp dụng Persist vs Retrieve), sử dụng streaming trả kết quả từng phần, cache các truy vấn phổ biến, định tuyến tác vụ dễ sang mô hình nhỏ hơn.
- **Bất định (Inconsistency):** Hạ temperature về 0.0 - 0.2 cho các tác vụ định dạng/sự thật, ép kiểu JSON Schema cứng, bổ sung 2-3 ví dụ mẫu (few-shot), ghim phiên bản model cố định.

## 7. Allowed Tool Calls
Không có tool call trực tiếp (Artifact & Proposal only).

## 8. Output Format
- **ai-product-spec**: Bản đặc tả tính năng AI đầy đủ: Giả định bài toán, Kiến trúc Context (Persist vs Retrieve), Kế hoạch PoL Probe (Pass/Fail/Learn thresholds), Chiến lược Evals và Phương án ứng phó lỗi.

## 9. Fallback & Handoff
- Khi không có dữ liệu thực tế để đo tỷ lệ lỗi, bắt buộc tạo Feasibility Probe kiểm thử trên tối thiểu 30-50 trường hợp mẫu trước khi đưa tính năng vào PRD chính thức.

## 10. Eval Notes
- Suite: `evals/ai/ai-product-craft.yaml`
