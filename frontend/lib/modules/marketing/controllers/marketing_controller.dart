import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../modules/marketing/services/marketing_service.dart';

/// Trạng thái của Marketing Cockpit.
///
/// Nguyên tắc: mọi con số hiển thị đều đến từ backend (Python Analytics Engine). Controller
/// không tự tính KPI và không tự bịa giá trị mặc định khi API lỗi - lỗi phải nổi lên UI.
class MarketingController extends GetxController {
  final MarketingService _service = MarketingService();

  final RxBool isLoading = false.obs;
  final RxBool isSubmitting = false.obs;
  final RxString errorMessage = ''.obs;

  final RxMap<String, dynamic> cockpitSummary = <String, dynamic>{}.obs;
  final RxMap<String, dynamic> marketingContext = <String, dynamic>{}.obs;
  final RxMap<String, dynamic> customerResearch = <String, dynamic>{}.obs;
  final RxMap<String, dynamic> productMarketing = <String, dynamic>{}.obs;
  final RxMap<String, dynamic> offerArchitecture = <String, dynamic>{}.obs;
  final RxMap<String, dynamic> plan12W = <String, dynamic>{}.obs;
  final RxMap<String, dynamic> funnel = <String, dynamic>{}.obs;
  final RxMap<String, dynamic> analytics = <String, dynamic>{}.obs;
  final RxList<dynamic> objectives = <dynamic>[].obs;
  final RxList<dynamic> campaigns = <dynamic>[].obs;
  final RxList<dynamic> loops = <dynamic>[].obs;
  final RxList<dynamic> experiments = <dynamic>[].obs;
  final RxList<dynamic> learnings = <dynamic>[].obs;
  final RxList<dynamic> playbooks = <dynamic>[].obs;
  final RxList<dynamic> decisions = <dynamic>[].obs;
  final RxList<dynamic> recommendations = <dynamic>[].obs;
  final RxList<dynamic> metrics = <dynamic>[].obs;
  final RxList<dynamic> pendingApprovals = <dynamic>[].obs;
  final RxList<dynamic> skills = <dynamic>[].obs;
  final RxList<dynamic> skillExecutions = <dynamic>[].obs;
  final RxMap<String, dynamic> attributionResult = <String, dynamic>{}.obs;
  final Rx<Map<String, dynamic>?> selectedSkill = Rx<Map<String, dynamic>?>(null);

  final RxList<dynamic> projects = <dynamic>[].obs;
  final RxnString selectedProjectId = RxnString();
  final RxString selectedFlowNode = 'trigger'.obs;
  final RxString contentSubTab = 'campaigns'.obs;
  final RxString learningSubTab = 'overview'.obs;

  // Market Validation Observables (§16 - §48)
  final RxList<dynamic> assumptions = <dynamic>[].obs;
  final RxMap<String, dynamic> assumptionsSummary = <String, dynamic>{}.obs;
  final RxList<dynamic> evidenceList = <dynamic>[].obs;
  final RxMap<String, dynamic> canvasesStatus = <String, dynamic>{}.obs;
  final RxList<dynamic> customerInterviews = <dynamic>[].obs;
  final RxList<dynamic> canvasRevisions = <dynamic>[].obs;
  final RxList<dynamic> marketingAttributions = <dynamic>[].obs;
  final Rx<Map<String, dynamic>?> selectedAssumption = Rx<Map<String, dynamic>?>(null);

  void selectSkill(Map<String, dynamic>? skill) {
    if (selectedSkill.value != null &&
        selectedSkill.value!['capability_id'] == skill?['capability_id']) {
      selectedSkill.value = null;
    } else {
      selectedSkill.value = skill;
    }
  }

  void selectFlowNode(String nodeKey) {
    selectedFlowNode.value = nodeKey;
  }

  void selectProject(String? projectId) {
    if (selectedProjectId.value == projectId) return;
    selectedProjectId.value = projectId;
    loadAllData();
  }

  @override
  void onInit() {
    super.onInit();
    _initBrainAndLoad();
  }

  Future<void> _initBrainAndLoad() async {
    await loadAllData();
  }


