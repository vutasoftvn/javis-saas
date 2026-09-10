// COSA Automation MVP — Run Inspector + Needs You controller (Task 8).

import 'package:get/get.dart';

import '../../../core/network/api_result.dart';
import '../models/automation_models.dart';
import '../services/automation_service.dart';
import 'automation_library_controller.dart' show AutomationLoadState;

class AutomationRunInspectorController extends GetxController {
  AutomationRunInspectorController({AutomationService? service})
      : _service = service ?? AutomationService();

  final AutomationService _service;

  final state = AutomationLoadState.idle.obs;
  final inspector = Rxn<AutomationRunInspector>();
  final invocation = Rxn<AutomationInvocationView>();
  final needsYouItems = <NeedsYouItem>[].obs;
  final errorMessage = RxnString();

  Future<void> load(String invocationId) async {
    state.value = AutomationLoadState.loading;
    errorMessage.value = null;
    final invRes = await _service.getInvocation(invocationId);
    invRes.when(
      success: (data, _) => invocation.value = data,
      failure: (f) => errorMessage.value = f.message,
    );
    final res = await _service.runInspector(invocationId);
    res.when(
      success: (data, _) {
        inspector.value = data;
        state.value = AutomationLoadState.ready;
      },
      failure: (f) {
        state.value = switch (f.code) {
          ApiFailureCode.forbidden => AutomationLoadState.forbidden,
          ApiFailureCode.unavailable => AutomationLoadState.unavailable,
          _ => AutomationLoadState.failed,
        };
        errorMessage.value = f.message;
      },
    );
  }

  Future<void> loadNeedsYou() async {
    final res = await _service.needsYou();
    res.when(
      success: (data, _) => needsYouItems.assignAll(data),
      failure: (f) => errorMessage.value = f.message,
    );
  }

  Future<bool> cancel() async {
    final inv = invocation.value;
    if (inv == null || !inv.isCancellable) return false;
    final res = await _service.cancel(invocationId: inv.id, expectedVersion: inv.version);
    return res.when(
      success: (data, _) {
        invocation.value = data;
        return true;
      },
      failure: (f) {
        errorMessage.value = f.message;
        return false;
      },
    );
  }
}
