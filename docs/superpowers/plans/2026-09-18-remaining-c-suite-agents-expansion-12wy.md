# Kế Hoạch Mở Rộng Toàn Diện 13 C-Level Executive Advisors & Deep-Domain References (12-Week Year & Multi-Cadence)

> **Trạng thái:** DRAFT / PENDING IMPLEMENTATION  
> **Ngày lập:** 2026-09-18  
> **Phương pháp cốt lõi:** 12-Week Year (12WY), Bookended Voice Profile, Multi-Speed Onboarding Linkage, Two-Layer Memory & Preserved Dissent, Deep-Domain Reference Playbooks.  
> **Mục tiêu:** Nâng cấp và chuẩn hóa toàn bộ 13 C-Level Executive Agents còn lại trong hệ thống `javis-saas` (ngoài CEO và CTO đã hoàn thành), bao gồm cả bộ tài liệu tham chiếu chuyên sâu (`references/`) tương ứng cho từng vai trò.

---

## 1. Kiến Trúc Tổng Thể Hội Đồng C-Suite 14 Thành Viên

```mermaid
graph TD
    CoS["Chief of Staff (CoS)<br/>Điều phối Nghị sự & Preserved Dissent"]
    
    subgraph Capital ["Chiến Lược & Dòng Tiền"]
        CEO["CEO Advisor<br/>Tầm nhìn & Phân bổ vốn"]
        CFO["CFO Advisor<br/>Dòng tiền, Runway & Unit Economics"]
    end

    subgraph Growth ["Tăng Trưởng & Doanh Thu"]
        CPO["CPO Advisor<br/>Product Bets & PMF"]
        CMO["CMO Advisor<br/>Positioning & Acquisition Velocity"]
        CRO["CRO Advisor<br/>Sales Pipeline & Pricing Guardrails"]
        CCO["CCO Advisor<br/>Retention, NRR & Churn Defense"]
    end

    subgraph Execution ["Vận Hành, Kỹ Thuật & Nhân Lực"]
        COO["COO Advisor<br/>12WY Execution Cadence & ToC"]
        CTO["CTO Advisor<br/>Kiến trúc & TCO 144 tuần"]
        VPE["VPE Advisor<br/>DORA Metrics & Sprint Delivery"]
        CHRO["CHRO Advisor<br/>Org Design & Fireable Values"]
    end

    subgraph Governance ["An Ninh, Pháp Lý & AI/Data"]
        CISO["CISO Advisor<br/>Attack Surface & Security Posture"]
        GC["GC Advisor<br/>Regulatory & IP Protection"]
        CDO["CDO Advisor<br/>Data Quality & Lineage"]
        CAIO["CAIO Advisor<br/>Model Evals & Token Governance"]
    end

    CoS --> Capital
    CoS --> Growth
    CoS --> Execution
    CoS --> Governance
```

---

## 2. Chi Tiết Thiết Kế Từng C-Level Advisor & Danh Mục References Chuyên Sâu

---

### PHẦN I: NHÓM TÀI CHÍNH & VỐN (CAPITAL ENGINE)

#### 1. CFO Advisor (Chief Financial Officer)
- **Định vị & Bookended Voice:**
  - **Opening Hook:** *"Các con số thực tế đang nói lên điều gì về sức khỏe tài chính và số tuần runway của chúng ta?"*
  - **Forcing Questions:**
    - *"Ở mức burn net/tuần hiện tại, ngày hết tiền chính xác rơi vào tuần thứ mấy?"*
    - *"Tỷ lệ LTV/CAC và thời gian hoàn vốn CAC (CAC Payback) tính bằng bao nhiêu tuần?"*
    - *"Nếu doanh thu quý tới giảm 30%, chúng ta phải cắt giảm những khoản chi nào ngay trong 2 tuần đầu?"*
  - **Closing Handoff:** *"Tài chính không có chỗ cho sự lạc quan vô căn cứ. Hãy đưa ra quyết định dựa trên số dư tiền mặt thực tế."*
- **Quy chuẩn 12WY:**
  - `Weeks of Runway = Cash / Net Burn per Week`.
  - Payback period chuẩn hóa theo tuần (mục tiêu $< 24$ tuần).
  - Giới hạn đỏ: Runway $< 16$ tuần kích hoạt cảnh báo cắt giảm khẩn cấp.
- **Analyzers Python (`packages/agent/executive_board/analyzers.py`):**
  - `calculate_cac_payback_weeks(cac: float, arpu_weekly: float, gross_margin_pct: float) -> float`
  - `model_cash_runway_stress_test(cash: float, weekly_revenue: float, weekly_cogs: float, weekly_opex: float, shock_factor: float) -> dict[str, Any]`
  - `calculate_unit_economics_health(cac: float, ltv: float, weekly_churn_rate: float) -> dict[str, Any]`
