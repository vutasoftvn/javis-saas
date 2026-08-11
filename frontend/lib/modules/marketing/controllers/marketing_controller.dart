import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../data/services/marketing_service.dart';

/// Trạng thái của Marketing Cockpit.
///
/// Nguyên tắc: mọi con số hiển thị đều đến từ backend (Python Analytics Engine). Controller
/// không tự tính KPI và không tự bịa giá trị mặc định khi API lỗi - lỗi phải nổi lên UI.
class MarketingController extends GetxController {
  final MarketingService _service = MarketingService();

  final RxString brainId = ''.obs;
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

  @override
  void onInit() {
    super.onInit();
    _initBrainAndLoad();
  }

  Future<void> _initBrainAndLoad() async {
    final prefs = await SharedPreferences.getInstance();
    brainId.value = prefs.getString('brain_id') ?? '';
    await loadAllData();
  }

  void setBrainId(String newBrainId) {
    brainId.value = newBrainId;
    loadAllData();
  }

  /// Nạp toàn bộ dữ liệu cockpit. Brain rỗng là hợp lệ: backend sẽ tự chọn brain mặc định
  /// của workspace đã xác thực (không tin brain_id do client tự khai).
  Future<void> loadAllData() async {
    isLoading.value = true;
    errorMessage.value = '';
    try {
      final b = brainId.value;
      final results = await Future.wait([
        _service.getCockpitSummary(b),
        _service.getMarketingContext(b),
        _service.getFunnel(b),
        _service.getAnalyticsOverview(b),
        _service.getMarketingObjectives(b),
        _service.getCampaigns(b),
        _service.getExperiments(b),
        _service.getLearnings(b),
        _service.getMetrics(b),
        _service.getApprovals(b),
        _service.getSkills(),
        _service.getSkillExecutions(b),
        _service.getLoops(b),
        _service.getDecisions(b),
        _service.getRecommendations(b),
      ]);

      cockpitSummary.value = results[0] as Map<String, dynamic>;
      final ctx = results[1] as Map<String, dynamic>?;
      marketingContext.value = ctx ?? <String, dynamic>{};
      customerResearch.value = (marketingContext['customer_research'] as Map<String, dynamic>?) ?? <String, dynamic>{};
      productMarketing.value = (marketingContext['product_marketing'] as Map<String, dynamic>?) ?? <String, dynamic>{};
      offerArchitecture.value = (marketingContext['offer_architecture'] as Map<String, dynamic>?) ?? <String, dynamic>{};
      plan12W.value = (marketingContext['marketing_plan_12w'] as Map<String, dynamic>?) ?? <String, dynamic>{};

      funnel.value = results[2] as Map<String, dynamic>;
      analytics.value = results[3] as Map<String, dynamic>;
      objectives.value = results[4] as List<dynamic>;
      campaigns.value = results[5] as List<dynamic>;
      experiments.value = results[6] as List<dynamic>;

      final learningData = results[7] as Map<String, dynamic>;
      learnings.value = (learningData['learnings'] as List<dynamic>?) ?? const [];
      playbooks.value = (learningData['playbooks'] as List<dynamic>?) ?? const [];

      metrics.value = results[8] as List<dynamic>;
      pendingApprovals.value = results[9] as List<dynamic>;
      skills.value = results[10] as List<dynamic>;
      skillExecutions.value = results[11] as List<dynamic>;
      loops.value = results[12] as List<dynamic>;
      decisions.value = results[13] as List<dynamic>;
      recommendations.value = results[14] as List<dynamic>;

      final resolvedBrain = cockpitSummary['brain_id'];
      if (resolvedBrain is String && resolvedBrain.isNotEmpty) {
        brainId.value = resolvedBrain;
      }
    } catch (e) {
      errorMessage.value = _describe(e);
    } finally {
      isLoading.value = false;
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
        Get.snackbar('Thành công', successMessage, snackPosition: SnackPosition.BOTTOM);
      }
      return true;
    } catch (e) {
      final message = _describe(e);
      errorMessage.value = message;
      Get.snackbar('Không thực hiện được', message, snackPosition: SnackPosition.BOTTOM);
      return false;
    } finally {
      isSubmitting.value = false;
    }
  }

  // ====================================================================
  // Bối cảnh Marketing
  // ====================================================================

  Future<bool> saveContext(Map<String, dynamic> payload) => _mutate(
        () => _service.updateMarketingContext(brainId.value, payload),
        successMessage: 'Đã lưu bối cảnh Marketing',
      );

  // ====================================================================
  // Mục tiêu
  // ====================================================================

  Future<bool> createObjective(Map<String, dynamic> payload) => _mutate(
        () => _service.createMarketingObjective(brainId.value, payload),
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
        () => _service.createCampaign(brainId.value, payload),
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
      Get.snackbar(
        queued ? 'Chờ phê duyệt' : 'Đã cập nhật',
        queued
            ? 'Thay đổi đã được đưa vào hàng đợi phê duyệt, cần người duyệt trước khi có hiệu lực.'
            : 'Trạng thái chiến dịch đã được cập nhật.',
        snackPosition: SnackPosition.BOTTOM,
      );
      return true;
    } catch (e) {
      final message = _describe(e);
      errorMessage.value = message;
      Get.snackbar('Không thực hiện được', message, snackPosition: SnackPosition.BOTTOM);
      return false;
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<Map<String, dynamic>> loadCampaignDetail(String campaignId) async {
    try {
      return await _service.getCampaignDetail(campaignId);
    } catch (e) {
      Get.snackbar('Không tải được chiến dịch', _describe(e), snackPosition: SnackPosition.BOTTOM);
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
        () => _service.createExperiment(brainId.value, payload),
        successMessage: 'Đã tạo thử nghiệm',
      );

  Future<Map<String, dynamic>> evaluateExperiment(String experimentId, Map<String, dynamic> payload) async {
    isSubmitting.value = true;
    try {
      final result = await _service.evaluateExperiment(experimentId, payload);
      await loadAllData();
      return result;
    } catch (e) {
      Get.snackbar('Không đánh giá được', _describe(e), snackPosition: SnackPosition.BOTTOM);
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
        () => _service.createLearning(brainId.value, payload),
        successMessage: 'Đã lưu bài học',
      );

  Future<bool> upsertMetric(Map<String, dynamic> payload) => _mutate(
        () => _service.upsertMetric(brainId.value, payload),
        successMessage: 'Đã cập nhật chỉ số',
      );

  // ====================================================================
  // Skill & phê duyệt
  // ====================================================================

  Future<Map<String, dynamic>> executeSkill(String capabilityId, Map<String, dynamic> input) async {
    isSubmitting.value = true;
    try {
      final result = await _service.executeSkill(brainId.value, capabilityId, input);
      await loadAllData();
      return result;
    } catch (e) {
      Get.snackbar('Không chạy được skill', _describe(e), snackPosition: SnackPosition.BOTTOM);
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
          await _service.updateCustomerResearch(brainId.value, data);
        },
        successMessage: 'Đã lưu kết quả nghiên cứu khách hàng',
      );

  Future<bool> saveProductMarketing(Map<String, dynamic> data) => _mutate(
        () async {
          await _service.updateProductMarketing(brainId.value, data);
        },
        successMessage: 'Đã cập nhật định vị Product Marketing',
      );

  Future<bool> saveOfferArchitecture(Map<String, dynamic> data) => _mutate(
        () async {
          await _service.updateOfferArchitecture(brainId.value, data);
        },
        successMessage: 'Đã lưu kiến trúc ưu đãi (Offer Architecture)',
      );

  Future<bool> savePlan12W(Map<String, dynamic> data) => _mutate(
        () async {
          await _service.update12WPlan(brainId.value, data);
        },
        successMessage: 'Đã lưu kế hoạch Marketing 12 tuần',
      );

  // ====================================================================
  // Marketing Loops (§18)
  // ====================================================================

  Future<bool> createLoop(Map<String, dynamic> payload) => _mutate(
        () => _service.createLoop(brainId.value, payload),
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
      Get.snackbar('Thành công', 'Đã tính toán phân bổ chuyển đổi ($modelType)', snackPosition: SnackPosition.BOTTOM);
    } catch (e) {
      Get.snackbar('Lỗi phân tích', _describe(e), snackPosition: SnackPosition.BOTTOM);
    } finally {
      isSubmitting.value = false;
    }
  }

  // ====================================================================
  // Decision Journal (§53)
  // ====================================================================

  Future<bool> createDecision(Map<String, dynamic> payload) => _mutate(
        () => _service.createDecision(brainId.value, payload),
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
        () => _service.createRecommendation(brainId.value, payload),
        successMessage: 'Đã tạo khuyến nghị mới',
      );

  Future<bool> updateRecommendationStatus(String recId, String status) => _mutate(
        () => _service.updateRecommendationStatus(recId, status),
        successMessage: 'Đã cập nhật trạng thái khuyến nghị',
      );
}

