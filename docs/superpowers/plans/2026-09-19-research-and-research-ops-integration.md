# Kế Hoạch Triển Khai: Tích Hợp Research & Research-Ops Skills và Quantitative Analyzers vào COSA

**Ngày lập:** 2026-09-19  
**Tài liệu tham chiếu:**  
- [`docs/cosa.md`](../../cosa.md)  
- [`CLAUDE.md`](../../../CLAUDE.md)  
- [`docs/integrations/skill-source-attribution.md`](../../integrations/skill-source-attribution.md)  
- [`alirezarezvani/claude-skills/research`](https://github.com/alirezarezvani/claude-skills/tree/main/research)  
- [`alirezarezvani/claude-skills/research-ops`](https://github.com/alirezarezvani/claude-skills/tree/main/research-ops)  
**Trạng thái:** Sẵn sàng thực thi (Tranche F)

---

## 1. Mục Tiêu & Ranh Giới Thiết Kế

Kế hoạch này tích hợp các phương pháp luận và công cụ nghiên cứu tiên tiến từ 2 kho tri thức nguồn `research` và `research-ops` (`alirezarezvani/claude-skills`, commit `19392f7a08264ed00486a251f5b2098321771f94`, giấy phép MIT) vào kiến trúc **COSA (`javis-saas`)**:

1. **Khoảng trống tính toán định lượng Nghiên cứu (Research Quantitative Gap):**
   - Xây dựng 6 công cụ tính toán tất định 100% Python Standard Library trong `packages/agent/research/analyzers/`:
     - `MarketSizingTriangulator`: Tính TAM/SAM/SOM kép (Top-down VÀ Bottoms-up), phát hiện sai lệch tam giác (> 30% cảnh báo `TRIANGULATION FAILED`).
     - `SurveySamplePlanner`: Tính cỡ mẫu thống kê Cochran và hiệu chỉnh quần thể hữu hạn, biên độ sai số (margin of error).
     - `DisconfirmingEvidenceChecker`: Kiểm soát tỷ lệ bằng chứng phản biện ($\ge 30\%$) và sinh truy vấn đối lập (*antonym-pivots*) chống thiên vị xác nhận (*confirmation bias*).
     - `SourceTierClassifier`: Phân tầng tự động độ tin cậy của URL nguồn (Primary: .gov, kiểm toán, đăng ký / Secondary: báo chí uy tín / Tertiary: diễn đàn, mạng xã hội).
     - `ResearchSaturationModeler`: Mô hình hóa độ bão hòa mẫu người dùng (định luật Nielsen $1-(1-p)^n$ và chuẩn Guest et al.), linter phân biệt rạch ròi giữa Anecdote (1 người) và Insight (hội tụ).
     - `RDCapexOpexRouter`: Rà soát 6 điều kiện vốn hóa R&D phần mềm SaaS (IAS 38 / ASC 350-40) và chuyển hồ sơ có định danh đến `R&D Finance Controller`.

2. **Khoảng trống Năng lực Nghiên cứu & Vận hành R&D (Research Capability Gap):**
   - **Thẩm định thực thể sâu (`research.dossier`):** Nghiên cứu đối tác chiến lược, khách hàng lớn B2B, nhà đầu tư, đối thủ cạnh tranh với kỷ luật kiểm chứng giả thuyết (*Hypothesis-Testing Discipline*).
   - **Quy trình vận hành nghiên cứu sản phẩm (`product.research-ops`):** Kết nối chặt chẽ giữa `discovery` và `prd`, chuẩn hóa kho lưu trữ quan sát $\rightarrow$ insight $\rightarrow$ đề xuất hành động.
   - **Quản trị chi phí R&D phần mềm (`finance.rd-accounting`):** Phân định chi phí nghiên cứu (OpEx) vs phát triển (CapEx) minh bạch.
   - **Tình báo sáng chế (`research.patent-intelligence`):** Rà soát Prior Art, FTO và CPC landscape kèm điều khoản miễn trừ tư vấn pháp lý nghiêm ngặt.
   - **Nâng cấp 3 skillpack hiện hữu:** `research.market-sizing`, `research.deep-research`, `research.industry-trends`.

### Nguyên Tắc Bắt Buộc:
- **100% Python Standard Library:** Tuyệt đối không thêm dependency ngoài (`numpy`, `pandas`, `scipy`) vào analyzers.
- **Tính toán tất định - Zero Hallucination:** Không giao cho LLM tính nhẩm cỡ mẫu hay tỷ lệ dung sai quy mô thị trường.
- **Ranh giới trách nhiệm con người (Named Human Owner):** Quyết định vốn hóa kế toán R&D luôn thuộc về `R&D Finance Controller`; kết luận sáng chế luôn gắn khuyến nghị tham vấn luật sư sở hữu trí tuệ.
- **Quy chuẩn 10 mục Skillpack COSA:** Đầy đủ `manifest.yaml`, `SKILL.md` tiếng Việt 10 mục và `evals/`.
- **Sổ cái nguồn gốc minh bạch:** Ghi nhận Tranche F vào `docs/integrations/skill-source-attribution.md`.

---

## 2. Danh Mục Các Hạng Mục Triển Khai

### Hợp phần 1: Bộ Thư Viện Phân Tích Định Lượng (`packages/agent/research/analyzers/`)
- `market_sizing_triangulator.py`: TAM/SAM/SOM kép, độ lệch tam giác, kiểm tra ngưỡng dung sai theo profile ngành.
- `survey_sample_planner.py`: Cỡ mẫu Cochran, khoảng tin cậy 90/95/99%, điều chỉnh quy mô hữu hạn, hệ số phản hồi.
- `disconfirming_evidence_checker.py`: Kiểm tra tỷ lệ phản biện $\ge 30\%$, cảnh báo thiên vị $< 20\%$, sinh gợi ý đối lập qua từ điển antonym-pivots.
- `source_tier_classifier.py`: Phân loại domain/URL vào Primary (1.0), Secondary (0.7), Tertiary (0.4).
- `research_saturation_modeler.py`: Cỡ mẫu Nielsen 5-user, Guest 12-user, linter chặn coi 1 người dùng là insight.
- `rd_capex_opex_router.py`: Rà soát 6 tiêu chí IAS 38, phân định OpEx vs CapEx, chuyển giao đích danh cho `R&D Finance Controller`.

### Hợp phần 2: Nâng Cấp 3 Skillpack Hiện Hữu
- `skillpacks/research/market-sizing`: Nâng cấp lên v1.2.0, tích hợp tính toán kép và cỡ mẫu Cochran qua `MarketSizingTriangulator`.
- `skillpacks/research/deep-research`: Nâng cấp lên v1.2.0, tích hợp `SourceTierClassifier` và Three-Count Tracking (*Sent / Received / Cited*).
- `skillpacks/research/industry-trends`: Nâng cấp lên v1.2.0, tích hợp mô hình quét xung lực thị trường theo 5 Angle và cửa sổ thời gian 7 - 90 ngày.

### Hợp phần 3: Bổ Sung 4 Skillpack Mới
- `skillpacks/research/dossier` (`research.dossier`): Thẩm định thực thể chuyên sâu, Hypothesis-Testing Discipline, kiểm soát tỷ lệ phản biện $\ge 30\%$.
- `skillpacks/product/research-ops` (`product.research-ops`): Vận hành nghiên cứu sản phẩm, đo lường điểm bão hòa mẫu và kho lưu trữ Insight chuẩn mực.
- `skillpacks/finance/rd-accounting` (`finance.rd-accounting`): Kế toán và quản trị tài chính R&D SaaS, định tuyến CapEx vs OpEx IAS 38.
- `skillpacks/research/patent-intelligence` (`research.patent-intelligence`): Tình báo bằng sáng chế Prior Art / FTO / CPC landscape kèm disclaimer pháp lý.

### Hợp phần 4: Bộ Kiểm Thử Đơn Vị & Hợp Quy
- `tests/agent/research/test_analyzers.py`: Bộ kiểm thử toàn diện cho 6 analyzer định lượng.
- `evals/`: Cập nhật và bổ sung các bộ kiểm thử eval suite YAML cho cả 7 skillpack.
- Chạy `scripts/validate_skillpacks.py` đảm bảo 100% hợp quy.

### Hợp phần 5: Sổ Cái Attribution Ledger (Tranche F)
- Cập nhật `docs/integrations/skill-source-attribution.md` ghi nhận 7 hạng mục Tranche F với commit SHA `19392f7a08264ed00486a251f5b2098321771f94`.
