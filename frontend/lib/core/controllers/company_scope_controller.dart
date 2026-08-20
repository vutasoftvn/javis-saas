import 'package:get/get.dart';

class CompanyScopeController extends GetxController {
  final operatingUnitId = Rxn<int>();
  final offeringId = Rxn<int>();
  final initiativeId = Rxn<int>();

  bool get isGlobalScope => operatingUnitId.value == null;

  void setScope({int? operatingUnitId, int? offeringId, int? initiativeId}) {
    this.operatingUnitId.value = operatingUnitId;
    this.offeringId.value = offeringId;
    this.initiativeId.value = initiativeId;
  }

  void clearScope() {
    operatingUnitId.value = null;
    offeringId.value = null;
    initiativeId.value = null;
  }
}
