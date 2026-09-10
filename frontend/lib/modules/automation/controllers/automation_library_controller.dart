// COSA Automation MVP — Automation Library controller (Task 7).

import 'package:get/get.dart';

import '../../../core/network/api_result.dart';
import '../models/automation_models.dart';
import '../services/automation_service.dart';

enum AutomationLoadState { idle, loading, ready, empty, forbidden, unavailable, failed }

class AutomationLibraryController extends GetxController {
  AutomationLibraryController({AutomationService? service})
      : _service = service ?? AutomationService();

  final AutomationService _service;

  final state = AutomationLoadState.idle.obs;
  final definitions = <AutomationDefinitionView>[].obs;
  final errorMessage = RxnString();

  final busyKey = RxnString(); // definition id currently mutating

  Future<void> load() async {
    state.value = AutomationLoadState.loading;
    errorMessage.value = null;
    final res = await _service.listDefinitions();
    res.when(
      success: (data, _) {
        definitions.assignAll(data);
        state.value = data.isEmpty ? AutomationLoadState.empty : AutomationLoadState.ready;
      },
      failure: (f) => _applyFailure(f),
    );
  }

  void _applyFailure(ApiFailureDetail f) {
    errorMessage.value = f.message;
    state.value = switch (f.code) {
      ApiFailureCode.forbidden => AutomationLoadState.forbidden,
      ApiFailureCode.unavailable => AutomationLoadState.unavailable,
      _ => AutomationLoadState.failed,
    };
  }

  Future<AutomationDefinitionView?> configure({
    required String automationKey,
    required Map<String, dynamic> configuration,
    required Map<String, dynamic> triggerContract,
  }) async {
    final res = await _service.configure(
      definitionId: 'unused',
      automationKey: automationKey,
      configuration: configuration,
      triggerContract: triggerContract,
    );
    return res.when(
      success: (data, _) {
        _upsert(data);
        return data;
      },
      failure: (f) {
        errorMessage.value = f.message;
        return null;
      },
    );
  }

  Future<bool> publish(String definitionId) => _mutate(definitionId, _service.publish);
  Future<bool> suspend(String definitionId) => _mutate(definitionId, _service.suspend);

  Future<AutomationInvocationView?> runNow(String definitionId) async {
    final res = await _service.runNow(
      definitionId: definitionId,
      clientRequestId: 'ui-${DateTime.now().microsecondsSinceEpoch}',
    );
    return res.when(
      success: (data, _) => data,
      failure: (f) {
        errorMessage.value = f.message;
        return null;
      },
    );
  }

  Future<bool> _mutate(
    String definitionId,
    Future<ApiResult<AutomationDefinitionView>> Function(String) op,
  ) async {
    busyKey.value = definitionId;
    final ApiResult<AutomationDefinitionView> res = await op(definitionId);
    busyKey.value = null;
    return res.when(
      success: (data, _) {
        _upsert(data);
        return true;
      },
      failure: (f) {
        errorMessage.value = f.message;
        return false;
      },
    );
  }

  void _upsert(AutomationDefinitionView v) {
    final i = definitions.indexWhere((d) => d.automationKey == v.automationKey);
    if (i >= 0) {
      definitions[i] = v;
    } else {
      definitions.add(v);
    }
    definitions.refresh();
  }
}
