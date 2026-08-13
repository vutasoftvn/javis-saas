import 'package:get/get.dart';
import '../../../data/services/finance_service.dart';

class FinanceController extends GetxController {
  final service = FinanceService();
  final overview = <String, dynamic>{}.obs;
  final transactions = <dynamic>[].obs;
  final documents = <dynamic>[].obs;
  final periods = <dynamic>[].obs;
  final exceptions = <dynamic>[].obs;
  @override
  void onInit() { super.onInit(); load(); }
  Future<void> load() async {
    final values = await Future.wait([service.getOverview(), service.getTransactions(), service.getDocuments(), service.getPeriods(), service.getExceptions()]);
    overview.assignAll((values[0] as Map<String, dynamic>?) ?? {});
    transactions.assignAll(values[1] as List<dynamic>); documents.assignAll(values[2] as List<dynamic>);
    periods.assignAll(values[3] as List<dynamic>); exceptions.assignAll(values[4] as List<dynamic>);
  }
}