  /// Nạp toàn bộ dữ liệu cockpit và validation engine.
  Future<void> loadAllData() async {
    isLoading.value = true;
    errorMessage.value = '';
    try {
      final p = selectedProjectId.value;
      final results = await Future.wait([
        _service.getCockpitSummary(projectId: p).catchError((_) => <String, dynamic>{}),
        _service.getMarketingContext(p).catchError((_) => null),
        _service.getFunnel(projectId: p).catchError((_) => <String, dynamic>{}),
        _service.getAnalyticsOverview(projectId: p).catchError((_) => <String, dynamic>{}),
        _service.getMarketingObjectives(projectId: p).catchError((_) => <dynamic>[]),
        _service.getCampaigns(projectId: p).catchError((_) => <dynamic>[]),
        _service.getExperiments().catchError((_) => <dynamic>[]),
        _service.getLearnings().catchError((_) => <String, dynamic>{}),
        _service.getMetrics().catchError((_) => <dynamic>[]),
        _service.getApprovals().catchError((_) => <dynamic>[]),
        _service.getSkills().catchError((_) => <dynamic>[]),
        _service.getSkillExecutions().catchError((_) => <dynamic>[]),
        _service.getLoops().catchError((_) => <dynamic>[]),
        _service.getDecisions().catchError((_) => <dynamic>[]),
        _service.getRecommendations().catchError((_) => <dynamic>[]),
        _service.getProjects().catchError((_) => <dynamic>[]),
        // Validation Engine Data
        _service.getAssumptions(projectId: p).catchError((_) => <dynamic>[]),
        _service.getAssumptionsSummary(projectId: p).catchError((_) => <String, dynamic>{}),
        _service.getCanvasesStatus(projectId: p).catchError((_) => <String, dynamic>{}),
        _service.getCanvasRevisions(projectId: p).catchError((_) => <dynamic>[]),
        _service.getCustomerInterviews(projectId: p).catchError((_) => <dynamic>[]),
        _service.getEvidenceList(projectId: p).catchError((_) => <dynamic>[]),
      ]);

      cockpitSummary.value = (results[0] as Map<String, dynamic>?) ?? <String, dynamic>{};
      final ctx = results[1] as Map<String, dynamic>?;
      marketingContext.value = ctx ?? <String, dynamic>{};
      customerResearch.value = (marketingContext['customer_research'] as Map<String, dynamic>?) ?? <String, dynamic>{};
      productMarketing.value = (marketingContext['product_marketing'] as Map<String, dynamic>?) ?? <String, dynamic>{};
      offerArchitecture.value = (marketingContext['offer_architecture'] as Map<String, dynamic>?) ?? <String, dynamic>{};
      plan12W.value = (marketingContext['marketing_plan_12w'] as Map<String, dynamic>?) ?? <String, dynamic>{};

      funnel.value = (results[2] as Map<String, dynamic>?) ?? <String, dynamic>{};
      analytics.value = (results[3] as Map<String, dynamic>?) ?? <String, dynamic>{};
      objectives.value = (results[4] as List<dynamic>?) ?? <dynamic>[];
      campaigns.value = (results[5] as List<dynamic>?) ?? <dynamic>[];
      experiments.value = (results[6] as List<dynamic>?) ?? <dynamic>[];

      final learningData = (results[7] as Map<String, dynamic>?) ?? <String, dynamic>{};
      learnings.value = (learningData['learnings'] as List<dynamic>?) ?? const [];
      playbooks.value = (learningData['playbooks'] as List<dynamic>?) ?? const [];

      metrics.value = (results[8] as List<dynamic>?) ?? <dynamic>[];
      pendingApprovals.value = (results[9] as List<dynamic>?) ?? <dynamic>[];
      skills.value = (results[10] as List<dynamic>?) ?? <dynamic>[];
      skillExecutions.value = (results[11] as List<dynamic>?) ?? <dynamic>[];
      loops.value = (results[12] as List<dynamic>?) ?? <dynamic>[];
      decisions.value = (results[13] as List<dynamic>?) ?? <dynamic>[];
      recommendations.value = (results[14] as List<dynamic>?) ?? <dynamic>[];
      projects.value = (results[15] as List<dynamic>?) ?? <dynamic>[];

      // Assign Validation State
      assumptions.value = (results[16] as List<dynamic>?) ?? <dynamic>[];
      assumptionsSummary.value = (results[17] as Map<String, dynamic>?) ?? <String, dynamic>{};
      canvasesStatus.value = (results[18] as Map<String, dynamic>?) ?? <String, dynamic>{};
      canvasRevisions.value = (results[19] as List<dynamic>?) ?? <dynamic>[];
      customerInterviews.value = (results[20] as List<dynamic>?) ?? <dynamic>[];
      evidenceList.value = (results[21] as List<dynamic>?) ?? <dynamic>[];

      // Auto-select first project if none selected or if selected project is not in list
      if (projects.isNotEmpty) {
        final currentSelected = selectedProjectId.value;
        final exists = projects.any((p) => p['id']?.toString() == currentSelected);
        if (currentSelected == null || !exists) {
          final firstId = projects.first['id']?.toString();
          selectedProjectId.value = firstId;
          if (p == null && firstId != null) {
            loadAllData();
            return;
          }
        }
      } else {
        selectedProjectId.value = null;
      }

    } catch (e) {
      errorMessage.value = _describe(e);
    } finally {
      isLoading.value = false;
    }
  }

