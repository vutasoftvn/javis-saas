import '../../../data/models/stage_model.dart';

/// Mức độ bằng chứng hiện có của dự án
enum EvidenceMaturityLevel {
  unverified('NONE', 'Chưa khảo sát (Ý tưởng giả định)'),
  initialConversations('INITIAL', 'Đã phỏng vấn 1–4 khách hàng tiềm năng'),
  validatedProblem('VALIDATED_PROBLEM', 'Đã xác thực với 5+ khách hàng (Nỗi đau rõ ràng)'),
  activePrototypeOrRevenue('PROTOTYPE_REVENUE', 'Đã có Prototype/LOI/Doanh thu đầu tiên');

  const EvidenceMaturityLevel(this.wire, this.label);
  final String wire;
  final String label;

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
  static const Map<ProjectStage, StageGuidanceTemplate> templates = {
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

  static StageGuidanceTemplate getTemplate(ProjectStage stage) {
    return templates[stage] ?? templates[ProjectStage.p0Discovery]!;
  }
}