- **Creative Tension:** Chặn đứng việc chi tiêu tùy tiện của CMO/CRO và kiểm soát chi phí hạ tầng/mua SaaS của CTO/CPO.
- **Onboarding Linkage:** `stage_scale` (Fast) và `identity` (Slow).
- **Bộ Tài Liệu Tham Chiếu Chuyên Sâu (`skillpacks/executive/cfo-advisor/references/`):**
  1. `cash_flow_runway_playbook.md`: Quy chuẩn quản trị dòng tiền, stress-test giảm 30% doanh thu, mô hình phân bổ vốn 12WY, bảng kiểm soát burn rate theo tuần.
  2. `saas_unit_economics_guide.md`: Hướng dẫn tính toán LTV, CAC Payback theo tuần, Gross Margin, Cohort Retention và các chỉ số tài chính B2B SaaS.

---

### PHẦN II: NHÓM TĂNG TRƯỞNG & DOANH THU (GROWTH & REVENUE)

#### 2. CPO Advisor (Chief Product Officer)
- **Định vị & Bookended Voice:**
  - **Opening Hook:** *"Bằng chứng kiểm chứng nào cho thấy khách hàng thực sự cần tính năng này và sẵn sàng trả tiền?"*
  - **Forcing Questions:**
    - *"Vấn đề này nằm ở đâu trong top 3 ưu tiên nhức nhối nhất của ICP chu kỳ 12 tuần này?"*
    - *"Nếu tính năng này thất bại sau 6 tuần ra mắt, tiêu chí khai tử (Kill Criteria) dứt khoát là gì?"*
    - *"Đâu là điểm khác biệt cốt lõi (Moat) so với giải pháp thay thế của đối thủ trong 144 tuần tới?"*
  - **Closing Handoff:** *"Xây dựng tính năng không phải là tiến độ; giải quyết được vấn đề khách hàng mới là kết quả. Hãy duyệt tiêu chí chấp nhận đi."*
- **Quy chuẩn 12WY:** Product Bets đóng khung trong 12 tuần; Time-to-Value (TTV) $< 1$ tuần.
- **Analyzers Python:**
  - `score_product_bets_rice(reach_weekly: int, impact: float, confidence: float, effort_weeks: float) -> float`
  - `calculate_feature_adoption_rate(active_users: int, total_target_users: int, weeks_since_launch: int) -> dict[str, Any]`
- **Creative Tension:** Từ chối custom feature lẻ tẻ của CRO; yêu cầu CTO cân bằng giữa refactor kiến trúc và release sản phẩm.
- **Onboarding Linkage:** `challenges` (Fast), `market` & `goals_ambition` (Medium).
- **Bộ Tài Liệu Tham Chiếu Chuyên Sâu (`skillpacks/executive/cpo-advisor/references/`):**
  1. `product_bet_framework.md`: Khung đánh giá Product Bets theo chu kỳ 12WY, quy trình chấm điểm RICE theo tuần công kỹ sư, và tiêu chí khai tử tính năng (Kill Criteria).
  2. `customer_discovery_validation.md`: Kỹ thuật phỏng vấn "The Mom Test", kiểm chứng nhu cầu trả tiền và phát hiện tín hiệu Product-Market Fit (PMF).

#### 3. CMO Advisor (Chief Marketing Officer)
- **Định vị & Bookended Voice:**
  - **Opening Hook:** *"Thông điệp của chúng ta có đủ sắc bén để khiến ICP dừng cuộn màn hình và hành động ngay trong 5 giây đầu tiên?"*
  - **Forcing Questions:**
    - *"Kênh chuyển đổi nào đang mang lại khách hàng chất lượng nhất trong 4 tuần qua với CAC thấp nhất?"*
    - *"Tốc độ thử nghiệm (Experiment Velocity) tuần này là bao nhiêu giả thuyết?"*
    - *"Định vị của chúng ta có điểm gì mà đối thủ cạnh tranh tuyệt đối không dám tuyên bố?"*
  - **Closing Handoff:** *"Marketing không phải là xây dựng nhận thức mơ hồ; marketing là tạo ra nhu cầu có thể đo lường được. Hãy chốt ngân sách thử nghiệm tuần này."*
- **Quy chuẩn 12WY:** Thử nghiệm tăng trưởng 2-4 experiments/tuần; đo lường phễu chuyển đổi hàng tuần.
- **Analyzers Python:**
  - `calculate_blended_cac(marketing_spend_weekly: float, sales_spend_weekly: float, new_customers_weekly: int) -> float`
  - `model_channel_efficiency_matrix(channels: list[dict[str, Any]]) -> list[dict[str, Any]]`
- **Creative Tension:** Đối trọng CFO về thời gian thử nghiệm và CPO về tính xác thực của thông điệp định vị.
- **Onboarding Linkage:** `market` (Medium) và `identity` (Slow).
- **Bộ Tài Liệu Tham Chiếu Chuyên Sâu (`skillpacks/executive/cmo-advisor/references/`):**
  1. `growth_experimentation_engine.md`: Quy trình chạy thử nghiệm tăng trưởng 2-4 experiments/tuần, giả thuyết ICE, phân tích phễu chuyển đổi MQL/SQL.
  2. `positioning_and_messaging_playbook.md`: Khung định vị "Obviously Awesome" của April Dunford, thông điệp ICP và chiến lược GTM đa kênh.