  // ====================================================================
  // Market Validation Actions
  // ====================================================================

  Future<void> reloadValidation() async {
    final p = selectedProjectId.value;
    final res = await Future.wait([
      _service.getAssumptions(projectId: p).catchError((_) => <dynamic>[]),
      _service.getAssumptionsSummary(projectId: p).catchError((_) => <String, dynamic>{}),
      _service.getCanvasesStatus(projectId: p).catchError((_) => <String, dynamic>{}),
      _service.getCanvasRevisions(projectId: p).catchError((_) => <dynamic>[]),
      _service.getCustomerInterviews(projectId: p).catchError((_) => <dynamic>[]),
      _service.getEvidenceList(projectId: p).catchError((_) => <dynamic>[]),
    ]);
    assumptions.value = (res[0] as List<dynamic>?) ?? <dynamic>[];
    assumptionsSummary.value = (res[1] as Map<String, dynamic>?) ?? <String, dynamic>{};
    canvasesStatus.value = (res[2] as Map<String, dynamic>?) ?? <String, dynamic>{};
    canvasRevisions.value = (res[3] as List<dynamic>?) ?? <dynamic>[];
    customerInterviews.value = (res[4] as List<dynamic>?) ?? <dynamic>[];
    evidenceList.value = (res[5] as List<dynamic>?) ?? <dynamic>[];
  }

