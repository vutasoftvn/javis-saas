import 'package:get/get.dart'; import '../../../data/services/sales_service.dart';
class SalesController extends GetxController { final leads=<dynamic>[].obs; @override void onInit(){super.onInit(); load();} Future<void> load() async => leads.assignAll(await SalesService().getLeads()); }
