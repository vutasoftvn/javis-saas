---
name: research-patent-intelligence
description: Tình báo sáng chế, rà soát giải pháp kỹ thuật có trước (Prior Art), phân tích tự do triển khai (Freedom-to-Operate - FTO) và bản đồ sáng chế công nghệ theo phân loại CPC, kèm tuyên bố miễn trừ tư vấn pháp lý.
---

# Tình Báo Sáng Chế & Tự Do Triển Khai Kỹ Thuật (Patent Prior-Art & FTO Intelligence)

## 1. Mục Tiêu (Objective)
Cung cấp phân tích kỹ thuật về tình báo bằng sáng chế (Patent Intelligence) nhằm hỗ trợ các kỹ sư và nhà sáng lập đánh giá tính mới của giải pháp (Novelty), kiểm tra rủi ro vi phạm bằng sáng chế đang có hiệu lực (Freedom-to-Operate - FTO), và phân tích cảnh quan cạnh tranh công nghệ theo hệ thống phân loại sáng chế hợp tác (Cooperative Patent Classification - CPC).

> [!IMPORTANT]
> **Tuyên Bố Miễn Trừ Trách Nhiệm Pháp Lý Bắt Buộc (Mandatory Legal Disclaimer):**
> Kỹ năng này cung cấp **TÍN HIỆU PHÂN TÍCH KỸ THUẬT (Technical Assessment Signal)**, tuyệt đối **KHÔNG PHẢI Ý KIẾN TƯ VẤN PHÁP LÝ (Not Legal Advice)**. Kết quả rà soát nhằm giúp đội ngũ kỹ thuật tối ưu hóa giải pháp và chuẩn bị tài liệu. Doanh nghiệp **bắt buộc phải tham vấn Luật sư Sáng chế / Đại diện Sở hữu Trí tuệ có chứng chỉ hành nghề** trước khi nộp đơn đăng ký hoặc đưa sản phẩm ra thị trường.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Khi phát triển một thuật toán, kiến trúc hệ thống hoặc cơ chế xử lý dữ liệu mới và cần kiểm tra xem giải pháp tương tự đã được đăng ký hay chưa.
  - Khi cần rà soát rủi ro vi phạm sáng chế của đối thủ trước khi thương mại hóa một tính năng phần mềm quan trọng (FTO).
  - Khi lập bản đồ sáng chế ngành để tìm ra các "khoảng trống công nghệ" chưa ai đăng ký bảo hộ.