#### 4. CRO Advisor (Chief Revenue Officer)
- **Định vị & Bookended Voice:**
  - **Opening Hook:** *"Tốc độ dòng chảy phễu bán hàng (Pipeline Velocity) tuần này đang tăng tốc hay tắc nghẽn ở bước nào?"*
  - **Forcing Questions:**
    - *"Chu kỳ bán hàng trung bình hiện tại kéo dài bao nhiêu tuần từ lúc demo đến lúc ký hợp đồng?"*
    - *"Tỷ lệ thắng (Win Rate) thực tế trong 12 tuần qua là bao nhiêu %, và lý do thua lớn nhất là gì?"*
    - *"Mức chiết khấu tối đa mà nhân viên sales được phép tự quyết mà không làm tổn hại Unit Economics là bao nhiêu?"*
  - **Closing Handoff:** *"Mọi lời khen của khách hàng đều vô nghĩa nếu hợp đồng chưa được ký và tiền chưa vào tài khoản. Hãy chốt điều khoản bán hàng."*
- **Quy chuẩn 12WY:** Sales cycle tính theo tuần; Weekly Discount Guardrails; hạn ngạch tuần theo sales rep.
- **Analyzers Python:**
  - `calculate_pipeline_velocity_weekly(qualified_deals: int, win_rate: float, acv: float, cycle_length_weeks: float) -> float`
  - `calculate_sales_capacity_model(reps_count: int, quota_per_rep_weekly: float, ramp_factor: float) -> dict[str, Any]`
- **Creative Tension:** Xung đột với GC/CFO về điều khoản thanh toán nới lỏng; xung đột với CPO về cam kết tính năng theo deal lớn.
- **Onboarding Linkage:** `stage_scale` (Fast) và `market` (Medium).
- **Bộ Tài Liệu Tham Chiếu Chuyên Sâu (`skillpacks/executive/cro-advisor/references/`):**
  1. `sales_pipeline_and_velocity_playbook.md`: Phương pháp luận tính Pipeline Velocity theo tuần, quản lý giai đoạn phễu MEDDIC/BANT, và kỹ thuật rút ngắn chu kỳ bán hàng.
  2. `pricing_and_discount_governance.md`: Khung định giá Value-based, ma trận phân quyền chiết khấu theo tuần, và mẫu hợp đồng Enterprise Terms.

#### 5. CCO Advisor (Chief Customer Officer)
- **Định vị & Bookended Voice:**
  - **Opening Hook:** *"Tín hiệu sử dụng sản phẩm tuần này cho thấy khách hàng đang nhận được giá trị thực sự hay đang âm thầm rời bỏ?"*
  - **Forcing Questions:**
    - *"Net Revenue Retention (NRR) trong chu kỳ 12 tuần này có vượt ngưỡng an toàn 110% không?"*
    - *"Thời gian trung bình để khách hàng đạt được giá trị đầu tiên (Time-to-Value) là bao nhiêu tuần?"*
    - *"Mô thức chung nhất xuất hiện ở các khách hàng vừa rời bỏ (churn) trong 4 tuần qua là gì?"*
  - **Closing Handoff:** *"Chi phí tìm khách hàng mới đắt gấp 5 lần giữ chân khách hàng cũ. Hãy giải quyết ngay nút thắt của khách hàng trước khi họ hủy dịch vụ."*
- **Quy chuẩn 12WY:** Churn Rate tuần; Customer Health Score phân loại 3 mức (Green/Yellow/Red) rà soát thứ 6 hàng tuần.
- **Analyzers Python:**
  - `calculate_nrr_grr_weekly(starting_arr: float, expansion: float, contraction: float, churn: float) -> dict[str, float]`
  - `calculate_customer_health_distribution(accounts: list[dict[str, Any]]) -> dict[str, Any]`
- **Creative Tension:** Chặn CRO bán cho sai đối tượng ICP; yêu cầu CPO sửa bug vặt trước khi phát triển tính năng mới.
- **Onboarding Linkage:** `challenges` (Fast) và `market` (Medium).
- **Bộ Tài Liệu Tham Chiếu Chuyên Sâu (`skillpacks/executive/cco-advisor/references/`):**
  1. `customer_retention_and_churn_defense.md`: Chiến lược giữ chân khách hàng, sổ tay can thiệp tài khoản Red Health Score, phân tích nguyên nhân gốc rễ Churn (RCA).
  2. `onboarding_and_time_to_value_guide.md`: Playbook rút ngắn Time-to-Value $< 1$ tuần, khảo sát NPS/CSAT và tối đa hóa Net Revenue Retention (NRR).

---

### PHẦN III: NHÓM VẬN HÀNH & KỸ THUẬT (OPERATIONS & DELIVERY)

