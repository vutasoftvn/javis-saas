import 'package:get/get.dart';
import '../../../data/services/sales_service.dart';

class SalesController extends GetxController {
  final currentTab = 0.obs;
  final leads = <dynamic>[].obs;
  final accounts = <dynamic>[].obs;
  final contacts = <dynamic>[].obs;
  final isLoading = false.obs;

  @override
  void onInit() {
    super.onInit();
    loadAll();
  }

  Future<void> loadAll() async {
    isLoading.value = true;
    try {
      final leadList = await SalesService().getLeads();
      final accList = await SalesService().getAccounts();
      final conList = await SalesService().getContacts();
      leads.assignAll(leadList);
      accounts.assignAll(accList);
      contacts.assignAll(conList);
    } finally {
      isLoading.value = false;
    }
  }

  void setTab(int index) {
    currentTab.value = index;
  }
}
