import 'package:get/get.dart';
import '../../../data/services/finance_service.dart';

class FinanceController extends GetxController {
  final service = FinanceService();
  final overview = <String, dynamic>{}.obs;
  final transactions = <dynamic>[].obs;
  final documents = <dynamic>[].obs;
  final books = <dynamic>[].obs;
  final reports = <dynamic>[].obs;
  final profile = <String, dynamic>{}.obs;
  final periods = <dynamic>[].obs;
  final exceptions = <dynamic>[].obs;
  @override
  void onInit() {
    super.onInit();
    load();
  }

  Future<void> load() async {
    final values = await Future.wait([
      service.getOverview(),
      service.getTransactions(),
      service.getDocuments(),
      service.getBooks(),
      service.getReports(),
      service.getPeriods(),
      service.getExceptions(),
      service.getProfile(),
    ]);
    overview.assignAll((values[0] as Map<String, dynamic>?) ?? {});
    transactions.assignAll(values[1] as List<dynamic>);
    documents.assignAll(values[2] as List<dynamic>);
    books.assignAll(values[3] as List<dynamic>);
    reports.assignAll(values[4] as List<dynamic>);
    periods.assignAll(values[5] as List<dynamic>);
    exceptions.assignAll(values[6] as List<dynamic>);
    profile.assignAll((values[7] as Map<String, dynamic>?) ?? {});
  }

  Future<bool> createProfile() async {
    final created = await service.createProfile('TT58_MODE_1');
    if (created == null) return false;
    profile.assignAll(created);
    return true;
  }

  Future<bool> activateProfile() async {
    final id = profile['id'];
    if (id == null) return false;
    final updated = await service.activateProfile('$id');
    if (updated == null) return false;
    profile['status'] = updated['status'];
    profile.refresh();
    return true;
  }
}
