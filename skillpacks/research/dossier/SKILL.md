---
name: research-dossier
description: Hồ sơ thẩm định thực thể cấp độ ra quyết định (Decision-Grade Entity Dossier), kiểm chứng giả thuyết, kiểm soát tỷ lệ phản biện chống thiên vị xác nhận và tạo móc nối đối thoại đàm phán.
---

# Hồ Sơ Thẩm Định Thực Thể Chuyên Sâu (Decision-Grade Entity Dossier)

## 1. Mục Tiêu (Objective)
Cung cấp báo cáo thẩm định chuyên sâu về một đối tượng cụ thể (doanh nghiệp đối tác, khách hàng Enterprise lớn, quỹ đầu tư, đối thủ cạnh tranh chiến lược hoặc nhân sự chủ chốt). Kỹ năng này **từ chối việc tóm tắt thông tin tiểu sử chung chung kiểu Wikipedia**. Trọng tâm cốt lõi là **Kiểm chứng giả thuyết (Hypothesis-Testing Discipline)**: buộc người dùng phải nêu rõ giả định ban đầu, từ đó chủ động tìm kiếm các bằng chứng **bác bỏ (disprove)** với tỷ lệ tối thiểu $30\%$, nhận diện các dấu hiệu cảnh báo đỏ (*Red Flags*), và đề xuất các móc nối đối thoại (*Conversation Hooks*) thực chiến.

## 2. Khi Nào Dùng & Khi Nào Không Dùng (When to use & When NOT to use)
- **Khi nào dùng**:
  - Chuẩn bị cho cuộc gặp cấp cao, đàm phán hợp đồng thương mại lớn hoặc ký kết hợp tác chiến lược.
  - Thẩm định đối thủ cạnh tranh trực tiếp trước khi định vị sản phẩm mới.
  - Thẩm định năng lực và uy tín của nhà đầu tư (VC/Angel) trước khi nhận vốn.
  - Kiểm tra lý lịch và độ tin cậy đối tác công nghệ trọng yếu.
- **Khi nào KHÔNG dùng**:
  - Khi chỉ cần tra cứu nhanh tin tức báo chí sự kiện trong ngày (dùng `research.industry-trends`).
  - Khi cần tổng hợp lý thuyết học thuật hoặc giải pháp kỹ thuật chung (dùng `research.deep-research`).
  - Khi phân tích chỉ số tài chính nội bộ của chính công ty mình (dùng `finance.cfo-review`).

## 3. Điều Kiện Tiên Quyết (Prerequisites)
1. **Định danh thực thể rõ ràng**: Tên chính xác, website, mã số thuế hoặc link LinkedIn. Tuyệt đối từ chối xử lý tên quá chung chung khi chưa được phân biệt cụ thể.
2. **Giả thuyết bắt buộc (Mandatory Hypothesis)**: Người dùng bắt buộc phải nêu rõ giả định muốn kiểm chứng (Ví dụ: *"Tôi tin rằng công ty X đang tái cấu trúc và cắt giảm chi tiêu công nghệ ngoài luồng"*, hoặc *"Tôi cho rằng đối thủ Y sắp thâm nhập thị trường Đông Nam Á"*).

## 4. Các Bước Tất Định (Deterministic Steps)

```
┌────────────────────────────────────────────────────────┐
│ 1. INTAKE ÉP BUỘC GIẢ THUYẾT (HYPOTHESIS COMMITMENT)   │ -> Từ chối tóm tắt chung chung
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 2. LẬP KẾ HOẠCH TRUY VẤN HAI CHIỀU                     │
│    • 70% Truy vấn xác minh (Supporting)                │
│    • 30% Truy vấn phản biện đối lập (Antonym-Pivots)   │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 3. THU THẬP & PHÂN TẦNG NGUỒN TIN (SOURCE TIERING)     │
│    • Primary (Hồ sơ pháp lý, SEC, đăng ký KD)          │
│    • Secondary (Báo chí tài chính, tạp chí ngành)      │
│    • Tertiary (Review nhân viên, thảo luận diễn đàn)   │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 4. KIỂM SOÁT TỶ LỆ PHẢN BIỆN (ANTI-BIAS GATE)          │ -> DisconfirmingChecker >= 30%
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 5. TRÍCH XUẤT RED FLAGS & CONVERSATION HOOKS           │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ 6. XUẤT HỒ SƠ THẨM ĐỊNH KÈM THREE-COUNT AUDIT          │
└────────────────────────────────────────────────────────┘
```

