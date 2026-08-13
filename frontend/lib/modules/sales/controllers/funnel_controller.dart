import 'package:get/get.dart';
import '../../../data/services/sales_service.dart';

class FunnelController extends GetxController {
  final isLoading = false.obs;
  final opportunities = <dynamic>[].obs;

  final stages = const ['DISCOVERY', 'QUALIFIED', 'SOLUTION', 'PROPOSAL', 'NEGOTIATION', 'WON', 'LOST'];

  @override
  void onInit() {
    super.onInit();
    loadOpportunities();
  }

  Future<void> loadOpportunities() async {
    isLoading.value = true;
    try {
      final list = await SalesService().getOpportunities();
      opportunities.assignAll(list);
    } finally {
      isLoading.value = false;
    }
  }

  List<dynamic> getOpportunitiesForStage(String stage) {
    return opportunities.where((o) => (o['stage'] as String?)?.toUpperCase() == stage).toList();
  }

  Future<void> changeStage(String oppId, String targetStage) async {
    final res = await SalesService().changeOpportunityStage(oppId, targetStage);
    if (res != null) {
      await loadOpportunities();
    }
  }
}