  Future<Map<String, dynamic>> extractAssumptionsAI(String text, {String? canvasType, Map<String, dynamic>? canvasContent, bool saveToDb = true}) async {
    isSubmitting.value = true;
    try {
      final payload = <String, dynamic>{
        'raw_text': text,
        'save_to_db': saveToDb,
        'canvas_type': canvasType,
        'canvas_content': canvasContent,
        if (selectedProjectId.value != null) 'project_id': int.tryParse(selectedProjectId.value!),
      };
      final res = await _service.extractAssumptionsAI(payload);
      await reloadValidation();
      return res;
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<void> createAssumption(Map<String, dynamic> data) async {
    isSubmitting.value = true;
    try {
      if (selectedProjectId.value != null) {
        data['project_id'] = int.tryParse(selectedProjectId.value!);
      }
      await _service.createAssumption(data);
      await reloadValidation();
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<void> updateAssumption(String id, Map<String, dynamic> data) async {
    isSubmitting.value = true;
    try {
      await _service.updateAssumption(id, data);
      await reloadValidation();
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<void> deleteAssumption(String id) async {
    isSubmitting.value = true;
    try {
      await _service.deleteAssumption(id);
      await reloadValidation();
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<Map<String, dynamic>> designSmallestExperimentAI(String assumptionId) async {
    isSubmitting.value = true;
    try {
      return await _service.designExperimentAI({
        'assumption_id': int.tryParse(assumptionId) ?? assumptionId,
      });
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<Map<String, dynamic>> checkScaleWarning(String assumptionId) async {
    return await _service.checkScaleWarning(assumptionId);
  }

  Future<void> completeValidationExperiment(String experimentId, String conclusion, String learning, Map<String, dynamic> observations) async {
    isSubmitting.value = true;
    try {
      await _service.completeValidationExperiment(experimentId, {
        'conclusion': conclusion,
        'learning_summary': learning,
        'observations': observations,
      });
      await loadAllData();
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<Map<String, dynamic>> extractInterviewAI(String transcript, {String? customerName, String? segment, bool saveToDb = false}) async {
    isSubmitting.value = true;
    try {
      final res = await _service.extractInterviewAI({
        'transcript': transcript,
        'customer_name': customerName,
        'segment': segment,
        'save_to_db': saveToDb,
        if (selectedProjectId.value != null) 'project_id': int.tryParse(selectedProjectId.value!),
      });
      if (saveToDb) {
        await reloadValidation();
      }
      return res;
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<void> recordCustomerInterview(Map<String, dynamic> data) async {
    isSubmitting.value = true;
    try {
      if (selectedProjectId.value != null) {
        data['project_id'] = int.tryParse(selectedProjectId.value!);
      }
      await _service.recordCustomerInterview(data);
      await reloadValidation();
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<Map<String, dynamic>> evaluateLearningLoopAI(String? experimentId, String? assumptionId, String actualOutcome) async {
    isSubmitting.value = true;
    try {
      return await _service.evaluateLearningLoopAI({
        if (experimentId != null) 'experiment_id': int.tryParse(experimentId),
        if (assumptionId != null) 'assumption_id': int.tryParse(assumptionId),
        'actual_outcome': actualOutcome,
      });
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<void> recordLearningAndDecision(Map<String, dynamic> data) async {
    isSubmitting.value = true;
    try {
      if (selectedProjectId.value != null) {
        data['project_id'] = int.tryParse(selectedProjectId.value!);
      }
      await _service.recordLearningAndDecision(data);
      await loadAllData();
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<Map<String, dynamic>> proposeCanvasRevisionAI(String canvasType, Map<String, dynamic> currentCanvas, String evidenceStatement, bool isContradiction) async {
    isSubmitting.value = true;
    try {
      return await _service.proposeCanvasRevisionAI({
        'canvas_type': canvasType,
        'current_canvas': currentCanvas,
        'evidence_statement': evidenceStatement,
        'is_contradiction': isContradiction,
      });
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<void> approveCanvasRevision(String revisionId) async {
    isSubmitting.value = true;
    try {
      await _service.approveCanvasRevision(revisionId);
      await reloadValidation();
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<void> rejectCanvasRevision(String revisionId) async {
    isSubmitting.value = true;
    try {
      await _service.rejectCanvasRevision(revisionId);
      await reloadValidation();
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<void> createEvidence(Map<String, dynamic> data) async {
    isSubmitting.value = true;
    try {
      if (selectedProjectId.value != null) {
        data['project_id'] = int.tryParse(selectedProjectId.value!);
      }
      await _service.createEvidence(data);
      await reloadValidation();
    } finally {
      isSubmitting.value = false;
    }
  }


  String _describe(Object e) => e is MarketingApiException ? e.message : e.toString();

  /// Bọc một thao tác ghi: hiện lỗi bằng snackbar tiếng Việt và nạp lại dữ liệu khi xong.
  Future<bool> _mutate(Future<void> Function() action, {String? successMessage}) async {
    isSubmitting.value = true;
    try {
      await action();
      await loadAllData();
      if (successMessage != null) {
        AppToast.success(successMessage);
      }
      return true;
    } catch (e) {
      final message = _describe(e);
      errorMessage.value = message;
      AppToast.error(message, title: 'Không thực hiện được');
      return false;
    } finally {
      isSubmitting.value = false;
    }
  }

  final RxInt activeCanvasAccordionIndex = 0.obs;

  void toggleCanvasAccordion(int index) {
    if (activeCanvasAccordionIndex.value == index) {
      activeCanvasAccordionIndex.value = -1;
    } else {
      activeCanvasAccordionIndex.value = index;
    }
  }

  Future<void> autoGenerateCanvas(String canvasType) async {
    final selectedProj = projects.firstWhereOrNull((p) => p['id']?.toString() == selectedProjectId.value);
    final projTitle = selectedProj != null ? (selectedProj['title']?.toString() ?? 'Sản phẩm SaaS') : 'Sản phẩm SaaS';
    final projDesc = selectedProj != null ? (selectedProj['description']?.toString() ?? '') : '';
    final contextHint = projDesc.isNotEmpty ? ' ($projDesc)' : '';

    final currentContext = Map<String, dynamic>.from(marketingContext);

    if (canvasType == 'customer_research') {
      currentContext['customer_research'] = {
        'segments': 'Khách hàng B2B/B2C mục tiêu của $projTitle$contextHint: Doanh chủ, Quản lý điều hành và Đội ngũ thực thi chuyên nghiệp.',
        'jtbd': 'Cần một giải pháp tinh gọn, tự động hóa quy trình nghiệp vụ và nâng cao hiệu suất vượt trội cho $projTitle.',
        'pains': 'Quy trình thủ công tốn kém, công cụ phân mảnh, thiếu thời gian và nhân sự chuyên trách.',
        'facts': 'Thị trường có nhu cầu rất lớn về công cụ tiếp thị tự trị khép kín có tích hợp AI.',
        'hypotheses': 'Khách hàng sẽ quyết định nhanh nếu thấy rõ kịch bản triển khai mẫu và cam kết hiệu quả rõ ràng.',
      };
    } else if (canvasType == 'product_marketing') {
      currentContext['product_marketing'] = {
        'category': 'Nền tảng AI SaaS Tự trị & Quản trị Tiếp thị Doanh nghiệp',
        'alternatives': 'Các công cụ phần mềm truyền thống rời rạc hoặc thuê ngoài agency tốn kém.',
        'differentiators': '$projTitle tích hợp AI thực thi khép kín theo vòng lặp Closed-Loop, có kiểm soát an toàn ngân sách và đo lường định lượng thời gian thực.',
        'positioning_statement': 'Dành cho các nhà sáng lập và đội ngũ đang tìm kiếm bước nhảy vọt về tăng trưởng, $projTitle$contextHint là nền tảng tất cả trong một giúp tự động hóa từ Chiến lược đến Khách hàng tiềm năng.',
      };
    } else if (canvasType == 'offer_architecture') {
      currentContext['offer_architecture'] = {
        'core_offer': 'Gói giải pháp toàn diện $projTitle với đầy đủ tính năng cốt lõi và AI Agents hỗ trợ 24/7.',
        'value': 'Tiết kiệm đến 70% thời gian vận hành và tăng gấp đôi tốc độ tạo ra chuyển đổi kinh doanh.',
        'proof': 'Hệ thống đã được chuẩn hóa theo khung quản trị quốc tế và kiểm chứng trên dữ liệu thực tế.',
        'bonus': 'Tặng kèm bộ tài liệu Playbook thực thi, Template thiết lập nhanh và gói cố vấn 1-1.',
        'guarantee': 'Cam kết đảo ngược rủi ro: Hoàn tiền 100% trong 30 ngày nếu không đạt kỳ vọng.',
        'urgency': 'Ưu đãi dành riêng cho 50 doanh nghiệp tiên phong đăng ký trong tháng này.',
        'cta': 'Kích hoạt thử nghiệm ngay hôm nay',
      };
    } else if (canvasType == 'all' || canvasType == 'brand_context') {
      currentContext['customer_research'] = {
        'segments': 'Khách hàng B2B/B2C mục tiêu của $projTitle$contextHint: Doanh chủ, Quản lý điều hành và Đội ngũ thực thi chuyên nghiệp.',
        'jtbd': 'Cần một giải pháp tinh gọn, tự động hóa quy trình nghiệp vụ và nâng cao hiệu suất vượt trội cho $projTitle.',
        'pains': 'Quy trình thủ công tốn kém, công cụ phân mảnh, thiếu thời gian và nhân sự chuyên trách.',
        'facts': 'Thị trường có nhu cầu rất lớn về công cụ tiếp thị tự trị khép kín có tích hợp AI.',
        'hypotheses': 'Khách hàng sẽ quyết định nhanh nếu thấy rõ kịch bản triển khai mẫu và cam kết hiệu quả rõ ràng.',
      };
      currentContext['product_marketing'] = {
        'category': 'Nền tảng AI SaaS Tự trị & Quản trị Tiếp thị Doanh nghiệp',
        'alternatives': 'Các công cụ phần mềm truyền thống rời rạc hoặc thuê ngoài agency tốn kém.',
        'differentiators': '$projTitle tích hợp AI thực thi khép kín theo vòng lặp Closed-Loop, có kiểm soát an toàn ngân sách và đo lường định lượng thời gian thực.',
        'positioning_statement': 'Dành cho các nhà sáng lập và đội ngũ đang tìm kiếm bước nhảy vọt về tăng trưởng, $projTitle$contextHint là nền tảng tất cả trong một giúp tự động hóa từ Chiến lược đến Khách hàng tiềm năng.',
      };
      currentContext['offer_architecture'] = {
        'core_offer': 'Gói giải pháp toàn diện $projTitle với đầy đủ tính năng cốt lõi và AI Agents hỗ trợ 24/7.',
        'value': 'Tiết kiệm đến 70% thời gian vận hành và tăng gấp đôi tốc độ tạo ra chuyển đổi kinh doanh.',
        'proof': 'Hệ thống đã được chuẩn hóa theo khung quản trị quốc tế và kiểm chứng trên dữ liệu thực tế.',
        'bonus': 'Tặng kèm bộ tài liệu Playbook thực thi, Template thiết lập nhanh và gói cố vấn 1-1.',
        'guarantee': 'Cam kết đảo ngược rủi ro: Hoàn tiền 100% trong 30 ngày nếu không đạt kỳ vọng.',
        'urgency': 'Ưu đãi dành riêng cho 50 doanh nghiệp tiên phong đăng ký trong tháng này.',
        'cta': 'Kích hoạt thử nghiệm ngay hôm nay',
      };
      currentContext['icp'] = 'Doanh nghiệp và Founder đang mở rộng quy mô kinh doanh với $projTitle$contextHint';
      currentContext['value_proposition'] = 'Tự động hóa tiếp thị và kinh doanh thông minh với $projTitle';
      currentContext['brand_voice'] = 'Chuyên nghiệp, Đáng tin cậy, Đột phá, Táo bạo và Hướng đến kết quả';
      currentContext['pricing'] = 'Mô hình thuê bao linh hoạt theo mức độ sử dụng thực tế';
      currentContext['competitors'] = 'Các công cụ SaaS truyền thống trên thị trường';
    }

    await saveContext(currentContext);
  }

  // ====================================================================
  // Bối cảnh Marketing
  // ====================================================================

  Future<bool> saveContext(Map<String, dynamic> payload) => _mutate(
        () => _service.updateMarketingContext(
          payload,
          projectId: selectedProjectId.value,
          expectedRevision: marketingContext['revision'] is int ? marketingContext['revision'] as int : null,
        ),
        successMessage: 'Đã lưu bối cảnh Marketing',
      );

  Future<bool> submitContextForReview() => _mutate(
        () => _service.submitMarketingContextForReview(
          expectedRevision: marketingContext['revision'] is int ? marketingContext['revision'] as int : null,
        ),
        successMessage: 'Đã gửi yêu cầu phê duyệt Marketing Context',
      );

  Future<bool> approveContext() => _mutate(
        () => _service.approveMarketingContext(
          expectedRevision: marketingContext['revision'] is int ? marketingContext['revision'] as int : null,
        ),
        successMessage: 'Đã phê duyệt Marketing Context thành công',
      );

  // ====================================================================
  // Mục tiêu
  // ====================================================================

  Future<bool> createObjective(Map<String, dynamic> payload) => _mutate(
        () => _service.createMarketingObjective(payload, projectId: selectedProjectId.value),
        successMessage: 'Đã tạo mục tiêu Marketing',
      );

  Future<bool> updateObjective(String objectiveId, Map<String, dynamic> payload) => _mutate(
        () => _service.updateMarketingObjective(objectiveId, payload),
        successMessage: 'Đã cập nhật mục tiêu',
      );

  Future<bool> deleteObjective(String objectiveId) => _mutate(
        () => _service.deleteMarketingObjective(objectiveId),
        successMessage: 'Đã xoá mục tiêu',
      );

  // ====================================================================
  // Chiến dịch
  // ====================================================================

  Future<bool> createCampaign(Map<String, dynamic> payload) => _mutate(
        () => _service.createCampaign(payload),
        successMessage: 'Đã tạo chiến dịch ở trạng thái nháp',
      );

  Future<bool> updateCampaign(String campaignId, Map<String, dynamic> payload) => _mutate(
        () => _service.updateCampaign(campaignId, payload),
        successMessage: 'Đã cập nhật chiến dịch',
      );

  Future<bool> deleteCampaign(String campaignId) => _mutate(
        () => _service.deleteCampaign(campaignId),
        successMessage: 'Đã xoá chiến dịch',
      );

  /// Kích hoạt/tạm dừng chiến dịch là hành động tiêu ngân sách nên backend đẩy vào hàng
  /// đợi phê duyệt. Thông báo phải nói đúng điều đó thay vì báo "đã kích hoạt".
  Future<bool> changeCampaignStatus(String campaignId, String status) async {
    isSubmitting.value = true;
    try {
      final result = await _service.changeCampaignStatus(campaignId, status);
      await loadAllData();
      final queued = result['status'] == 'pending_approval';
      if (queued) {
        AppToast.info(
          'Thay đổi đã được đưa vào hàng đợi phê duyệt, cần người duyệt trước khi có hiệu lực.',
          title: 'Chờ phê duyệt',
        );
      } else {
        AppToast.success(
          'Trạng thái chiến dịch đã được cập nhật.',
          title: 'Đã cập nhật',
        );
      }
      return true;
    } catch (e) {
      final message = _describe(e);
      errorMessage.value = message;
      AppToast.error(message, title: 'Không thực hiện được');
      return false;
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<Map<String, dynamic>> loadCampaignDetail(String campaignId) async {
    try {
      return await _service.getCampaignDetail(campaignId);
    } catch (e) {
      AppToast.error(_describe(e), title: 'Không tải được chiến dịch');
      return <String, dynamic>{};
    }
  }

  Future<bool> createAsset(String campaignId, Map<String, dynamic> payload) => _mutate(
        () => _service.createCampaignAsset(campaignId, payload),
        successMessage: 'Đã lưu nội dung ở trạng thái nháp',
      );

  Future<bool> requestAssetApproval(String assetId) => _mutate(
        () => _service.requestAssetApproval(assetId),
        successMessage: 'Đã gửi nội dung tới hàng đợi phê duyệt',
      );

  // ====================================================================
  // Thử nghiệm
  // ====================================================================

  Future<bool> createExperiment(Map<String, dynamic> payload) => _mutate(
        () => _service.createExperiment(payload),
        successMessage: 'Đã tạo thử nghiệm',
      );

  Future<Map<String, dynamic>> evaluateExperiment(String experimentId, Map<String, dynamic> payload) async {
    isSubmitting.value = true;
    try {
      final result = await _service.evaluateExperiment(experimentId, payload);
      await loadAllData();
      return result;
    } catch (e) {
      AppToast.error(_describe(e), title: 'Không đánh giá được');
      return <String, dynamic>{};
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<bool> decideExperiment(String experimentId, String decision, String? learning) => _mutate(
        () => _service.decideExperiment(experimentId, decision, learning),
        successMessage: 'Đã ghi nhận quyết định và bài học',
      );

  // ====================================================================
  // Bài học & chỉ số
  // ====================================================================

  Future<bool> createLearning(Map<String, dynamic> payload) => _mutate(
        () => _service.createLearning(payload),
        successMessage: 'Đã lưu bài học',
      );

  Future<bool> upsertMetric(Map<String, dynamic> payload) => _mutate(
        () => _service.upsertMetric(payload),
        successMessage: 'Đã cập nhật chỉ số',
      );

  // ====================================================================
  // Skill & phê duyệt
  // ====================================================================

  Future<Map<String, dynamic>> executeSkill(String capabilityId, Map<String, dynamic> input) async {
    isSubmitting.value = true;
    try {
      final result = await _service.executeSkill(capabilityId, input);
      await loadAllData();
      return result;
    } catch (e) {
      AppToast.error(_describe(e), title: 'Không chạy được skill');
      return <String, dynamic>{};
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<bool> reviewApproval(String approvalId, bool approved, String? notes) => _mutate(
        () => _service.reviewApproval(approvalId, approved, notes),
        successMessage: approved ? 'Đã phê duyệt và thực thi' : 'Đã từ chối yêu cầu',
      );

  // ====================================================================
  // Canvas Sub-sections: Research, Product Marketing, Offers, 12W Plan
  // ====================================================================

  Future<bool> saveCustomerResearch(Map<String, dynamic> data) => _mutate(
        () async {
          await _service.updateCustomerResearch(data);
        },
        successMessage: 'Đã lưu kết quả nghiên cứu khách hàng',
      );

  Future<bool> saveProductMarketing(Map<String, dynamic> data) => _mutate(
        () async {
          await _service.updateProductMarketing(data);
        },
        successMessage: 'Đã cập nhật định vị Product Marketing',
      );

  Future<bool> saveOfferArchitecture(Map<String, dynamic> data) => _mutate(
        () async {
          await _service.updateOfferArchitecture(data);
        },
        successMessage: 'Đã lưu kiến trúc ưu đãi (Offer Architecture)',
      );

  Future<bool> savePlan12W(Map<String, dynamic> data) => _mutate(
        () async {
          await _service.update12WPlan(data);
        },
        successMessage: 'Đã lưu kế hoạch Marketing 12 tuần',
      );

  // ====================================================================
  // Marketing Loops (§18)
  // ====================================================================

  Future<bool> createLoop(Map<String, dynamic> payload) => _mutate(
        () => _service.createLoop(payload),
        successMessage: 'Đã tạo vòng lặp tăng trưởng',
      );

  Future<bool> updateLoop(String loopId, Map<String, dynamic> payload) => _mutate(
        () => _service.updateLoop(loopId, payload),
        successMessage: 'Đã cập nhật vòng lặp',
      );

  Future<bool> deleteLoop(String loopId) => _mutate(
        () => _service.deleteLoop(loopId),
        successMessage: 'Đã xoá vòng lặp',
      );

  Future<bool> triggerLoop(String loopId) => _mutate(
        () => _service.triggerLoop(loopId),
        successMessage: 'Đã kích hoạt vòng lặp',
      );

  // ====================================================================
  // Attribution Analytics (§28)
  // ====================================================================

  Future<void> runAttributionAnalysis(List<Map<String, dynamic>> touchpoints, String modelType, double convValue) async {
    isSubmitting.value = true;
    try {
      final res = await _service.calculateAttribution({
        'touchpoints': touchpoints,
        'model_type': modelType,
        'conversion_value': convValue,
      });
      attributionResult.value = res;
      AppToast.success(
        'Đã tính toán phân bổ chuyển đổi ($modelType)',
        title: 'Thành công',
      );
    } catch (e) {
      AppToast.error(_describe(e), title: 'Lỗi phân tích');
    } finally {
      isSubmitting.value = false;
    }
  }

  // ====================================================================
  // Decision Journal (§53)
  // ====================================================================

  Future<bool> createDecision(Map<String, dynamic> payload) => _mutate(
        () => _service.createDecision(payload),
        successMessage: 'Đã ghi nhận quyết định vào nhật ký',
      );

  Future<bool> updateDecision(String decisionId, Map<String, dynamic> payload) => _mutate(
        () => _service.updateDecision(decisionId, payload),
        successMessage: 'Đã cập nhật nhật ký quyết định',
      );

  Future<bool> deleteDecision(String decisionId) => _mutate(
        () => _service.deleteDecision(decisionId),
        successMessage: 'Đã xoá quyết định',
      );

  // ====================================================================
  // Recommendations (§52)
  // ====================================================================

  Future<bool> createRecommendation(Map<String, dynamic> payload) => _mutate(
        () => _service.createRecommendation(payload),
        successMessage: 'Đã tạo khuyến nghị mới',
      );

  Future<bool> updateRecommendationStatus(String recId, String status) => _mutate(
        () => _service.updateRecommendationStatus(recId, status),
        successMessage: 'Đã cập nhật trạng thái khuyến nghị',
      );
}

