import 'package:get/get.dart';
import '../../../data/services/company_runtime_service.dart';

class CompanyRuntimeController extends GetxController {
  CompanyRuntimeController({CompanyRuntimeService? service})
      : _service = service ?? CompanyRuntimeService();

  final CompanyRuntimeService _service;

  final needsYouItems = <dynamic>[].obs;
  final blockers = <dynamic>[].obs;
  final runtimeStatus = Rxn<Map<String, dynamic>>();
  final runtimeDag = Rxn<Map<String, dynamic>>();
  final currentInspectorData = Rxn<Map<String, dynamic>>();

  final loading = false.obs;
  final selectedTaskId = ''.obs;

  @override
  void onInit() {
    super.onInit();
    loadAll();
  }

  Future<void> loadAll() async {
    loading.value = true;
    try {
      final results = await Future.wait([
        _service.getNeedsYou(),
        _service.getBlockers(),
        _service.getRuntimeStatus(),
      ]);
      needsYouItems.assignAll(results[0] as List<dynamic>);
      blockers.assignAll(results[1] as List<dynamic>);
      runtimeStatus.value = results[2] as Map<String, dynamic>?;
    } finally {
      loading.value = false;
    }
  }

  Future<void> loadNeedsYou() async {
    final items = await _service.getNeedsYou();
    needsYouItems.assignAll(items);
  }

  Future<void> resolveNeedsYou(String itemId) async {
    final ok = await _service.resolveNeedsYou(itemId);
    if (ok) {
      needsYouItems.removeWhere((item) => (item['id'] ?? '').toString() == itemId);
    }
  }

  Future<void> snoozeNeedsYou(String itemId, DateTime until) async {
    final ok = await _service.snoozeNeedsYou(itemId, until);
    if (ok) {
      needsYouItems.removeWhere((item) => (item['id'] ?? '').toString() == itemId);
    }
  }

  Future<void> loadBlockers({String? status}) async {
    final list = await _service.getBlockers(status: status);
    blockers.assignAll(list);
  }

  Future<void> resolveBlocker(String blockerId) async {
    final ok = await _service.resolveBlocker(blockerId);
    if (ok) {
      await loadBlockers();
      await loadNeedsYou();
    }
  }

  Future<void> loadInspector(String taskId) async {
    selectedTaskId.value = taskId;
    if (taskId.isEmpty) {
      currentInspectorData.value = null;
      return;
    }
    loading.value = true;
    try {
      final data = await _service.getWorkInspector(taskId);
      currentInspectorData.value = data;
    } finally {
      loading.value = false;
    }
  }
}
