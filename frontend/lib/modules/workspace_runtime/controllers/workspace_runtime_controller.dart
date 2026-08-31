import 'package:get/get.dart';
import '../../../core/network/api_result.dart';
import '../services/workspace_runtime_service.dart';
import '../models/mvp_runtime_models.dart';

class WorkspaceRuntimeController extends GetxController {
  WorkspaceRuntimeController({WorkspaceRuntimeService? service})
      : _service = service ?? WorkspaceRuntimeService();

  final WorkspaceRuntimeService _service;

  final needsYouResult = Rxn<ApiResult<List<MvpRuntimeItem>>>();
  final blockersResult = Rxn<ApiResult<List<MvpRuntimeItem>>>();
  final sourceStatusResult = Rxn<ApiResult<List<MvpSourceStatus>>>();
  final currentInspectorResult = Rxn<ApiResult<MvpRuntimeItemDetail>>();

  final loading = false.obs;
  final selectedTaskId = ''.obs;

  List<MvpRuntimeItem> get needsYouItems =>
      needsYouResult.value is ApiSuccess<List<MvpRuntimeItem>>
          ? (needsYouResult.value as ApiSuccess<List<MvpRuntimeItem>>).data
          : [];

  List<MvpRuntimeItem> get blockers =>
      blockersResult.value is ApiSuccess<List<MvpRuntimeItem>>
          ? (blockersResult.value as ApiSuccess<List<MvpRuntimeItem>>).data
          : [];

  List<MvpSourceStatus> get sourceStatuses =>
      sourceStatusResult.value is ApiSuccess<List<MvpSourceStatus>>
          ? (sourceStatusResult.value as ApiSuccess<List<MvpSourceStatus>>).data
          : [];

  @override
  void onInit() {
    super.onInit();
    loadAll();
  }

  Future<void> loadAll() async {
    loading.value = true;
    try {
      final results = await Future.wait([
        _service.getNeedsYouResult(),
        _service.getBlockersResult(),
        _service.getRuntimeStatusResult(),
      ]);
      needsYouResult.value = results[0] as ApiResult<List<MvpRuntimeItem>>;
      blockersResult.value = results[1] as ApiResult<List<MvpRuntimeItem>>;
      sourceStatusResult.value = results[2] as ApiResult<List<MvpSourceStatus>>;
    } finally {
      loading.value = false;
    }
  }

  Future<void> loadNeedsYou() async {
    loading.value = true;
    try {
      needsYouResult.value = await _service.getNeedsYouResult();
    } finally {
      loading.value = false;
    }
  }

  Future<void> snoozeNeedsYou(String sourceKind, String sourceId, DateTime until) async {
    final res = await _service.snoozeNeedsYouResult(
      sourceKind: sourceKind,
      sourceId: sourceId,
      until: until,
    );
    if (res is ApiSuccess) {
      await loadNeedsYou();
    }
  }

  Future<void> loadBlockers() async {
    loading.value = true;
    try {
      blockersResult.value = await _service.getBlockersResult();
    } finally {
      loading.value = false;
    }
  }

  Future<void> loadInspector(String sourceKind, String sourceId) async {
    selectedTaskId.value = sourceId;
    if (sourceId.isEmpty) {
      currentInspectorResult.value = null;
      return;
    }
    loading.value = true;
    try {
      currentInspectorResult.value = await _service.getWorkInspectorResult(
        sourceKind: sourceKind,
        sourceId: sourceId,
      );
    } finally {
      loading.value = false;
    }
  }
}
