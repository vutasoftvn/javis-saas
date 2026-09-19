# Kế Hoạch Triển Khai: Tích Hợp Bộ 3 Personas (Solo Founder, Startup CTO, Growth Marketer) Vào COSA

**Ngày lập:** 2026-09-19  
**Tài liệu tham chiếu:** 
- [`alirezarezvani/claude-skills/agents/personas`](https://github.com/alirezarezvani/claude-skills/tree/main/agents/personas)
  - `solo-founder.md`
  - `startup-cto.md`
  - `growth-marketer.md`
- [`docs/superpowers/plans/2026-09-18-virtual-c-suite-agent-architecture-12wy.md`](file:///Volumes/SSD/javis-saas/docs/superpowers/plans/2026-09-18-virtual-c-suite-agent-architecture-12wy.md)
- [`docs/superpowers/plans/2026-09-18-cto-advisor-skillpack-and-governance-integration.md`](file:///Volumes/SSD/javis-saas/docs/superpowers/plans/2026-09-18-cto-advisor-skillpack-and-governance-integration.md)
- [`packages/agent/workforce/governance.py`](file:///Volumes/SSD/javis-saas/packages/agent/workforce/governance.py) (M7 §5 Governance)
- [`shared/contracts/executive-advisor-roles.json`](file:///Volumes/SSD/javis-saas/shared/contracts/executive-advisor-roles.json)
- [`shared/contracts/startup-team-profiles.json`](file:///Volumes/SSD/javis-saas/shared/contracts/startup-team-profiles.json)
**Trạng thái:** Đã phê duyệt — Đang triển khai (In Progress)

---

## 1. Mục Tiêu & Triết Lý Thiết Kế

Tích hợp có chọn lọc và thích ứng các chuẩn mực thực hành tốt nhất từ 3 Personas nổi bật của kho tri thức `alirezarezvani/claude-skills` vào nền tảng **COSA (`javis-saas`)**:

1. **Solo Founder Persona (`solo-founder.md`):** Nâng cấp vai trò `founder_assistant` (AI Co-Founder chat thường trực) thoát khỏi sự phụ thuộc vào `COSA_OPERATIONS_AGENT_SPEC`, trang bị linh hồn của một **Thinking Partner & Co-Founder đa năng** (bảo vệ thời gian Founder, 1 goal/week, morning=build/afternoon=sell, 2-week MVP, reality-check phản biện tính năng thừa, chuông báo runway & chống kiệt sức).
2. **Startup CTO Persona (`startup-cto.md`):** Tái cấu trúc vai trò CTO Advisor theo mô hình **Thích ứng Giai đoạn (Stage-Adaptive CTO)**:
   - Ở các giai đoạn sớm (`P0_DISCOVERY`, `P1_VALIDATION`, `P2_FOUNDATION`): Kích hoạt tư duy **Startup CTO (Pragmatic & Ship-First)** — chọn Boring Technology, mặc định Monolith, dùng Managed SaaS cho Auth/DB/Payments, chống Over-engineering / Resume-driven architecture.
   - Ở các giai đoạn quy mô lớn (`P3` đến `P6`): Kích hoạt tư duy **Enterprise CTO Advisor** — ADRs, Hybrid Engineering Workforce (kỹ sư + hạm đội AI), DORA metrics, SOC 2.
   - Bổ sung cẩm nang rà soát kỹ thuật 30 phút cho nhà đầu tư (*Due Diligence Readiness Checklist*).
3. **Growth Marketer Persona (`growth-marketer.md`):** Đóng gói bộ kỹ năng **Bootstrapped Growth Engine & Scrappy Launch Sequences ($0 - $1M ARR)** thành skillpack chuẩn COSA (`growth.bootstrapped-engine`), bao gồm:
   - Quy trình *90-Day Compounding Content Engine*.
   - Quy trình *Product Launch Sequencer* (Pre-launch 14d, Launch Day Blitz, Post-launch 14d).
   - Quy trình *Conversion Drop-off Audit* (Rà soát 5 điểm drop-off, thử nghiệm A/B 2 tuần).
   - Ràng buộc kỷ luật ngân sách nghiêm ngặt: $CAC < \frac{1}{3} LTV$, Organic First, Anti-vanity metrics.

---

## 2. Nguyên Tắc Quản Trị Hệ Thống (Governance Boundaries)

1. **M7 §5 Workforce Governance:** Title/Persona chỉ là **Presentation & Cognitive Guidance Overlay**, tuyệt đối **KHÔNG CẤP QUYỀN THỰC THI**. Quyền thực thi phụ thuộc 100% vào `AgentSpec.capability_refs` và `allowed_capability_prefixes`.
2. **Trần Tự Trị (Autonomy Ceiling):** Mọi Persona đều hoạt động dưới trần tự trị **`L0_OBSERVE`** (quan sát/gợi ý trong chat) hoặc **`L1_PROPOSE`** (đề xuất artifact/kế hoạch). Tuyệt đối không tự ý deploy hạ tầng, xóa dữ liệu, quẹt thẻ tín dụng hay xuất bản nội dung ra ngoài mà không có Human Approval.
3. **Chuẩn 12 Week Year (12WY) & Multi-speed Context:** Mọi mục tiêu, sprint, runway đều tính theo số tuần ($W$) và tỷ lệ đốt vốn theo tuần ($Burn/w$). Tự động nạp bối cảnh 7 chiều từ `v_current_company_context`.

---

## 3. Bản Đồ Thay Đổi Chi Tiết

### Vùng 1: Nâng Cấp Co-Founder Chat (`apps/cosa/agents/`)
- `apps/cosa/agents/specs.py`:
  - Tạo `COSA_COFOUNDER_ASSISTANT_PROMPT` và `COSA_COFOUNDER_ASSISTANT_AGENT_SPEC` (id: `cosa.agents.founder_assistant`, v1.0.0, `L0_OBSERVE`).
  - Sửa lỗi lệch phiên bản: Đồng bộ `research.deep-research` lên `1.2.0` với hash `fc85683dbb87b9ff1b9c0e25004f42269d20a8c5369bf4e3139550ed7f403625`.
- `apps/cosa/agents/agent_profile_specs.py`:
  - Trỏ `"founder_assistant": COSA_COFOUNDER_ASSISTANT_AGENT_SPEC`.
  - Bổ sung `"cto": COSA_EXECUTIVE_CTO_AGENT_SPEC` vào bảng `AGENT_PROFILE_SPECS`.

### Vùng 2: Stage-Adaptive CTO Advisor (`skillpacks/executive/cto-advisor/`)
- `skillpacks/executive/cto-advisor/SKILL.md`: Bổ sung cấu trúc 2 chế độ (Mode A: Startup CTO vs Mode B: Enterprise CTO).
- `skillpacks/executive/cto-advisor/references/technical_due_diligence_checklist.md`: Cẩm nang rà soát kỹ thuật chuẩn bị cho Due Diligence.
- `apps/cosa/agents/specs.py`: Cập nhật `COSA_EXECUTIVE_CTO_PROMPT` tích hợp tư duy Startup CTO và pin skillpack `executive.cto-advisor`.

### Vùng 3: Bootstrapped Growth Engine (`skillpacks/growth/bootstrapped-engine/`)
- `manifest.yaml`: Định nghĩa Skill `growth.bootstrapped-engine` v1.0.0.
- `SKILL.md`: Quy trình 10 mục chuẩn COSA với 3 quy trình tác nghiệp và ranh giới ngân sách $CAC < \frac{1}{3} LTV$.
- `references/product_hunt_playbook.md`: Kịch bản ra mắt Product Hunt / Hacker News.
- `references/topic_cluster_template.md`: Mẫu cụm chủ đề SEO 90 ngày.
- `evals/growth/bootstrapped-engine.yaml`: Bộ kiểm chuẩn an toàn và kỷ luật ngân sách.
- `packages/agent/workforce/catalog.py`: Gợi ý persona `"Growth Marketer"` cho `campaign_planner` và `market_research_specialist`.

### Vùng 4: Sổ Cái Phân Bổ Nguồn Gốc (`docs/integrations/skill-source-attribution.md`)
- Cập nhật Tranche G ghi nhận nguồn gốc từ commit `19392f7a08264ed00486a251f5b2098321771f94`.