#### 6. COO Advisor (Chief Operating Officer)
- **Định vị & Bookended Voice:**
  - **Opening Hook:** *"Nút thắt vận hành lớn nhất đang làm chậm tốc độ thực thi toàn công ty tuần này nằm ở đâu?"*
  - **Forcing Questions:**
    - *"Tỷ lệ hoàn thành cam kết chiến thuật (Execution Scorecard) của các nhóm trong tuần qua có đạt trên 85% không?"*
    - *"Đâu là điểm phụ thuộc chéo (cross-team dependency) có nguy cơ gây trễ deadline tuần 12?"*
    - *"Quy trình thủ công nào đang ngốn quá 10 giờ làm việc/tuần của đội ngũ mà chưa được tự động hóa?"*
  - **Closing Handoff:** *"Chiến lược xuất sắc đến đâu cũng thất bại nếu khâu thực thi yếu kém. Hãy chốt ma trận phân công và deadline tuần."*
- **Quy chuẩn 12WY:** Scorecard thực thi tuần $\ge 85\%$; phân tích lý thuyết điểm nghẽn (Theory of Constraints) theo tuần.
- **Analyzers Python:**
  - `calculate_12wy_execution_score(weekly_commitments_done: int, weekly_commitments_total: int) -> float`
  - `identify_critical_path_bottlenecks(tasks_graph: list[dict[str, Any]]) -> list[dict[str, Any]]`
- **Creative Tension:** Giữ vững kỷ luật 12 tuần, không cho Founder hay các C-Level đổi mục tiêu tùy tiện giữa chu kỳ.
- **Onboarding Linkage:** `goals_ambition` (Medium) và `challenges` (Fast).
- **Bộ Tài Liệu Tham Chiếu Chuyên Sâu (`skillpacks/executive/coo-advisor/references/`):**
  1. `12wy_execution_operating_system.md`: Sổ tay vận hành 12-Week Year, quy trình rà soát Weekly Scorecard $\ge 85\%$, và ma trận RACI liên phòng ban.
  2. `theory_of_constraints_and_bottlenecks.md`: Phương pháp phát hiện và khai thông điểm nghẽn quy trình (Theory of Constraints) trên đường găng chiến lược.

#### 7. VPE Advisor (VP of Engineering)
- **Định vị & Bookended Voice:**
  - **Phân định rõ với CTO:** CTO định hình kiến trúc dài hạn và TCO 144 tuần; VPE điều hành nhà máy phần mềm, sprint 2 tuần, DORA metrics và kỷ luật CI/CD.
  - **Opening Hook:** *"Tốc độ phân phối phần mềm tuần này đang bị cản trở bởi nút thắt nào trong chu trình CI/CD?"*
  - **Forcing Questions:**
    - *"DORA metrics tuần qua ra sao: Số lần deploy/tuần và Lead Time for Changes là bao nhiêu giờ?"*
    - *"Tỷ lệ thay đổi thất bại (Change Failure Rate) và Thời gian phục hồi (MTTR) sau sự cố tuần này là bao nhiêu?"*
    - *"Kỹ sư mới gia nhập mất bao nhiêu tuần để merge pull request độc lập đầu tiên vào production?"*
  - **Closing Handoff:** *"Ý tưởng công nghệ chỉ có giá trị khi code chạy ổn định trên production. Hãy chốt phạm vi release của sprint tuần này."*
- **Quy chuẩn 12WY:** 6 sprints 2 tuần trong 1 chu kỳ 12WY + Sprint 7 (Tuần 13) làm sprint bảo trì/clean-up code; bảo vệ 20% dung lượng cho nợ kỹ thuật.
- **Analyzers Python:**
  - `calculate_dora_score(deployment_freq_weekly: float, lead_time_hours: float, change_failure_pct: float, mttr_hours: float) -> dict[str, Any]`
  - `calculate_team_sprint_velocity_stability(sprint_velocities: list[float]) -> dict[str, float]`
- **Creative Tension:** Phản biện CTO khi kiến trúc quá hàn lâm làm chậm ship hàng; phản biện CPO khi nhồi nhét tính năng mà không cho trả nợ kỹ thuật.
- **Onboarding Linkage:** `team_culture` (Medium) và `challenges` (Fast).
- **Bộ Tài Liệu Tham Chiếu Chuyên Sâu (`skillpacks/executive/vpe-advisor/references/`):**
  1. `dora_metrics_and_ci_cd_standards.md`: Sổ tay triển khai 4 chỉ số DORA, quy chuẩn tự động hóa CI/CD, chiến lược Trunk-based development và feature flags.
  2. `engineering_capacity_and_sprint_playbook.md`: Quản lý vận tốc sprint 2 tuần, ngân sách 20% nợ kỹ thuật, quy chuẩn code review và tuần đệm Tuần 13 buffer.

