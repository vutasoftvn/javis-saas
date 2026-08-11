# JAVIS Marketing OS — Phân tích khoảng trống & Kế hoạch hoàn thiện

**Nguồn yêu cầu:** `JAVIS_MARKETING_OS_SUPPLEMENT.md` (v1.0)
**Phạm vi:** `backend/app/modules/marketing`, `frontend/lib/modules/marketing`
**Ngày:** 2026-08-10

---

## 1. Hiện trạng

Module Marketing OS đã có khung sườn:

| Lớp | Đã có | Tình trạng |
|---|---|---|
| Data model | 10 bảng (context, objective, campaign, asset, metric, snapshot, experiment, learning, skill registry, approval) | ORM **lệch schema** so với migration |
| Skill Router | `SkillRouter` với 13 capability mặc định + approval gate | Chưa ghi log thực thi, chưa có provider runtime |
| Analytics | `AnalyticsEngine`: CVR, CAC, ROAS, Z-test | Thiếu LTV/ARPU/payback/retention/funnel/12-week |
| Context | `ContextAdapter` ghép Marketing Context + Strategy Foundation | Đủ cho Phase 1 |
| API | 13 endpoint REST | **Không xác thực** (lỗ hổng cross-tenant) |
| UI | Cockpit 6 tab, đa số read-only | Nhãn tiếng Anh lẫn lộn, không tạo/sửa được dữ liệu |

## 2. Khoảng trống nghiêm trọng (chặn phát hành)

### 2.1. Lỗ hổng tenancy — `get_current_marketing_member`

```python
member = db.query(WorkspaceMember).first()   # lấy đại thành viên đầu tiên trong DB
```

Router marketing **không** dùng `get_current_workspace_member` như các module khác. Hệ quả:

- Gọi API **không cần token** vẫn đọc/ghi được dữ liệu.
- `workspace_id` client gửi lên không được đối chiếu với người dùng đã đăng nhập →
  bất kỳ ai cũng đọc được Marketing Context, ngân sách chiến dịch, và **duyệt được**
  `PendingApproval` của workspace khác.

Vi phạm trực tiếp `CLAUDE.md` §Security. Đây là hạng mục sửa đầu tiên.

### 2.2. ORM lệch schema Postgres

Migration `mkt001a2b3c4` và `models.py` mô tả 5 bảng khác nhau:

| Bảng | Migration | ORM | Hậu quả |
|---|---|---|---|
| `marketing_metrics` | `metric_value`, `period`, `campaign_id`, `recorded_at` | `current_value`, `previous_value`, `change_pct`, `category` | Mọi truy vấn metric lỗi cột |
| `metric_snapshots` | `workspace_id`, `metric_name`, `snapshot_at` | `metric_id`, `recorded_at` | Không ghi được snapshot |
| `marketing_learnings` | `insight`, `category`, `impact_score` | `observation/hypothesis/action/result/learning` | Learning Loop (§16) không chạy |
| `campaign_assets` | `workspace_id`, `metadata`, `status` | `meta_data`, `approval_status` | Asset không scope theo tenant |
| `marketing_experiments` | thiếu `learning` | có `learning` | Ghi kết quả thử nghiệm lỗi |

Router đang che lỗi bằng `try/except Exception: return []` nên UI luôn hiện rỗng thay vì báo lỗi.

### 2.3. Số liệu giả trong cockpit

`execution_score_pct` hard-code `85.0` ở cả backend lẫn fallback frontend — đúng con số
đang hiển thị trên màn hình. Trong khi `TwelveWeekCycle`/`WeeklyPlan`/`WeeklyCommitment`
đã có dữ liệu thật ở module strategy để tính.

## 3. Khoảng trống theo tài liệu bổ sung

| Mục tài liệu | Yêu cầu | Trạng thái |
|---|---|---|
| §8 Funnel Model | 8 giai đoạn Discover→Advocate, mỗi stage có goal/metrics/experiments | ❌ chưa có |
| §10 12 Week Year | Execution Score, Lead/Lag KPI Score, Experiment Velocity | ❌ chỉ có hằng số |
| §13–14 Analytics | LTV, ARPU, payback, retention, NRR, cohort, attribution | ❌ thiếu |
| §15 Experiment Engine | Vòng đời hypothesis→measure→decision (WIN/LOSE/INCONCLUSIVE/ITERATE) | ⚠️ chỉ có Z-test |
| §16 Learning Loop | Campaign → Learning → Playbook | ❌ chưa có API |
| §20 Human Approval | Duyệt trước mọi hành động ra ngoài | ⚠️ có hàng đợi, duyệt xong **không** thực thi |
| §25 Skill Evaluation | Log skill/version/cost/latency/rating | ❌ chưa có bảng |
| §26–27 Cockpit UI | Objective, funnel, campaign, experiment, insight, approval | ⚠️ 6 tab, phần lớn trống |

