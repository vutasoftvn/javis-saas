import 'package:get/get.dart';
import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';
import '../../../data/models/stage_model.dart';

/// Mức độ bằng chứng hiện có của dự án
enum EvidenceMaturityLevel {
  unverified('NONE', 'Chưa khảo sát (Ý tưởng giả định)', 'Unverified (Idea / Assumption)'),
  initialConversations('INITIAL', 'Đã phỏng vấn 1–4 khách hàng tiềm năng', 'Interviewed 1–4 prospective customers'),
  validatedProblem('VALIDATED_PROBLEM', 'Đã xác thực với 5+ khách hàng (Nỗi đau rõ ràng)', 'Validated with 5+ customers (Urgent pain confirmed)'),
  activePrototypeOrRevenue('PROTOTYPE_REVENUE', 'Đã có Prototype/LOI/Doanh thu đầu tiên', 'Active Prototype / LOI / Initial revenue');

  const EvidenceMaturityLevel(this.wire, this.label, [String? labelEn])
      : labelEn = labelEn ?? label;

  final String wire;
  final String label;
  final String labelEn;

  String localizedLabel([bool isEn = false]) => isEn ? labelEn : label;

  static EvidenceMaturityLevel fromWire(String? wire) {
    return values.firstWhere(
      (e) => e.wire == wire,
      orElse: () => EvidenceMaturityLevel.unverified,
    );
  }
}

/// Dữ liệu gợi ý cho từng Stage để dẫn dắt Founder
class StageGuidanceTemplate {
  final ProjectStage stage;
  final String stageTag;
  final String focusHeadline;
  final String customerHint;
  final String problemHint;
  final List<String> coreAssumptions;
  final List<String> suggestedFirstWeekActions;
  final String suggestedOutcomeTemplate;

  const StageGuidanceTemplate({
    required this.stage,
    required this.stageTag,
    required this.focusHeadline,
    required this.customerHint,
    required this.problemHint,
    required this.coreAssumptions,
    required this.suggestedFirstWeekActions,
    required this.suggestedOutcomeTemplate,
  });
}

/// Kho tri thức phân tích theo từng giai đoạn dự án (P0 -> P6)
class StageAnalysisKnowledge {
  static Map<ProjectStage, StageGuidanceTemplate> get templates => templatesVi;

