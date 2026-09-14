// Task 7 (PHẠM VI MỞ RỘNG 2026-09-14) — controller GetX tối thiểu để mở route
// strategy thật. Controller KHÔNG có BuildContext nên không tự mở dialog
// (showOkrWeeklyGeneratorDialog) — chỉ trả Future<void>/throw khi lỗi, View
// (strategy_view.dart) mới là nơi gọi dialog sau khi publish() thành công.
import 'package:get/get.dart';
import '../models/mvp_strategy_models.dart';
import '../services/okr_service.dart';

class StrategyController extends GetxController {
  StrategyController({OkrService? okrService}) : _okrService = okrService ?? OkrService();

  final OkrService _okrService;

  final isLoading = false.obs;
  final objectives = <MvpObjective>[].obs;
  final errorMessage = RxnString();

  @override
  void onInit() {
    super.onInit();
    loadObjectives();
  }

  Future<void> loadObjectives() async {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      final result = await _okrService.getObjectives();
      if (result.isFailure) {
        errorMessage.value = result.errorMessage;
        return;
      }
      objectives.value = result.items.map(MvpObjective.fromJson).toList();
    } finally {
      isLoading.value = false;
    }
  }

  /// Publish 1 Objective rồi refresh danh sách. Ném lỗi ra ngoài nếu thất
  /// bại — View xử lý hiển thị (snackbar/toast), controller không biết UI.
  Future<void> publish(String objectiveId) async {
    await _okrService.publishObjective(objectiveId);
    await loadObjectives();
  }
}
