# COSA — RACRO AI Marketing System: Phase B Plan & Technical Specification

> **Tài liệu tham chiếu gốc:** [COSA_AI_Marketing_System_Integration_Spec.md](file:///Volumes/SSD/javis-saas/markdown/COSA_AI_Marketing_System_Integration_Spec.md)  
> **Giai đoạn:** Phase B — RACRO Domain Contracts, Routing Metadata & Intent Guard  
> **Trạng thái:** Đã phê duyệt và triển khai

---

## 1. Mục tiêu Cốt lõi của Phase B

1. **Thiết lập Data Contracts:** Xây dựng các Pydantic Schemas chuẩn hóa cho `MarketingMission`, `MarketingSignal`, và `AttributionEvent`.
2. **Triển khai RACRO Specialist Router:** Tích hợp bộ phân loại chuyên sâu cho Marketing Domain mà không phá vỡ `IntentRouter` hiện tại.
3. **Hiện thực hóa Bất biến `NO INTENT = NO TOOL`:** Ngăn chặn tuyệt đối việc bot tự động kích hoạt tools/APIs khi người dùng chỉ gửi câu chào hoặc trò chuyện thông thường.
4. **Định tuyến Đa tầng (Multi-tier Routing):**
   $$\text{User Query} \longrightarrow \text{Domain} \longrightarrow \text{RACRO Move} \longrightarrow \text{Capability} \longrightarrow \text{Skill / Tool}$$

---

## 2. Đặc tả Schemas & Data Contracts

### 2.1. MarketingSignal Contract
```python
class MarketingSignal(BaseModel):
    id: str
    workspace_id: int
    project_id: Optional[int] = None
    source_type: str  # search, social, crm, competitor, review
    source_url: Optional[str] = None
    title: str
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    related_segment: Optional[str] = None
    related_hypothesis: Optional[str] = None
    observed_at: datetime
    expires_at: Optional[datetime] = None
    evidence_id: Optional[int] = None  # Link sang EvidenceItem khi được founder duyệt
```

### 2.2. MarketingMission Contract
```python
class MarketingMission(BaseModel):
    mission_id: str
    workspace_id: int
    project_id: Optional[int] = None
    move: RACROMove
    capability_id: str
    intent: str
    goal: str
    requested_by: str
    approval_required: bool = False
    context_data: Dict[str, Any] = Field(default_factory=dict)
```

---

## 3. Quy tắc Định tuyến & Invariant Guard

| Mẫu câu đầu vào (User Query) | Target Domain | RACRO Move | Capability | Tool Allowed? | Ghi chú |
| :--- | :--- | :--- | :--- | :---: | :--- |
| *"Chào em"*, *"Hello COSA"* | `general` | `None` | `None` | ❌ **FALSE** | `NO INTENT = NO TOOL` |
| *"Nghiên cứu đối thủ cạnh tranh của mID"* | `marketing` | `RESEARCH` | `competitor_intelligence` | ✅ **TRUE** | Kích hoạt Research Skill |
| *"Tạo nội dung bài viết và brief video cho tuần tới"* | `marketing` | `ATTRACT` | `content_creative` | ✅ **TRUE** | Content Generator |
| *"Kiểm tra có lead nào chưa được phản hồi không?"* | `sales` | `CONVERT` | `speed_to_lead` | ✅ **TRUE** | Đọc Speed-to-Lead CRM |
| *"Chăm sóc lại khách hàng cũ tháng trước"* | `sales` | `RETAIN` | `follow_up` | ✅ **TRUE** | Playbook Reactivation |
| *"Marketing hôm nay có gì cần tôi chú ý?"* | `marketing` | `ORCHESTRATE` | `founder_brief` | ✅ **TRUE** | Marketing Pulse Card |
