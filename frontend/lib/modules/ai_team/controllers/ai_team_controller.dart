import 'package:get/get.dart';

import '../../../data/services/function_status_service.dart';
import '../../../data/services/outcomes_service.dart';

class AiTeamController extends GetxController {
  AiTeamController({FunctionStatusService? statusService, OutcomesService? outcomesService})
      : _statusService = statusService ?? FunctionStatusService(),
        _outcomesService = outcomesService ?? OutcomesService();

  final FunctionStatusService _statusService;
  final OutcomesService _outcomesService;
  final functions = <Map<String, dynamic>>[].obs;
  final outcomes = <dynamic>[].obs;
  final loading = false.obs;

  @override
  void onInit() { super.onInit(); load(); }

  Future<void> load() async {
    loading.value = true;
    try {
      final values = await Future.wait([_statusService.getStatuses(), _outcomesService.getOutcomes()]);
      functions.assignAll(values[0] as List<Map<String, dynamic>>);
      outcomes.assignAll(values[1]);
    } finally {
      loading.value = false;
    }
  }
}