  static const Map<ProjectStage, StageGuidanceTemplate> templatesVi = {
    ProjectStage.p0Discovery: StageGuidanceTemplate(
      stage: ProjectStage.p0Discovery,
      stageTag: 'P0: Khám phá & Đánh giá cơ hội',
      focusHeadline: 'Xác định rõ tệp khách hàng tiên phong (Early Adopter) và tìm kiếm tín hiệu thị trường đầu tiên.',
      customerHint: 'VD: Founder startup B2B SaaS tại Việt Nam có dưới 10 nhân sự',
      problemHint: 'VD: Khó khăn trong việc duy trì kỷ luật thực thi OKR và quản trị mục tiêu tuần giữa các phòng ban',
      coreAssumptions: [
        'Khách hàng mục tiêu đang chủ động tìm kiếm giải pháp thay thế cho bảng tính Excel/Notion.',
        'Khách hàng sẵn sàng dành 20-30 phút phỏng vấn chuyên sâu về quy trình hiện tại.',
        'Nỗi đau này đủ nhức nhối để họ chi trả ít nhất 100\$/tháng nếu được giải quyết.',
      ],
      suggestedFirstWeekActions: [
        'Lập danh sách 15 khách hàng tiềm năng phù hợp hồ sơ ICP.',
        'Thực hiện tối thiểu 3 cuộc phỏng vấn khám phá vấn đề (Discovery Interviews).',
        'Tổng hợp 3 điểm nghẽn lớn nhất từ các cuộc trò chuyện vào tài liệu bằng chứng.',
      ],
      suggestedOutcomeTemplate: 'Hoàn thành 3 cuộc phỏng vấn khách hàng tiềm năng và xác định ít nhất 1 nỗi đau cốt lõi có bằng chứng xác thực.',
    ),

    ProjectStage.p1ProblemValidation: StageGuidanceTemplate(
      stage: ProjectStage.p1ProblemValidation,
      stageTag: 'P1: Xác thực vấn đề & Mức độ sẵn sàng chi trả',
      focusHeadline: 'Đo lường tần suất và cường độ của nỗi đau; kiểm chứng khách hàng có sẵn lòng cam kết/đặt cọc.',
      customerHint: 'VD: Trưởng phòng Marketing các doanh nghiệp SME ngành thương mại điện tử',
      problemHint: 'VD: Chi phí chạy ads ngày càng tăng nhưng tỷ lệ chuyển đổi thấp do không cá nhân hoá được thông điệp',
      coreAssumptions: [
        'Vấn đề xảy ra hàng ngày và gây thất thoát chi phí/doanh thu có thể lượng hoá.',
        'Khách hàng đã thử ít nhất 2 giải pháp khác nhưng thất bại.',
        'Khách hàng sẵn sàng ký Thư ý định (LOI) hoặc tham gia chương trình Design Partner.',
      ],
      suggestedFirstWeekActions: [
        'Thiết kế kịch bản phỏng vấn chuyên sâu Problem/Willingness-to-pay.',
        'Gặp 5 khách hàng để kiểm tra phản ứng với mức giá dự kiến.',
        'Thu thập ít nhất 1 cam kết thử nghiệm (Letter of Intent / Đặt cọc).',
      ],
      suggestedOutcomeTemplate: 'Có ít nhất 2 khách hàng xác nhận sẽ dùng thử và chấp nhận khung giá dự kiến khi sản phẩm ra mắt.',
    ),

    ProjectStage.p2SolutionValidation: StageGuidanceTemplate(
      stage: ProjectStage.p2SolutionValidation,
      stageTag: 'P2: Xác thực giải pháp & Prototype',
      focusHeadline: 'Kiểm tra xem giải pháp/prototype có giải quyết dứt điểm nỗi đau với trải nghiệm mượt mà không.',
      customerHint: 'VD: Giám đốc vận hành (COO) chuỗi bán lẻ 5-20 cửa hàng',
      problemHint: 'VD: Tồn kho thực tế lệch với số liệu phần mềm, mất 2 tiếng mỗi ngày để đối soát',
      coreAssumptions: [
        'Người dùng có thể hoàn thành luồng nghiệp vụ chính trong vòng 5 phút mà không cần đào tạo phức tạp.',
        'Tính năng cốt lõi (Core Feature) mang lại giá trị "Aha moment" ngay lần dùng đầu.',
        'Tỷ lệ phản hồi hài lòng sau khi test Prototype đạt trên 70%.',
      ],
      suggestedFirstWeekActions: [
        'Demo bản Clickable Prototype/Figma cho 3 khách hàng mục tiêu.',
        'Ghi nhận bảng Usability Feedback và các câu hỏi thắc mắc thường gặp.',
        'Chốt danh sách phạm vi MVP tối thiểu (Scope Freeze) cho tuần tới.',
      ],
      suggestedOutcomeTemplate: 'Hoàn thành bài kiểm tra Prototype với 3 khách hàng và hoàn thiện bảng phạm vi tính năng MVP v1.0.',
    ),

    ProjectStage.p3BuildValidate: StageGuidanceTemplate(
      stage: ProjectStage.p3BuildValidate,
      stageTag: 'P3: Xây dựng MVP & Thử nghiệm thực tế',
      focusHeadline: 'Đưa phiên bản hoạt động đầu tiên (Working Software) vào tay người dùng thật và đo lường tỷ lệ giữ chân.',
      customerHint: 'VD: Nhóm 10 người dùng thử nghiệm tiên phong (Alpha Testers)',
      problemHint: 'VD: Cần tự động hoá việc trích xuất hóa đơn và đối soát thanh toán',
      coreAssumptions: [
        'Hệ thống xử lý ổn định luồng dữ liệu chính không phát sinh lỗi nghiêm trọng.',
        'Người dùng kích hoạt tài khoản và quay lại sử dụng ít nhất 3 lần/tuần.',
        'Khách hàng đánh giá giải pháp nhanh hơn ít nhất 3x so với cách làm cũ.',
      ],
      suggestedFirstWeekActions: [
        'Onboard 3 người dùng đầu tiên vào bản MVP hoạt động.',
        'Theo dõi phiên sử dụng và phỏng vấn sau 48h trải nghiệm.',
        'Sửa các lỗi cản trở luồng chính (Blocker bugs) được báo cáo.',
      ],
      suggestedOutcomeTemplate: 'Ít nhất 3 khách hàng hoàn thành trọn vẹn luồng tác vụ chính trên MVP thật và cung cấp dữ liệu đánh giá.',
    ),

    ProjectStage.p4GoToMarket: StageGuidanceTemplate(
      stage: ProjectStage.p4GoToMarket,
      stageTag: 'P4: Đưa sản phẩm ra thị trường (GTM)',
      focusHeadline: 'Xây dựng phễu chuyển đổi lặp lại được, xác định kênh phân phối hiệu quả nhất và chốt hợp đồng thương mại.',
      customerHint: 'VD: Doanh nghiệp phân khúc Tier-2 đang tìm giải pháp tối ưu vận hành',
      problemHint: 'VD: Thiếu công cụ chuyên dụng đồng bộ quy trình đa kênh',
      coreAssumptions: [
        'Chi phí thu hút khách hàng (CAC) thấp hơn 1/3 giá trị trọn đời (LTV).',
        'Kênh tiếp cận lạnh (Outbound/Content) đem lại tỷ lệ hẹn gặp trên 5%.',
        'Thời gian từ lúc tiếp cận đến khi chốt hợp đồng dưới 3 tuần.',
      ],
      suggestedFirstWeekActions: [
        'Khởi chạy chiến dịch tiếp cận 50 khách hàng tiềm năng qua kênh mục tiêu.',
        'Tối ưu hóa trang Landing Page & bảng giá dựa trên phản hồi thị trường.',
        'Thiết lập pipeline bán hàng và theo dõi tỷ lệ chuyển đổi qua các giai đoạn.',
      ],
      suggestedOutcomeTemplate: 'Tạo ra 5 cuộc hẹn demo chất lượng và chốt ít nhất 1 hợp đồng thương mại chính thức.',
    ),

    ProjectStage.p5OperateGrowth: StageGuidanceTemplate(
      stage: ProjectStage.p5OperateGrowth,
      stageTag: 'P5: Vận hành & Tăng trưởng (Operate & Grow)',
      focusHeadline: 'Mở rộng quy mô doanh thu, nâng cao NPS và tự động hóa quy trình chăm sóc khách hàng.',
      customerHint: 'VD: Toàn bộ tập khách hàng thuộc thị trường trọng điểm',
      problemHint: 'VD: Cần mở rộng sang phân khúc mới hoặc tăng doanh thu trung bình trên mỗi khách hàng (ARPU)',
      coreAssumptions: [
        'Tỷ lệ churn hàng tháng duy trì dưới 2%.',
        'Khách hàng hiện tại sẵn sàng giới thiệu sản phẩm cho đối tác khác (Net Promoter Score > 50).',
        'Hạ tầng hệ thống đáp ứng tải tăng gấp 5 lần mà không suy giảm hiệu năng.',
      ],
      suggestedFirstWeekActions: [
        'Đo lường chỉ số Net Churn và phân tích lý do huỷ dịch vụ (nếu có).',
        'Triển khai chương trình chăm sóc định kỳ cho nhóm khách hàng giá trị cao.',
        'Chuẩn hoá quy trình bàn giao (SOP) cho đội ngũ hỗ trợ và vận hành.',
      ],
      suggestedOutcomeTemplate: 'Đạt tăng trưởng 10% doanh số định kỳ hàng tháng (MRR) và giữ tỷ lệ hài lòng CSAT trên 90%.',
    ),

    ProjectStage.p6ScaleGovern: StageGuidanceTemplate(
      stage: ProjectStage.p6ScaleGovern,
      stageTag: 'P6: Mở rộng & Quản trị (Scale & Govern)',
      focusHeadline: 'Chuẩn hóa bộ máy, quản trị rủi ro, tối ưu hóa lợi nhuận và mở rộng thị trường quốc tế/chiều sâu.',
      customerHint: 'VD: Khách hàng quy mô Enterprise và thị trường khu vực',
      problemHint: 'VD: Đảm bảo tuân thủ bảo mật, kiểm toán, quản trị dòng tiền quy mô lớn',
      coreAssumptions: [
        'Bộ máy vận hành có khả năng tự trị cao với sự điều phối của AI Workforce.',
        'Đạt tiêu chuẩn an toàn thông tin và chính sách tuân thủ pháp lý cao cấp.',
        'Biên lợi nhuận gộp duy trì trên 75%.',
      ],
      suggestedFirstWeekActions: [
        'Rà soát ma trận rủi ro tuân thủ và chính sách bảo mật dữ liệu.',
        'Thiết lập hạn mức tự chủ (Autonomy Level) cho các AI Agent chuyên trách.',
        'Kiểm tra kế hoạch kinh doanh quý tiếp theo cùng Hội đồng quản trị/Nhà đầu tư.',
      ],
      suggestedOutcomeTemplate: 'Hoàn thiện khung quản trị rủi ro và xác lập OKRs chiến lược cho chu kỳ tăng trưởng mới.',
    ),
  };

