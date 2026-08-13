import 'package:get/get.dart';
import '../../../data/services/sales_service.dart';

class SalesTodayController extends GetxController {
  final isLoading = false.obs;
  final funnelMetrics = <String, dynamic>{}.obs;
  final openOpportunities = <dynamic>[].obs;
  final leads = <dynamic>[].obs;

  @override
  void onInit() {
    super.onInit();
    refreshData();
  }

  Future<void> refreshData() async {
    isLoading.value = true;
    try {
      final metrics = await SalesService().getFunnelMetrics();
      if (metrics != null) {
        funnelMetrics.assignAll(metrics);
        if (metrics['open_opportunities'] is List) {
          openOpportunities.assignAll(metrics['open_opportunities'] as List<dynamic>);
        }
      }
      final leadList = await SalesService().getLeads();
      leads.assignAll(leadList);
    } finally {
      isLoading.value = false;
    }
  }
}