1. **Intake Ép Buộc Khai Báo Giả Thuyết**:
   - Nếu người dùng không cung cấp giả thuyết, agent nhắc nhở: *"Hồ sơ thẩm định cần một giả thuyết công tác để kiểm chứng, nếu không báo cáo sẽ chỉ là tóm tắt thông tin chung và mất giá trị ra quyết định. Bạn đang tin điều gì về thực thể này?"*
2. **Thiết Kế Truy Vấn Hai Chiều (Antonym-Pivot Search Design)**:
   - Sử dụng `DisconfirmingEvidenceChecker` để tự động đảo ngược các động từ then chốt của giả thuyết (Ví dụ: *đang tăng trưởng $\rightarrow$ đang thu hẹp/sa thải; dẫn đầu $\rightarrow$ tụt hậu/mất thị phần*).
   - Phân bổ ngân sách tìm kiếm: tối thiểu $30\%$ truy vấn hướng tới việc tìm bằng chứng bác bỏ giả thuyết.
3. **Thu Thập & Phân Tầng Độ Tin Cậy Nguồn**:
   - Sử dụng `web.search` và phân tầng bằng `SourceTierClassifier`.
   - Ưu tiên tối đa nguồn Primary (.gov, cổng thông tin doanh nghiệp, báo cáo kiểm toán). Mọi thông tin tiêu cực hoặc cáo buộc từ nguồn Tertiary (diễn đàn, review ẩn danh) phải được đối chiếu chéo với nguồn Secondary hoặc Primary trước khi đưa vào báo cáo.
4. **Cổng Kiểm Soát Thiên Vị Xác Nhận (Anti-Confirmation-Bias Gate)**:
   - Tính tỷ lệ bằng chứng phản biện. Nếu tỷ lệ $< 20\%$, **DỪNG XUẤT KẾT LUẬN** và bổ sung thêm các truy vấn phản biện bắt buộc.
5. **Trích Xuất Mốc Thời Gian & Dấu Hiệu Cảnh Báo (Red Flags)**:
   - Rà soát 12 tháng gần nhất: Thay đổi nhân sự lãnh đạo, tranh chấp pháp lý, biến động cổ đông, sụt giảm tăng trưởng, sự cố bảo mật hoặc khiếu nại khách hàng.
6. **Xây Dựng Móc Nối Đối Thoại Thực Chiến (Conversation Hooks)**:
   - Sinh ra 3 móc nối đối thoại gắn liền với các sự kiện hoặc phát hiện cụ thể, phục vụ mở đầu câu chuyện một cách tinh tế trong cuộc gặp.

## 5. Tool Calls Được Phép (Allowed Tool Calls)
- `web.search`: Tra cứu hồ sơ doanh nghiệp, báo cáo tài chính, báo chí và thông tin pháp lý công khai.

## 6. Yêu Cầu Bằng Chứng (Evidence Requirements)
- **Tỷ lệ phản biện bắt buộc**: Disconfirming ratio $\ge 30\%$. Nghiêm cấm xuất hồ sơ thẩm định mang tính tâng bốc một chiều.
- **Phân tầng minh bạch**: Mọi khẳng định phải gắn nhãn `[Primary]`, `[Secondary]` hoặc `[Tertiary]`.
- **Cảnh báo đỏ phải có dẫn chứng**: Nghiêm cấm đưa ra cáo buộc tài chính hoặc pháp lý nếu chỉ dựa vào nguồn Tertiary không được kiểm chứng.

## 7. Safe Fallback
Khi `web.search` chưa khả dụng:
- Agent yêu cầu người dùng cung cấp tài liệu nội bộ (báo cáo thẩm định sơ bộ, pitch deck hoặc hợp đồng).
- Gắn cờ cảnh báo `[Internal Documents Only - No External Verification]`.