- **Khi nào KHÔNG dùng**:
  - Khi cần tra cứu nhãn hiệu, logo, tên thương hiệu (Trademark $\rightarrow$ Out of Scope).
  - Khi cần bảo hộ bản quyền phần mềm hoặc bí mật kinh doanh (Copyright/Trade Secret $\rightarrow$ Out of Scope).
  - Khi chỉ cần tra cứu tài liệu học thuật không phải văn bằng sáng chế (dùng `research.deep-research`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
1. **Mô tả kỹ thuật chính xác**: Mô tả 2-3 câu về cơ chế hoạt động, giải pháp kỹ thuật cụ thể và điểm khác biệt cốt lõi (từ chối mô tả chung chung như "hệ thống AI tối ưu").
2. **Xác định mục tiêu rà soát cụ thể**: Chọn 1 trong 5 nhánh ứng dụng (Novelty, FTO, Competitive Landscape, M&A Diligence, hoặc Invalidation).

## 4. Các Bước Tất Định (Deterministic Steps)

```
┌────────────────────────────────────────────────────────┐
│ 1. XÁC ĐỊNH MỤC TIÊU RÀ SOÁT (SUB-USE-CASE SELECTION)  │
│    • Novelty Search          • Freedom-to-Operate (FTO)│
│    • Competitive Landscape   • Litigation / M&A        │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 2. CHIẾT XUẤT TỪ KHÓA & MÃ PHÂN LOẠI CPC               │
│    • G06F (Xử lý dữ liệu số) • G06N (Mạng nơ-ron AI)   │
│    • H04L (Truyền thông mạng và bảo mật)               │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 3. TRUY VẤN DỮ LIỆU SÁNG CHẾ CÔNG KHAI                 │
│    • Google Patents, USPTO, Espacenet, Cục SHTT (VN)   │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 4. PHÂN TÍCH ĐỐI CHIẾU YÊU CẦU BẢO HỘ (CLAIMS ANALYSIS)│
│    • So sánh yêu cầu bảo hộ độc lập (Independent Claims│
│    • Đánh giá mức độ trùng lặp kỹ thuật                │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 5. XUẤT BÁO CÁO KÈM TUYÊN BỐ MIỄN TRỪ PHÁP LÝ          │
└────────────────────────────────────────────────────────┘
```

1. **Xác Định Nhánh Ứng Dụng Rà Soát (Sub-Use-Case)**:
   - *Novelty*: Tập trung tìm kiếm các giải pháp kỹ thuật đã công bố trước ngày ưu tiên, không phân biệt bằng sáng chế còn hiệu lực hay đã hết hạn.
   - *Freedom-to-Operate (FTO)*: Chỉ tập trung vào các bằng sáng chế **đang còn hiệu lực** tại các vùng lãnh thổ mục tiêu (Mỹ, EU, Việt Nam,...).
   - *Competitive Landscape*: Khảo sát số lượng văn bằng của các đối thủ chính theo mã phân loại công nghệ.
2. **Chiết Xuất Khái Niệm & Mã CPC (Classification Mapping)**:
   - Xác định mã phân loại quốc tế tương ứng: ví dụ G06N (Mô hình tính toán dựa trên sinh học / Trí tuệ nhân tạo), G06F (Xử lý dữ liệu điện toán), H04L (Bảo mật mạng và truyền thông tin).
3. **Truy Vấn Dữ Liệu Sáng Chế Đa Nguồn**:
   - Sử dụng `web.search` trên cổng Google Patents (`patents.google.com`), USPTO, Espacenet và WIPO Patentscope.
   - Trích xuất số hiệu văn bằng, ngày nộp đơn, ngày cấp, chủ đơn (*Assignee*), và trạng thái hiệu lực (*Active, Expired, Abandoned*).
4. **Phân Tích Đối Chiếu Yêu Cầu Bảo Hộ (Claims Extraction)**:
   - Trích dẫn trực tiếp nội dung Yêu cầu bảo hộ độc lập (Independent Claim 1) của các sáng chế gần nhất.
   - Chỉ ra điểm tương đồng và các điểm khác biệt kỹ thuật mà giải pháp mới có thể thiết lập tính mới.
5. **Đóng Gói Báo Cáo & Khuyến Nghị Tránh Vi Phạm (Design-Around Strategy)**:
   - Nếu phát hiện rủi ro FTO cao, đề xuất hướng thiết kế né tránh (*design-around*) thay đổi cấu trúc hoặc luồng xử lý dữ liệu.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `web.search`: Tra cứu cơ sở dữ liệu sáng chế công khai (Google Patents, Espacenet, USPTO).

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- **Số hiệu văn bằng chính xác**: Mọi sáng chế được nêu phải có số hiệu đăng ký chuẩn (ví dụ: `US11456789B2`, `EP3456789A1`) và liên kết URL trực tiếp.
- **Trích dẫn Claim nguyên văn**: Bắt buộc trích dẫn nguyên văn câu văn yêu cầu bảo hộ khi đánh giá rủi ro FTO.
- **Tuyên bố pháp lý hiện diện**: Bắt buộc có khối Disclaimer ở đầu và cuối báo cáo.

## 7. Safe Fallback
- Khi cơ sở dữ liệu sáng chế quốc tế không thể truy cập trực tiếp, agent khuyến nghị người dùng xuất danh sách các từ khóa kỹ thuật và mã CPC để tra cứu trên cổng WIPO Patentscope nội địa.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Báo Cáo Tình Báo Sáng Chế & Tự Do Triển Khai (Patent Intelligence Brief)

> **CẢNH BÁO PHÁP LÝ:** Báo cáo này là tài liệu phân tích kỹ thuật của đội ngũ R&D, KHÔNG PHẢI ý kiến tư vấn pháp lý. Tham vấn luật sư sáng chế trước khi nộp đơn hoặc thương mại hóa.

## 1. Tóm Tắt Đánh Giá (Executive Verdict)
- **Tên giải pháp / Tính năng**: [Tên công nghệ được rà soát]
- **Mục tiêu rà soát**: [Novelty Search / Freedom-to-Operate (FTO) / Competitive Landscape]
- **Mã phân loại công nghệ chính (CPC)**: [G06N 3/08, G06F 16/90...]
- **KẾT LUẬN RỦI RO KỸ THUẬT**: **[RỦI RO THẤP / RỦI RO TRUNG BÌNH / CÓ BẰNG CHỨNG TRÙNG LẶP CAO]**

## 2. Các Sáng Chế Có Giải Pháp Kỹ Thuật Gần Nhất (Closest Prior Art)
### 2.1 [US11234567B2] - [Tiêu đề bằng sáng chế]
- **Chủ đơn (Assignee)**: [Tên tập đoàn/công ty đối thủ] | **Ngày cấp**: [YYYY-MM-DD] | **Trạng thái**: [Active / Còn hiệu lực]
- **URL**: [https://patents.google.com/patent/US11234567B2/en]
- **Yêu cầu bảo hộ độc lập (Claim 1 trích dẫn)**:
  > "[Trích dẫn nguyên văn nội dung Claim 1]"
- **Đối chiếu kỹ thuật**:
  - *Điểm tương đồng*: [Tính năng X xử lý tương tự]
  - *Điểm khác biệt của chúng ta*: [Giải pháp của chúng ta sử dụng cơ chế Y hoàn toàn khác]

## 3. Bản Đồ Cạnh Tranh Theo Phân Loại CPC (Landscape Trends)
- **Các đơn vị nộp đơn nhiều nhất trong phân khúc**: [Tập đoàn A (XX bằng), Công ty B (XX bằng)]
- **Khoảng trống công nghệ chưa có bảo hộ**: [Vùng giải pháp kỹ thuật chưa có bằng sáng chế kiểm soát]

## 4. Đề Xuất Chiến Lược Né Tránh (Design-Around Recommendations)
1. **Khuyến nghị 1**: Thay đổi phương thức lưu trữ bộ nhớ đệm từ client-side sang serverless cache để tránh Claim 3 của bằng US11234567B2.
2. **Khuyến nghị 2**: Tham vấn đại diện sở hữu trí tuệ để nộp đơn Provisional Patent cho cơ chế định tuyến dữ liệu mới.

---
**Khối Kiểm Toán Truy Vấn (Three-Count Audit):**
- Queries Sent: XX | Patents Received: XX | Patents Cited: XX
```

## 9. Xử Lý Lỗi & Phòng Vệ An Toàn (Security & Edge Cases)
- **Từ chối Trademark / Copyright**: Nếu người dùng yêu cầu kiểm tra tên thương hiệu hoặc logo, agent từ chối và giải thích rõ phạm vi của bằng sáng chế kỹ thuật.
- **Rào cản thẩm quyền lãnh thổ**: Lưu ý người dùng rằng bằng sáng chế có tính lãnh thổ (bằng cấp tại Mỹ không tự động có hiệu lực tại Việt Nam trừ khi có đơn theo Hiệp ước Hợp tác Sáng chế PCT).

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: alirezarezvani/claude-skills
  commit: 19392f7a08264ed00486a251f5b2098321771f94
  skill: research/skills/patent
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - 5 nhánh ứng dụng rà soát sáng chế (Novelty, FTO, Landscape, M&A, Invalidation)
    - Tuyên bố miễn trừ tư vấn pháp lý nghiêm ngặt
    - Quy tắc trích dẫn nguyên văn Independent Claims
    - Phân loại mã công nghệ CPC
  changed:
    - Bản địa hóa sang tiếng Việt và cấu trúc 10 mục chuẩn COSA
    - Đóng gói thành skillpack research.patent-intelligence
  added:
    - Chiến lược thiết kế né tránh vi phạm (Design-around recommendations)
    - Đối chiếu quy định pháp luật sở hữu trí tuệ lãnh thổ
  excluded:
    - Script Node.js docx template phụ thuộc bên ngoài
```