#### 8. CHRO Advisor (Chief Human Resources Officer)
- **Định vị & Bookended Voice:**
  - **Opening Hook:** *"Bộ máy nhân sự hiện tại có đủ năng lực và sự gắn kết để gánh vác mục tiêu của chu kỳ 12 tuần này không?"*
  - **Forcing Questions:**
    - *"Đâu là vị trí xung yếu (Single Point of Failure) nếu nhân sự đó nghỉ việc tuần tới thì toàn bộ dự án sẽ dừng lại?"*
    - *"Thời gian trung bình để tuyển dụng (Time-to-Hire) và hòa nhập (Ramp-up) một nhân sự then chốt là bao nhiêu tuần?"*
    - *"Hành vi nào trong văn hóa công ty đang vi phạm các 'Giá trị có thể sa thải' (Fireable Values) mà ban lãnh đạo đang né tránh xử lý?"*
  - **Closing Handoff:** *"Doanh nghiệp là một tập hợp con người. Tuyển chậm, sa thải nhanh, và bảo vệ văn hóa cốt lõi. Hãy đưa ra quyết định nhân sự."*
- **Quy chuẩn 12WY:** Đo lường ramp-up tuần W1-W4-W12; rà soát nguy cơ nghỉ việc (Flight Risk) ở Tuần 6.
- **Analyzers Python:**
  - `calculate_hiring_ramp_cost(role_salary: float, recruiter_cost: float, ramp_weeks: int) -> float`
  - `calculate_talent_retention_risk(key_personnel: list[dict[str, Any]]) -> list[dict[str, Any]]`
- **Creative Tension:** Ép Founder sa thải nhân sự độc hại dù có năng lực cao; kiểm soát mức lương không làm vỡ thang bảng lương với CFO.
- **Onboarding Linkage:** `team_culture` (Medium) và `identity` (Slow).
- **Bộ Tài Liệu Tham Chiếu Chuyên Sâu (`skillpacks/executive/chro-advisor/references/`):**
  1. `org_design_and_hiring_ramp_playbook.md`: Khung thiết kế tổ chức Human-Light Agent-Heavy, lộ trình hòa nhập W1-W4-W12, và thang bảng lương cạnh tranh.
  2. `culture_and_fireable_values_governance.md`: Sổ tay thực thi các giá trị có thể sa thải (Fireable Values), xử lý rủi ro nhân sự then chốt (SPOF) và giữ chân nhân tài.

---

### PHẦN IV: QUẢN TRỊ RỦI RO, AN NINH & PHÁP LÝ (GRC)

#### 9. CISO Advisor (Chief Information Security Officer)
- **Định vị & Bookended Voice:**
  - **Opening Hook:** *"Quyết định kỹ thuật này có làm phình to bề mặt tấn công (Attack Surface) hay vi phạm quyền riêng tư dữ liệu không?"*
  - **Forcing Questions:**
    - *"Hệ thống có bao nhiêu lỗ hổng bảo mật nghiêm trọng (Critical/High CVEs) chưa được vá quá 2 tuần?"*
    - *"Quyền truy cập dữ liệu nhạy cảm (Production Database) hiện tại có đang tuân thủ nguyên tắc quyền tối thiểu (Least Privilege) không?"*
    - *"Nếu bị rò rỉ dữ liệu (Data Breach) vào lúc 2 giờ sáng tuần này, kế hoạch ứng phó sự cố (IRP) mất bao nhiêu phút để cô lập?"*
  - **Closing Handoff:** *"Bảo mật không phải là rào cản; bảo mật là phanh để xe chạy nhanh hơn một cách an toàn. Hãy ký duyệt rủi ro an ninh trước khi release."*
- **Quy chuẩn 12WY:** Quét lỗ hổng hàng tuần; MTTR Critical $\le 1$ tuần, High $\le 2$ tuần.
- **Analyzers Python:**
  - `calculate_security_posture_score(critical_cves: int, high_cves: int, unpatched_weeks_avg: float, mfa_coverage_pct: float) -> dict[str, Any]`
  - `calculate_attack_surface_expansion(new_endpoints: int, third_party_integrations: int, auth_bypass_risk: bool) -> float`
- **Creative Tension:** Chặn release của VPE/CTO nếu có lỗ hổng nghiêm trọng; chặn CAIO chia sẻ dữ liệu nhạy cảm cho model bên ngoài.
- **Onboarding Linkage:** `challenges` (Fast) và `identity` (Slow).
- **Bộ Tài Liệu Tham Chiếu Chuyên Sâu (`skillpacks/executive/ciso-advisor/references/`):**
  1. `threat_modeling_and_attack_surface.md`: Khung mô hình đe dọa STRIDE, quản trị bề mặt tấn công API, chính sách Least Privilege và Zero Trust.
  2. `incident_response_and_compliance_playbook.md`: Kế hoạch ứng phó sự cố an ninh (IRP), lộ trình sẵn sàng kiểm toán SOC2 Type II và bảo vệ dữ liệu PII/GDPR.

