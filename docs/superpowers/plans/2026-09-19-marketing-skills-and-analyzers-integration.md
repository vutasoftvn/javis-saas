# Kế Hoạch Triển Khai: Tích Hợp Marketing Skills & Quantitative Analyzers vào COSA

**Ngày lập:** 2026-09-19  
**Tài liệu tham chiếu:**  
- [`docs/cosa.md`](../../cosa.md)  
- [`CLAUDE.md`](../../../CLAUDE.md)  
- [`skillpacks/engineering/workspace-site-builder/SKILL.md`](../../../skillpacks/engineering/workspace-site-builder/SKILL.md)  
- [`skillpacks/engineering/workspace-site-builder/references/sandbox_isolation_guide.md`](../../../skillpacks/engineering/workspace-site-builder/references/sandbox_isolation_guide.md)  
- [`alirezarezvani/claude-skills/marketing`](https://github.com/alirezarezvani/claude-skills/tree/main/marketing)  
- [`alirezarezvani/claude-skills/marketing-skill`](https://github.com/alirezarezvani/claude-skills/tree/main/marketing-skill)  
- [`coreyhaines31/marketingskills`](https://github.com/coreyhaines31/marketingskills)  
**Trạng thái:** Sẵn sàng thực thi

---

## 1. Mục Tiêu & Ranh Giới Thiết Kế

Kế hoạch này tích hợp các mô hình thực hành tốt nhất từ 3 kho tri thức nguồn Marketing bên ngoài vào kiến trúc **COSA (javis-saas)**:
1. **Khoảng trống định lượng Tiếp thị (Marketing Quantitative Gap):** Bổ sung các công cụ tính toán tất định 100% Python Standard Library (Brand Voice Flesch & AI Clichés, AEO Readiness & Fact Density, WCAG 2.1 Contrast Ratio & Palette Derivation, LinkedIn Post Linter & Unicode blocker).
2. **Khoảng trống Năng lực Tiếp thị Hiện đại (Modern Marketing Capability Gap):**
   - Tối ưu hóa tìm kiếm AI (Answer Engine Optimization - AEO / GEO) cho Perplexity, ChatGPT Search, Claude, Gemini.
   - Hội đồng cố vấn tiếp thị phản biện đa góc nhìn (Marketing Council) với cơ chế bắt buộc có **Designated Dissenter**.
   - Playbook phát triển thương hiệu cá nhân/B2B trên LinkedIn tự nhiên (organic), cấm hoàn toàn bot và automation vi phạm chính sách.
   - Sinh trang giới thiệu sản phẩm 3D tương tác (Showcase One-Pager) trong Sandbox cô lập.
   - Tự nhiên hóa văn phong, tẩy sạch "mùi AI" (Content Humanizer).
   - Vòng lặp tiếp thị định kỳ (Marketing Loops) trên nền tảng `operations.loop-lifecycle` và `LoopDoctor`.

### Nguyên Tắc Bắt Buộc:
- **100% Python Standard Library:** Không cài thêm package bên ngoài vào `requirements.txt` hay `packages/agent/pyproject.toml`.
- **Ranh giới bất khả xâm phạm với `landing/`:** Thư mục `landing/` ở gốc repository là Landing Page tiếp thị của chính nền tảng COSA SaaS. Tính năng tạo trang web cho người dùng **tuyệt đối không đụng chạm vào `landing/`**, chỉ hoạt động trong không gian **Sandbox cô lập** của từng Workspace (`var/sandboxes/{workspace_id}/sites/{site_id}/out/index.html`) hoặc lưu trữ qua `commercial.campaign_asset.write`.
- **Ranh giới an toàn (Anti-Spam / Non-Mutating):** Tuyệt đối loại bỏ các hành vi tự động gửi outbound spam, cold email không kiểm soát, bot cào dữ liệu hoặc tự động đổi giá tiền trên cổng thanh toán.
- **Quy chuẩn 10 mục Skillpack:** Mọi skillpack mới/nâng cấp đều có `manifest.yaml`, `SKILL.md` tiếng Việt 10 mục, và `evals/<domain>/<name>.yaml`.
- **Minh bạch nguồn gốc:** Ghi nhận đầy đủ commit SHA 40 ký tự bất biến và giấy phép MIT vào `docs/integrations/skill-source-attribution.md`.

---

## 2. Danh Mục Các Hạng Mục Triển Khai

### Hợp phần 1: Bộ Thư Viện Phân Tích Định Lượng (`packages/agent/marketing/analyzers/`)
- `brand_voice_analyzer.py`: Flesch Reading Ease score, formality index, passive voice ratio, AI cliches detector.
- `aeo_readiness_calculator.py`: E-E-A-T score (0-100), factual density per 1000 words, fact-first lede check, schema JSON-LD checklist.
- `palette_contrast_validator.py`: W3C WCAG 2.1 relative luminance, contrast ratio (AA/AAA), derived palette.
- `linkedin_post_linter.py`: Hook length / fold break, Unicode pseudo-bold/pseudo-italic blocker, formatting rhythm.

### Hợp phần 2: Các Skillpack Tiếp Thị Mới (`skillpacks/marketing/` và `evals/marketing/`)
- `marketing.aeo`: Answer Engine Optimization (Tối ưu hóa để được trích dẫn trên LLM Search).
- `marketing.marketing-council`: Hội đồng cố vấn tiếp thị đa góc nhìn với Designated Dissenter bắt buộc.
- `marketing.linkedin-presence`: Chiến lược & nội dung LinkedIn hữu cơ chuyên nghiệp, cấm bot.
- `marketing.content-humanizer`: Thanh lọc và tự nhiên hóa văn phong tiếp thị do AI tạo ra.
- `marketing.showcase-page-generator`: Sinh trang giới thiệu 3D tương tác dạng single-file HTML trong Sandbox cô lập.
- `marketing.marketing-loops`: Chuẩn hóa các vòng lặp tiếp thị định kỳ theo 9 thành phần giải phẫu.

### Hợp phần 3: Nâng Cấp Các Skillpack Hiện Hữu
- `marketing.copywriting`: Nâng cấp lên v1.2.0, bổ sung kiểm định thông điệp thị trường và tích hợp `BrandVoiceAnalyzer`.
- `marketing.seo-plan`: Nâng cấp lên v1.2.0, bổ sung Programmatic SEO và schema JSON-LD.
- `marketing.campaign-review`: Nâng cấp lên v1.1.0, bổ sung Event Taxonomy và UTM Taxonomy chuẩn.

### Hợp phần 4: Sổ Cái Nguồn Gốc (Attribution Ledger)
- Cập nhật `docs/integrations/skill-source-attribution.md` ghi nhận commit SHA 40 ký tự và mapping Keep/Adapt/Add/Exclude.

### Hợp phần 5: Bộ Kiểm Thử Đơn Vị (Unit Tests)
- `tests/agent/marketing/test_analyzers.py`: Kiểm thử toàn bộ 4 analyzer.
- Chạy `scripts/validate_skillpacks.py` kiểm tra hợp quy 100%.