## 4. Kế hoạch hoàn thiện

### Giai đoạn A — Nền tảng ✅ đã triển khai

1. **Bảo mật:** resolver giả được thay bằng `get_current_workspace_member`; mọi endpoint
   bắt buộc `workspace_id` + token; mọi tra cứu theo id đều lọc theo `workspace_id` và trả
   404 chung cho "không tồn tại" lẫn "khác tenant". Kiểm chứng: gọi không token trả 401.
2. **Schema:** migration `mkt002b3c4d5e` đồng bộ ORM ↔ Postgres (metric, snapshot,
   learning, asset, experiment, `marketing_campaigns.start_date/end_date`) và thêm bảng
   `skill_executions`.
3. **Analytics:** `AnalyticsEngine` bổ sung CTR/CPC/CPL, ARPU, LTV, payback, LTV/CAC,
   retention, churn, NRR, GRR, funnel conversion, phát hiện bất thường, bảng điểm 12 tuần
   và p-value cho kiểm định Z — thuần Python, không nhờ LLM (§38).
4. **Funnel:** `FunnelEngine` chuẩn hoá 8 bước kèm nhãn tiếng Việt, rollup chiến dịch/thử
   nghiệm/chỉ số. Hai bẫy đã xử lý: bước chưa có số đo trả `null` (không phải 0%) và chuỗi
   chuyển đổi chỉ nối bằng chỉ số **số lượng**, không nối bằng tỷ lệ như `churn_rate`.
5. **12 Week Year:** `ScorecardService` tính điểm từ `WeeklyCommitment` thật; khi chưa có
   chu kỳ nào thì trả `has_execution_data=false` để UI hiện "—" thay cho hằng số 85%.
6. **API:** 23 endpoint gồm funnel, metrics + lịch sử, analytics overview, learnings, vòng
   đời chiến dịch, asset, đánh giá/chốt thử nghiệm, nhật ký chạy skill và **thực thi sau
   khi được duyệt**.
7. **UI:** cockpit 10 tab tiếng Việt (Tổng quan, Bối cảnh, Mục tiêu, Phễu, Chiến dịch,
   Thử nghiệm, Chỉ số, Bài học, Kho kỹ năng, Phê duyệt) kèm đầy đủ form tạo/sửa/duyệt.

Kiểm chứng: 152 test pytest pass, `flutter analyze lib` sạch, và một lượt smoke test thật
qua HTTP trên Postgres (tạo mục tiêu → chiến dịch → xin duyệt kích hoạt → duyệt → ghi chỉ
số → phễu → thử nghiệm → chốt quyết định → bài học).

### Giai đoạn B — Execution runtime (kế tiếp)

- `SkillProvider` interface (`discover/validate/execute/score`) + `OpenClawProvider`,
  `AlirezaProvider`, `PythonProvider`, `NativeProvider` (§24).
- Chạy skill trong sandbox tách khỏi Vault/Finance (§22), khai báo permission theo §21.
- Hiện tại `execute-skill` **không gọi runtime thật**: nó ghi `SkillExecution` trạng thái
  `simulated` và trả về thông báo rõ ràng. Không được hiển thị như đã thực thi thật.

### Giai đoạn C — Live data & closed loop

- Connector Google Ads / Search Console / Meta Ads / X (§12.6) đổ vào `marketing_metrics`.
- Event bus: `CPA > ngưỡng` → Ads Optimization Agent (§18).
- Learning Engine tổng hợp playbook từ lịch sử campaign (§16).

## 5. Nguyên tắc giữ nguyên

- Javis sở hữu context, router, memory, permission, analytics DB. Skill bên thứ ba chỉ là
  provider (ADR-MKT-001).
- Không LLM tính KPI (§39.4). Mọi con số trên cockpit đến từ `AnalyticsEngine`.
- Không auto-publish, không auto-spend (§39.5, §39.6): mọi capability có
  `external_write` hoặc `spend` đều bị chặn bằng cấu trúc, không bằng prompt.
- Toàn bộ nhãn UI dùng tiếng Việt; mã capability (`marketing.cro`) giữ nguyên vì là định danh kỹ thuật.