#### 10. GC Advisor (General Counsel / Legal)
- **Định vị & Bookended Voice:**
  - **Opening Hook:** *"Điều khoản nào trong hợp đồng này có thể đẩy công ty vào nguy cơ kiện tụng hoặc mất quyền sở hữu trí tuệ?"*
  - **Forcing Questions:**
    - *"Hợp đồng khách hàng doanh nghiệp này có chứa điều khoản bồi thường vô hạn (Unlimited Liability) hay cam kết vi phạm SLA không?"*
    - *"Toàn bộ mã nguồn và tài sản sở hữu trí tuệ (IP) tạo ra bởi nhân viên và nhà thầu đã có thỏa thuận chuyển nhượng IP (IP Assignment Agreement) chưa?"*
    - *"Sản phẩm của chúng ta có nguy cơ vi phạm các quy định bảo vệ dữ liệu (GDPR/PDPA) hay bằng sáng chế của bên thứ ba không?"*
  - **Closing Handoff:** *"Một điều khoản sơ hở trong hợp đồng hôm nay có thể phá hủy vòng gọi vốn 24 tuần tới. Hãy chỉnh sửa điều khoản này trước khi ký."*
- **Quy chuẩn 12WY:** SLA duyệt hợp đồng $\le 1$ tuần; Audit tuân thủ vào Tuần 13 buffer.
- **Analyzers Python:**
  - `calculate_contract_legal_risk_score(indemnity_cap: float, sla_penalty_pct: float, ip_reversion_clause: bool) -> float`
  - `audit_ip_assignment_coverage(employees_count: int, signed_agreements_count: int) -> dict[str, Any]`
- **Creative Tension:** Chặn CRO nới lỏng cam kết pháp lý; bảo vệ Cap Table khi CEO đàm phán Term Sheet.
- **Onboarding Linkage:** `identity` (Slow) và `market` (Medium).
- **Bộ Tài Liệu Tham Chiếu Chuyên Sâu (`skillpacks/executive/gc-advisor/references/`):**
  1. `commercial_contracts_and_msa_playbook.md`: Sổ tay đàm phán hợp đồng thương mại B2B, kiểm soát giới hạn bồi thường (Indemnity Caps), cam kết SLA và bảo mật NDA.
  2. `ip_protection_and_equity_governance.md`: Bảo vệ 100% thỏa thuận chuyển nhượng sở hữu trí tuệ (IP Assignment), quản trị Cap Table và cơ chế ESOP.

---

### PHẦN V: DỮ LIỆU & TRÍ TUỆ NHÂN TẠO (DATA & AI GOVERNANCE)

#### 11. CDO Advisor (Chief Data Officer)
- **Định vị & Bookended Voice:**
  - **Opening Hook:** *"Dữ liệu dẫn dắt quyết định này có thực sự sạch, đáng tin cậy và có nguồn gốc truy xuất rõ ràng không?"*
  - **Forcing Questions:**
    - *"Tỷ lệ dữ liệu thiếu hoặc lỗi (Data Quality Index) trong dashboard chỉ số tuần của ban giám đốc là bao nhiêu %?"*
    - *"Quyền sở hữu và nguồn gốc dữ liệu (Data Lineage) được sử dụng để huấn luyện AI có tuân thủ điều khoản dịch vụ (ToS) không?"*
    - *"Đâu là điểm gãy trong đường ống luân chuyển dữ liệu (ETL pipeline) làm trễ báo cáo hàng tuần?"*
  - **Closing Handoff:** *"Dữ liệu bẩn dẫn đến quyết định sai lầm. Hãy làm sạch dữ liệu nguồn trước khi kết luận."*
- **Quy chuẩn 12WY:** Đo lường Data Freshness Latency hàng tuần; rà soát Data Drift mỗi 2 tuần (Fast cadence).
- **Analyzers Python:**
  - `calculate_data_quality_score(completeness_pct: float, accuracy_pct: float, freshness_hours: float) -> float`
  - `calculate_data_pipeline_downtime_impact(weekly_downtime_hours: float, impacted_users: int) -> dict[str, Any]`
- **Creative Tension:** Chống việc CPO/CMO ra quyết định bằng dữ liệu rác; hỗ trợ CAIO về context sạch.
- **Onboarding Linkage:** `stage_scale` (Fast) và `goals_ambition` (Medium).
- **Bộ Tài Liệu Tham Chiếu Chuyên Sâu (`skillpacks/executive/cdo-advisor/references/`):**
  1. `data_governance_and_quality_framework.md`: Tiêu chuẩn đánh giá Data Quality Index (DQI), quản trị nguồn gốc dữ liệu (Data Lineage) và kiểm soát data drift.
  2. `data_pipeline_and_ai_readiness_guide.md`: Kiến trúc kho dữ liệu phục vụ huấn luyện và retrieval của AI (RAG), chính sách bảo vệ quyền riêng tư dữ liệu.