## 8. Định Dạng Đầu Ra (Output Format)
```markdown
# Hồ Sơ Thẩm Định Thực Thể (Decision-Grade Entity Dossier)

## 1. Hồ Sơ Nhận Diện & Kết Luận Giả Thuyết (Executive Verdict)
- **Thực thể**: [Tên đầy đủ công ty / nhân sự / tổ chức] | Website: [URL]
- **Mục đích thẩm định**: [Đàm phán hợp đồng / M&A / Đối tác / Đầu tư]
- **Giả thuyết ban đầu (Hypothesis)**: "[Nội dung giả thuyết của người dùng]"
- **KẾT LUẬN KIỂM CHỨNG**: **[XÁC NHẬN (SUPPORTED) / BÁC BỎ (DISPROVED) / KHÔNG ĐỦ BẰNG CHỨNG]**
- **Điểm tin cậy hồ sơ**: [X.XX / 1.00] - Tỷ lệ nguồn Primary: XX%

## 2. Dữ Kiện Thực Tế & Dòng Thời Gian 12 Tháng (Timeline)
- **Trụ sở & Quy mô**: [Địa điểm, số lượng nhân sự, ước tính doanh thu]
- **Dòng thời gian hoạt động nổi bật (12M)**:
  - `YYYY-MM`: [Sự kiện 1 kèm liên kết nguồn trích dẫn]
  - `YYYY-MM`: [Sự kiện 2 kèm liên kết nguồn trích dẫn]

## 3. Bằng Chứng Đối Chiếu Hai Chiều (Evidence Balance)
### 3.1 Dữ kiện Ủng hộ Giả thuyết (Supporting Evidence)
- [Bằng chứng cụ thể kèm trích dẫn nguồn cấp 1 hoặc 2]
### 3.2 Dữ kiện Bác bỏ / Giới hạn của Giả thuyết (Disconfirming Evidence)
- [Bằng chứng phản biện cụ thể chỉ ra các ngoại lệ hoặc rủi ro tiềm ẩn]

## 4. Dấu Hiệu Cảnh Báo Đỏ (Red Flags & Risk Radar)
- 🚩 **Cảnh báo 1**: [Mô tả rủi ro pháp lý, tài chính hoặc biến động nhân sự] - `[Tier: Primary/Secondary]`
- 🚩 **Cảnh báo 2**: [Rủi ro công nghệ hoặc phàn nàn của khách hàng]

## 5. Móc Nối Đối Thoại Đàm Phán (Conversation Hooks)
1. **Hook 1 (Về thành tựu/sự kiện gần đây)**: "[Câu hỏi gợi mở mở đầu cuộc trò chuyện]"
2. **Hook 2 (Về điểm nghẽn chiến lược)**: "[Cách đặt vấn đề đồng cảm với thách thức của họ]"
3. **Hook 3 (Về cơ hội hợp tác đôi bên cùng có lợi)**: "[Góc tiếp cận giá trị khác biệt]"

---
**Khối Kiểm Toán Truy Vấn (Three-Count Audit Block):**
- Queries Sent: XX | Sources Received: XX | Sources Cited: XX
- Tỷ lệ phản biện: XX% (Đạt chuẩn >= 30%) | Trạng thái thiên vị: PASS
```

## 9. Xử Lý Lỗi & Phòng Vệ An Toàn (Security & Edge Cases)
- **Ranh giới bảo mật thông tin nhạy cảm**: Không tìm kiếm hoặc lưu trữ thông tin đời tư cá nhân vi phạm pháp luật (tài khoản ngân hàng cá nhân, hồ sơ y tế).
- **Phòng vệ bôi nhọ đối thủ**: Nếu phát hiện các bài viết mang tính bôi nhọ không căn cứ từ đối thủ của thực thể, bắt buộc phân loại vào nguồn Tertiary và gắn cờ `[Potential Defamation / Unverified Competitor Attack]`.

## 10. Nguồn (Review Record)
```yaml
upstream:
  repository: alirezarezvani/claude-skills
  commit: 19392f7a08264ed00486a251f5b2098321771f94
  skill: research/skills/dossier
  upstream_version: 1.0.0
  license: MIT
adaptation:
  kept:
    - Kỷ luật kiểm chứng giả thuyết (Hypothesis-Testing Discipline)
    - Tỷ lệ bằng chứng phản biện tối thiểu 30% (Antonym-pivot heuristics)
    - Phân tầng nguồn tin Primary / Secondary / Tertiary
    - Cấu trúc Conversation Hooks và Red Flags
  changed:
    - Bản địa hóa sang tiếng Việt và tích hợp chuẩn cấu trúc 10 mục của COSA
    - Tích hợp DisconfirmingEvidenceChecker và SourceTierClassifier thuần Python stdlib
  added:
    - Rào chắn kiểm duyệt nguồn bôi nhọ ẩn danh
    - Ráp nối với pipeline đánh giá gate P1-P5
  excluded:
    - Script Node.js docx template phụ thuộc thư viện ngoài
```
