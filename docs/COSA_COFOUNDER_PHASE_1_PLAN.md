# COSA CO-FOUNDER ARCHITECTURE (F4 SPEC)
## PHASE 1 IMPLEMENTATION PLAN: DATABASE SCHEMA & MIGRATION

> **Mục tiêu:** Thiết lập nền tảng dữ liệu và lược đồ cơ sở dữ liệu cho kiến trúc COSA Co-Founder & 5 Core Domain Workforce mà không làm gián đoạn hay mất mát dữ liệu hiện tại.

---

## 1. PHÂN TÍCH THỰC THỂ DỮ LIỆU & SCHEMA GAP

### 1.1. Thực thể `AgentDefinition` ([backend/app/workforce/models.py](file:///Volumes/SSD/javis-saas/backend/app/workforce/models.py))
- **Hiện trạng:** Bảng `agent_definitions` chỉ có `agent_type` (`specialist`, `general`, `orchestrator`), chưa phân biệt được COSA Co-Founder ở cấp hệ thống với các Domain Agents.
- **Bổ sung:**
  - `category`: `String(50)` (Indexed, default `'DOMAIN'`).
    - `ORCHESTRATOR`: Dành riêng cho `COSA Co-Founder` (`key: 'cosa'`).
    - `DOMAIN`: 5 Core Domain Agents (`sales`, `marketing`, `finance`, `legal`, `build`).
    - `OPTIONAL_DOMAIN`: Các domain cài đặt thêm (`operations`, `people`, `support`).
    - `LEGACY`: Các agent đơn nhiệm cũ (`research_agent`, `seo_agent`, `qa_agent`...).
  - `is_default_active`: `Boolean` (default `False`, set `True` cho `cosa` và 5 Core Domains).

### 1.2. Thực thể mới `FounderDecision` (`founder_decisions`)
- **Mục tiêu:** Lưu trữ các quyết định chiến lược kinh doanh của Founder, phân biệt với `ApprovalRequest` (duyệt tác vụ).
- **Cấu trúc bảng:**
  ```python
  class FounderDecision(Base, SnowflakeIDMixin):
      __tablename__ = "founder_decisions"

      workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
      project_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
      domain: Mapped[str] = mapped_column(String(50), index=True) # SALES, MARKETING, FINANCE, LEGAL, TECH, CROSS_DOMAIN
      question: Mapped[str] = mapped_column(Text)
      context_summary: Mapped[str] = mapped_column(Text)
      options_jsonb: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)
      ai_recommendation_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
      evidence_ids: Mapped[List[str]] = mapped_column(JSONB, default=list) # Liên kết Evidence Engine (F1/F3)
      risk_analysis_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
      status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True) # PENDING, DECIDED, DISMISSED, DEFERRED
      decision_made: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
      founder_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
      decided_by_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
      decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
      created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
      updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
  ```

### 1.3. Thực thể mới `AgentAlias` (`agent_aliases`)
- **Mục tiêu:** Định tuyến mềm các truy vấn agent cũ sang kiến trúc mới mà không làm gãy API.
- **Cấu trúc bảng:**
  ```python
  class AgentAlias(Base, SnowflakeIDMixin):
      __tablename__ = "agent_aliases"

      workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
      alias_key: Mapped[str] = mapped_column(String(100), index=True) # vd: 'founder_agent', 'research_agent'
      target_type: Mapped[str] = mapped_column(String(50)) # 'ORCHESTRATOR', 'DOMAIN', 'SPECIALIST', 'CAPABILITY'
      target_key: Mapped[str] = mapped_column(String(100)) # vd: 'cosa', 'investigate', 'marketing.seo'
      is_active: Mapped[bool] = mapped_column(Boolean, default=True)
      notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
      created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
  ```

---

## 2. CÁC BƯỚC TRIỂN KHAI CHI TIẾT (STEP-BY-STEP)

### Bước 1: Chỉnh sửa Models trong Backend
- Cập nhật file [backend/app/workforce/models.py](file:///Volumes/SSD/javis-saas/backend/app/workforce/models.py):
  - Thêm `category`, `is_default_active` vào `AgentDefinition`.
  - Khai báo model `FounderDecision`.
  - Khai báo model `AgentAlias`.

### Bước 2: Tạo Alembic Migration Script
- Tạo migration `backend/alembic/versions/v13_051_cosa_cofounder_schema.py`.
- Thiết lập đầy đủ các lệnh `upgrade()` và `downgrade()`.

### Bước 3: Data Migration & Seeding
- Viết script seed mặc định:
  - Khởi tạo bản ghi `COSA Co-Founder` (`key: 'cosa'`, `category: 'ORCHESTRATOR'`, `is_default_active: True`).
  - Khởi tạo 5 Core Agents (`sales`, `marketing`, `finance`, `legal`, `build`) với `category: 'DOMAIN'`, `is_default_active: True`.
  - Seed bảng `agent_aliases`:
    - `founder_agent` $\rightarrow$ `('ORCHESTRATOR', 'cosa')`
    - `founder_copilot` $\rightarrow$ `('ORCHESTRATOR', 'cosa')`
    - `research_agent` $\rightarrow$ `('CAPABILITY', 'investigate')`
    - `seo_agent` $\rightarrow$ `('SPECIALIST', 'marketing.seo')`
    - `content_agent` $\rightarrow$ `('SPECIALIST', 'marketing.content')`
    - `qa_agent` $\rightarrow$ `('CAPABILITY', 'quality_gate')`

### Bước 4: Khai báo Pydantic Schemas
- Tạo file [backend/app/workforce/schemas/decision_schemas.py](file:///Volumes/SSD/javis-saas/backend/app/workforce/schemas/decision_schemas.py):
  - `FounderDecisionCreate`
  - `FounderDecisionUpdate`
  - `FounderDecisionResponse`
  - `FounderDecisionResolveRequest`
- Tạo file [backend/app/workforce/schemas/agent_category_schemas.py](file:///Volumes/SSD/javis-saas/backend/app/workforce/schemas/agent_category_schemas.py):
  - Enums `AgentCategoryEnum`.

### Bước 5: Viết Unit Test cho Phase 1
- Tạo file [backend/app/tests/workforce/test_phase1_cofounder_schema.py](file:///Volumes/SSD/javis-saas/backend/app/tests/workforce/test_phase1_cofounder_schema.py):
  - Kiểm tra tính toàn vẹn của bảng `founder_decisions`.
  - Kiểm tra truy vấn danh sách 5 Core Domains và COSA Co-Founder.
  - Kiểm tra cơ chế giải quyết `AgentAlias`.

---

## 3. CHECKLIST NGHIỆM THU PHASE 1

- [ ] Alembic migration `v13_051` chạy `alembic upgrade head` thành công không lỗi.
- [ ] Truy vấn DB xác nhận có bản ghi `cosa` thuộc `category = 'ORCHESTRATOR'`.
- [ ] Truy vấn DB xác nhận 5 Core Domains có `category = 'DOMAIN'` và `is_default_active = True`.
- [ ] Bảng `founder_decisions` tạo và lưu được bản ghi đầy đủ `options_jsonb` và `evidence_ids`.
- [ ] Bảng `agent_aliases` phân giải chính xác các alias cũ.
- [ ] Toàn bộ unit tests của Phase 1 đều pass.