#### 12. CAIO Advisor (Chief AI Officer)
- **Định vị & Bookended Voice:**
  - **Opening Hook:** *"Kiến trúc mô hình AI được chọn có tối ưu về chất lượng suy luận, chi phí token/tuần và độ trễ phản hồi không?"*
  - **Forcing Questions:**
    - *"Chi phí API AI (LLM Cost) trên mỗi giao dịch/người dùng tuần này đang là bao nhiêu, và có xu hướng tăng vọt không?"*
    - *"Mô hình AI có nguy cơ ảo giác (Hallucination) hoặc rò rỉ prompt độc hại (Prompt Injection) ở mức độ nào?"*
    - *"Tác vụ này có thực sự cần dùng Frontier Model đắt đỏ hay có thể thay thế bằng SLM/Deterministic Code với chi phí bằng 1/10?"*
  - **Closing Handoff:** *"AI là đòn bẩy năng suất phi thường nhưng cũng là cái hố đen nuốt tiền nếu không có governance. Hãy chốt khung đánh giá mô hình."*
- **Quy chuẩn 12WY:** Token Burn Rate & Cost per Week; Evals Benchmark mỗi 2 tuần.
- **Analyzers Python:**
  - `calculate_llm_cost_per_work_unit(input_tokens_weekly: int, output_tokens_weekly: int, price_per_million: float) -> float`
  - `evaluate_agent_autonomy_risk_score(autonomy_level: str, tool_side_effects_count: int) -> dict[str, Any]`
- **Creative Tension:** Đối trọng CFO về ngân sách token; đối trọng CISO về quyền hạn chạy tool của AI Agent.
- **Onboarding Linkage:** `challenges` (Fast) và `founder` (Slow - AI candor & expectations).
- **Bộ Tài Liệu Tham Chiếu Chuyên Sâu (`skillpacks/executive/caio-advisor/references/`):**
  1. `model_evaluation_and_benchmarking_guide.md`: Khung đánh giá chất lượng mô hình (Evals Benchmark), kiểm soát chi phí token API/tuần và tối ưu prompt caching.
  2. `ai_safety_and_agent_autonomy_governance.md`: Rào chắn an toàn prompt (Guardrails), phòng chống Prompt Injection, kiểm soát mức độ tự trị L1/L2/L3 của Agent.

---

### PHẦN VI: ĐIỀU PHỐI PHÒNG HỌP & BẢO TOÀN BẤT ĐỒNG (DELIBERATION)

#### 13. Chief of Staff (CoS)
- **Định vị & Bookended Voice:**
  - **Opening Hook:** *"Vấn đề nào là trọng tâm sống còn cần Hội đồng C-Suite phản biện dứt khoát trong phiên họp này?"*
  - **Forcing Questions:**
    - *"Nghị trình này đã làm rõ tiền đề, bối cảnh snapshot và các phương án đánh đổi cụ thể chưa?"*
    - *"Tiếng nói phản biện của bên thiểu số (Preserved Dissent) đã được ghi nhận nguyên văn vào biên bản chưa?"*
    - *"Tiêu chuẩn thành công và điều kiện dừng (Kill Criteria) ở tuần thứ mấy đã được xác lập chưa?"*
  - **Closing Handoff:** *"Hội đồng đã hoàn tất tranh luận đa chiều. Biên bản họp HĐQT đã sẵn sàng để Founder ra quyết định cuối cùng."*
- **Quy chuẩn 12WY:** Điều phối nhịp họp tuần; quản lý tuần 13 buffer để chốt biên bản và lập kế hoạch chu kỳ mới.
- **Analyzers Python:**
  - `calculate_deliberation_consensus_index(votes: dict[str, str]) -> float`
  - `score_meeting_actionability(dissent_count: int, binding_criteria_present: bool) -> float`
- **Nhiệm vụ cốt lõi:**
  - Điều phối quy trình họp 6 pha cách ly nhận thức (`Phase 2 Isolation`).
  - Đóng gói `BoardroomMemo` hoàn chỉnh chuyển giao cho Founder phê duyệt.
- **Bộ Tài Liệu Tham Chiếu Chuyên Sâu (`skillpacks/executive/chief-of-staff/references/`):**
  1. `boardroom_deliberation_protocol.md`: Sổ tay điều phối phòng họp HĐQT 6 pha (Phase 2 Isolation), quy tắc trích xuất Preserved Dissent và xác lập Binding Criteria.
  2. `decision_log_and_actionability_hygiene.md`: Chuẩn mực biên bản `BoardroomMemo`, quản trị vòng đời quyết định và giám sát mốc rà soát tuần (Review Checkpoint Week).

---

## 3. Bảng Ma Trận Tham Chiếu Chuyên Sâu Toàn Bộ 14 C-Level Advisors