  static const Map<ProjectStage, StageGuidanceTemplate> templatesEn = {
    ProjectStage.p0Discovery: StageGuidanceTemplate(
      stage: ProjectStage.p0Discovery,
      stageTag: 'P0: Discovery & Opportunity Evaluation',
      focusHeadline: 'Clearly identify early adopters and find initial market pull signals.',
      customerHint: 'e.g., Founder of B2B SaaS startup in Southeast Asia with under 10 employees',
      problemHint: 'e.g., Struggle maintaining OKR execution discipline and cross-department weekly alignment',
      coreAssumptions: [
        'Target customers actively search for alternatives to Excel/Notion spreadsheets.',
        'Customers are willing to spend 20–30 minutes for an in-depth discovery interview.',
        'The pain is urgent enough that they would pay at least \$100/month to solve it.',
      ],
      suggestedFirstWeekActions: [
        'Build a list of 15 potential leads matching ICP criteria.',
        'Conduct at least 3 problem discovery interviews.',
        'Synthesize top 3 bottlenecks from interviews into evidence documentation.',
      ],
      suggestedOutcomeTemplate: 'Complete 3 customer discovery interviews and identify at least 1 validated core pain point with evidence.',
    ),

    ProjectStage.p1ProblemValidation: StageGuidanceTemplate(
      stage: ProjectStage.p1ProblemValidation,
      stageTag: 'P1: Problem Validation & Willingness to Pay',
      focusHeadline: 'Measure pain frequency and intensity; validate customer willingness to commit or deposit.',
      customerHint: 'e.g., Marketing Director at SME e-commerce businesses',
      problemHint: 'e.g., Rising ad spend but low conversion rates due to lack of personalized messaging',
      coreAssumptions: [
        'The problem occurs daily and causes quantifiable cost or revenue loss.',
        'Customers have tried at least 2 alternative solutions but failed.',
        'Customers are willing to sign a Letter of Intent (LOI) or join as Design Partners.',
      ],
      suggestedFirstWeekActions: [
        'Design deep-dive interview script for problem urgency and willingness-to-pay.',
        'Meet 5 customers to test price elasticity and proposed pricing tiers.',
        'Secure at least 1 pilot commitment (Letter of Intent or pre-order deposit).',
      ],
      suggestedOutcomeTemplate: 'Have at least 2 customers commit to pilot usage and accept proposed pricing structure.',
    ),

    ProjectStage.p2SolutionValidation: StageGuidanceTemplate(
      stage: ProjectStage.p2SolutionValidation,
      stageTag: 'P2: Solution Validation & Prototype',
      focusHeadline: 'Validate whether the solution/prototype cleanly solves the core pain with a frictionless experience.',
      customerHint: 'e.g., Chief Operating Officer (COO) of retail chain with 5–20 stores',
      problemHint: 'e.g., Physical inventory diverges from ERP records, taking 2 hours daily to reconcile',
      coreAssumptions: [
        'Users can complete the primary workflow in under 5 minutes without complex training.',
        'Core feature delivers an "Aha moment" on the very first session.',
        'Satisfaction rating after testing the prototype exceeds 70%.',
      ],
      suggestedFirstWeekActions: [
        'Demo clickable prototype/Figma to 3 target customers.',
        'Compile usability feedback matrix and top frequently asked questions.',
        'Finalize and freeze minimum MVP scope for next week.',
      ],
      suggestedOutcomeTemplate: 'Complete prototype testing with 3 target customers and finalize MVP v1.0 feature scope.',
    ),

    ProjectStage.p3BuildValidate: StageGuidanceTemplate(
      stage: ProjectStage.p3BuildValidate,
      stageTag: 'P3: Build MVP & Real-world Validation',
      focusHeadline: 'Put the first working software version into real users\' hands and measure retention.',
      customerHint: 'e.g., Cohort of 10 pioneer alpha testers',
      problemHint: 'e.g., Need to automate invoice extraction and payment reconciliation',
      coreAssumptions: [
        'System reliably processes the primary data flow without critical blockers.',
        'Users activate their account and return at least 3 times per week.',
        'Customers report that the solution is at least 3x faster than their old workflow.',
      ],
      suggestedFirstWeekActions: [
        'Onboard first 3 real users onto working software MVP.',
        'Observe usage sessions and conduct 48-hour follow-up interviews.',
        'Fix all blocker bugs impeding primary user workflow.',
      ],
      suggestedOutcomeTemplate: 'At least 3 customers successfully complete the end-to-end core workflow on MVP and provide review metrics.',
    ),

    ProjectStage.p4GoToMarket: StageGuidanceTemplate(
      stage: ProjectStage.p4GoToMarket,
      stageTag: 'P4: Go-to-Market (GTM)',
      focusHeadline: 'Build a repeatable conversion funnel, identify the top distribution channel, and close commercial contracts.',
      customerHint: 'e.g., Tier-2 enterprise seeking operational efficiency tools',
      problemHint: 'e.g., Lack of dedicated tools to synchronize multi-channel operations',
      coreAssumptions: [
        'Customer Acquisition Cost (CAC) is under 1/3 of Customer Lifetime Value (LTV).',
        'Outbound and content cold channels generate an appointment booking rate above 5%.',
        'Sales cycle from initial outreach to contract signing is under 3 weeks.',
      ],
      suggestedFirstWeekActions: [
        'Launch outreach campaign to 50 target leads across primary channel.',
        'Optimize landing page and pricing table based on market feedback.',
        'Establish sales pipeline tracking conversion stages.',
      ],
      suggestedOutcomeTemplate: 'Generate 5 qualified demo meetings and close at least 1 commercial contract.',
    ),

    ProjectStage.p5OperateGrowth: StageGuidanceTemplate(
      stage: ProjectStage.p5OperateGrowth,
      stageTag: 'P5: Operate & Grow',
      focusHeadline: 'Scale recurring revenue, improve NPS, and automate customer lifecycle workflows.',
      customerHint: 'e.g., Full customer base in core target market',
      problemHint: 'e.g., Need to expand to adjacent segment or increase average revenue per user (ARPU)',
      coreAssumptions: [
        'Monthly churn rate stays below 2%.',
        'Existing customers actively refer peers (Net Promoter Score > 50).',
        'Infrastructure reliably scales to 5x load without performance degradation.',
      ],
      suggestedFirstWeekActions: [
        'Measure Net Churn metrics and diagnose cancellation root causes.',
        'Implement structured cadence reviews for high-value customer accounts.',
        'Standardize Standard Operating Procedures (SOP) for support and operations.',
      ],
      suggestedOutcomeTemplate: 'Achieve 10% month-over-month MRR growth while maintaining CSAT above 90%.',
    ),

    ProjectStage.p6ScaleGovern: StageGuidanceTemplate(
      stage: ProjectStage.p6ScaleGovern,
      stageTag: 'P6: Scale & Govern',
      focusHeadline: 'Standardize organizational governance, manage risk, optimize unit economics, and expand internationally.',
      customerHint: 'e.g., Enterprise-scale customers and regional markets',
      problemHint: 'e.g., Ensuring security compliance, audit trails, and large-scale treasury management',
      coreAssumptions: [
        'Operations achieve high autonomy orchestrated by AI Workforce agents.',
        'Meets enterprise-grade information security standards and regulatory compliance policies.',
        'Gross profit margin remains above 75%.',
      ],
      suggestedFirstWeekActions: [
        'Review compliance risk matrix and data protection policies.',
        'Configure autonomy level thresholds for specialized AI Agents.',
        'Audit next quarter business plan with Advisory Board / Investors.',
      ],
      suggestedOutcomeTemplate: 'Finalize comprehensive governance framework and establish strategic OKRs for next scale cycle.',
    ),
  };

  static StageGuidanceTemplate getTemplate(ProjectStage stage, [String? lang]) {
    final effectiveLang = lang ??
        ((Get.isRegistered<LocaleController>() &&
                Get.find<LocaleController>().current.value == SupportedLocale.enUS) ||
            Get.locale?.languageCode == 'en'
            ? 'en'
            : 'vi');

    if (effectiveLang == 'en') {
      return templatesEn[stage] ?? templatesEn[ProjectStage.p0Discovery]!;
    }
    return templatesVi[stage] ?? templatesVi[ProjectStage.p0Discovery]!;
  }
}
