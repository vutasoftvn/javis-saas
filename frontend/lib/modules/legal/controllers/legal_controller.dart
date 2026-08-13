import 'package:get/get.dart';
import '../../../data/services/legal_service.dart';
class LegalController extends GetxController { final status = <String, dynamic>{}.obs; @override void onInit(){super.onInit(); load();} Future<void> load() async => status.assignAll(await LegalService().getStatus()); }