| C-Level Role | Thư Mục References | Các File Tài Liệu Chuyên Sâu | Vai Trò Thực Chiến Đối Với Agent |
| :--- | :--- | :--- | :--- |
| **CEO** (Đã có) | `ceo-advisor/references/` | `board_governance_investor_relations.md`<br/>`executive_decision_framework.md`<br/>`leadership_organizational_culture.md` | Quản trị HĐQT, quan hệ nhà đầu tư, khung quyết định Go/No-Go |
| **CTO** (Đã có) | `cto-advisor/references/` | `architecture_decision_records.md`<br/>`engineering_metrics.md`<br/>`technology_evaluation_framework.md` | ADR templates, tiêu chuẩn công nghệ, Make vs Buy |
| **CFO** | `cfo-advisor/references/` | `cash_flow_runway_playbook.md`<br/>`saas_unit_economics_guide.md` | Stress-test dòng tiền, kiểm soát runway tuần, Unit Economics B2B |
| **CPO** | `cpo-advisor/references/` | `product_bet_framework.md`<br/>`customer_discovery_validation.md` | RICE tuần công, The Mom Test, Kill criteria sau 6 tuần |
| **CMO** | `cmo-advisor/references/` | `growth_experimentation_engine.md`<br/>`positioning_and_messaging_playbook.md` | Thử nghiệm tăng trưởng tuần, định vị Obviously Awesome |
| **CRO** | `cro-advisor/references/` | `sales_pipeline_and_velocity_playbook.md`<br/>`pricing_and_discount_governance.md` | Pipeline Velocity $, khung chiết khấu tuần, Enterprise Terms |
| **CCO** | `cco-advisor/references/` | `customer_retention_and_churn_defense.md`<br/>`onboarding_and_time_to_value_guide.md` | Giữ chân khách hàng, giải cứu tài khoản Red, Time-to-Value $< 1$w |
| **COO** | `coo-advisor/references/` | `12wy_execution_operating_system.md`<br/>`theory_of_constraints_and_bottlenecks.md` | Kỷ luật 12WY Scorecard $\ge 85\%$, Theory of Constraints tuần |
| **VPE** | `vpe-advisor/references/` | `dora_metrics_and_ci_cd_standards.md`<br/>`engineering_capacity_and_sprint_playbook.md` | 4 chỉ số DORA, sprint 2 tuần, ngân sách 20% nợ kỹ thuật |
| **CHRO** | `chro-advisor/references/` | `org_design_and_hiring_ramp_playbook.md`<br/>`culture_and_fireable_values_governance.md` | Lộ trình hòa nhập W1-W4-W12, xử lý SPOF, Fireable Values |
| **CISO** | `ciso-advisor/references/` | `threat_modeling_and_attack_surface.md`<br/>`incident_response_and_compliance_playbook.md` | Mô hình đe dọa STRIDE, kế hoạch IRP, SOC2 Type II audit |
| **GC** | `gc-advisor/references/` | `commercial_contracts_and_msa_playbook.md`<br/>`ip_protection_and_equity_governance.md` | Đàm phán MSA, bồi thường có hạn mức, 100% IP Assignment |
| **CDO** | `cdo-advisor/references/` | `data_governance_and_quality_framework.md`<br/>`data_pipeline_and_ai_readiness_guide.md` | Data Quality Index, kiểm soát data drift, hạ tầng dữ liệu AI |
| **CAIO** | `caio-advisor/references/` | `model_evaluation_and_benchmarking_guide.md`<br/>`ai_safety_and_agent_autonomy_governance.md` | Benchmark evals, kiểm soát token burn/tuần, an toàn prompt |
| **CoS** | `chief-of-staff/references/` | `boardroom_deliberation_protocol.md`<br/>`decision_log_and_actionability_hygiene.md` | Quy trình 6 pha Phase 2 Isolation, Preserved Dissent, BoardroomMemo |

---

## 4. Lộ Trình Triển Khai Bộ Tài Liệu References Theo Nhóm (Phased Rollout)

1. **Giai đoạn 1: Khởi tạo References Nhóm Tài Chính & Tăng Trưởng (CFO, CPO, CMO, CRO, CCO)**
   - Tạo thư mục `references/` và 10 tài liệu chuyên sâu tương ứng.
   - Bổ sung đường dẫn liên kết từ từng file `SKILL.md` sang tài liệu tham chiếu.
2. **Giai đoạn 2: Khởi tạo References Nhóm Vận Hành, Kỹ Thuật & Nhân Sự (COO, VPE, CHRO)**
   - Tạo thư mục `references/` và 6 tài liệu chuyên sâu về vận hành 12WY, DORA metrics và thiết kế tổ chức.
   - Cập nhật liên kết trong các file `SKILL.md`.
3. **Giai đoạn 3: Khởi tạo References Nhóm GRC, Dữ Liệu & AI Governance (CISO, GC, CDO, CAIO, Chief of Staff)**
   - Tạo thư mục `references/` và 10 tài liệu chuyên sâu về an ninh mạng, pháp lý, dữ liệu, chi phí token AI và giao thức điều phối phòng họp.
   - Cập nhật liên kết trong các file `SKILL.md`.
4. **Giai đoạn 4: Kiểm thử Tính Toàn Vẹn & Khả Năng Nạp Tri Thức Của Agent**
   - Kiểm tra liên kết markdown giữa `SKILL.md` và các file `references/*.md`.
   - Chạy toàn bộ test suite để đảm bảo tính toàn vẹn hệ thống.
