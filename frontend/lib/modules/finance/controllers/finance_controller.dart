import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../modules/finance/services/finance_service.dart';
import '../../../modules/finance/services/finance_tt58_service.dart';

class FinanceController extends GetxController {
  final service = FinanceService();
  final tt58Service = FinanceTT58Service();

  final overview = <String, dynamic>{}.obs;
  final transactions = <dynamic>[].obs;
  final documents = <dynamic>[].obs;
  final books = <dynamic>[].obs;
  final reports = <dynamic>[].obs;
  final profile = <String, dynamic>{}.obs;
  final periods = <dynamic>[].obs;
  final exceptions = <dynamic>[].obs;

  // Multi-Regime & Fiscal Year State (TT58 & TT199)
  final selectedFiscalYear = DateTime.now().year.obs;
  final fiscalYearsHistory = <Map<String, dynamic>>[].obs;
  final currentRegime = <String, dynamic>{}.obs;
  final isYearLocked = false.obs;
  final availableRegimes = <Map<String, dynamic>>[].obs;

  // Phase 4 TT58 State
  final founderLiteMetrics = Rxn<Map<String, dynamic>>();
  final reportB01 = Rxn<Map<String, dynamic>>();
  final reportB02 = Rxn<Map<String, dynamic>>();
  final reportB03 = Rxn<Map<String, dynamic>>();
  final reportF01 = Rxn<Map<String, dynamic>>();
  final isLoadingTT58 = false.obs;

  @override
  void onInit() {
    super.onInit();
    load();
    loadTT58Data();
    loadRegimeData();
  }

  Future<void> loadRegimeData() async {
    try {
      final history = await service.getFiscalYearHistory();
      fiscalYearsHistory.assignAll(history);

      final regimes = await service.getAvailableRegimes();
      availableRegimes.assignAll(regimes);

      await selectFiscalYear(selectedFiscalYear.value);
    } catch (e) {
      debugPrint('[FinanceController] loadRegimeData error: $e');
    }
  }

  Future<void> selectFiscalYear(int year) async {
    selectedFiscalYear.value = year;
    final regInfo = await service.getCurrentFiscalRegime(fiscalYear: year);
    if (regInfo != null) {
      currentRegime.assignAll(regInfo);
      isYearLocked.value = regInfo['is_locked'] ?? false;
    }
  }

  Future<Map<String, dynamic>?> previewTransition({
    required int fromYear,
    required int toYear,
    String toRegulation = "TT199_2026",
  }) async {
    return await service.previewRegimeTransition(
      fromFiscalYear: fromYear,
      toFiscalYear: toYear,
      toRegulation: toRegulation,
    );
  }

  Future<bool> executeTransition({
    required int fromYear,
    required int toYear,
    String toRegulation = "TT199_2026",
    String? notes,
  }) async {
    final result = await service.executeRegimeTransition(
      fromFiscalYear: fromYear,
      toFiscalYear: toYear,
      toRegulation: toRegulation,
      notes: notes,
    );

    if (result != null && result['status'] == 'success') {
      Get.snackbar(
        'Chuyển đổi thành công',
        'Đã nâng cấp sang chế độ $toRegulation cho năm $toYear',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
      await loadRegimeData();
      await selectFiscalYear(toYear);
      return true;
    }
    return false;
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

  Future<void> loadTT58Data() async {
    isLoadingTT58.value = true;
    try {
      final metrics = await tt58Service.getFounderLiteMetrics();
      if (metrics != null) founderLiteMetrics.value = metrics;

      final b01 = await tt58Service.getReportB01();
      if (b01 != null) reportB01.value = b01;

      final b02 = await tt58Service.getReportB02();
      if (b02 != null) reportB02.value = b02;

      final b03 = await tt58Service.getReportB03();
      if (b03 != null) reportB03.value = b03;

      final f01 = await tt58Service.getReportF01();
      if (f01 != null) reportF01.value = f01;
    } finally {
      isLoadingTT58.value = false;
    }
  }

  Future<bool> createAndPostDocument({
    required String documentNo,
    required String documentType,
    required double amount,
    required String direction,
    required String description,
    String category = 'DOANH_THU',
  }) async {
    final res = await tt58Service.createAndPostDocument(
      documentNo: documentNo,
      documentType: documentType,
      amount: amount,
      direction: direction,
      description: description,
      category: category,
    );

    if (res != null) {
      Get.snackbar(
        'Thành công',
        'Chứng từ $documentNo đã được ghi sổ thành công',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
      await load();
      await loadTT58Data();
      return true;
    }
    Get.snackbar(
      'Lỗi',
      'Không thể ghi sổ chứng từ',
      snackPosition: SnackPosition.BOTTOM,
      backgroundColor: const Color(0xFFEF4444),
      colorText: Colors.white,
    );
    return false;
  }

  Future<bool> voidDocument(String documentId, String reason) async {
    final res = await tt58Service.voidDocument(documentId, reason);
    if (res != null) {
      Get.snackbar(
        'Đã hủy chứng từ',
        'Chứng từ đã được hủy và ghi nhận bút toán đảo',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF0F172A),
        colorText: Colors.white,
      );
      await load();
      await loadTT58Data();
      return true;
    }
    return false;
  }

  Future<bool> createProfile([String mode = 'TT58_MODE_1']) async {
    final created = await service.createProfile(mode);
    if (created == null) return false;
    profile.assignAll(created);
    Get.snackbar(
      'Hồ sơ chế độ kế toán',
      'Đã thiết lập chế độ $mode',
      snackPosition: SnackPosition.BOTTOM,
      backgroundColor: const Color(0xFF10B981),
      colorText: Colors.white,
    );
    return true;
  }

  Future<bool> updateProfileMode(String mode) async {
    final updated = await service.updateProfile(mode);
    if (updated == null) return false;
    profile.assignAll(updated);
    profile.refresh();
    Get.snackbar(
      'Cập nhật thành công',
      'Đã chuyển sang chế độ $mode',
      snackPosition: SnackPosition.BOTTOM,
      backgroundColor: const Color(0xFF10B981),
      colorText: Colors.white,
    );
    await load();
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

  Future<bool> createAccountingPeriod(String startDate, String endDate) async {
    final res = await service.createPeriod(startDate, endDate);
    if (res != null) {
      Get.snackbar(
        'Thành công',
        'Đã mở kỳ kế toán mới ($startDate đến $endDate)',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
      await load();
      return true;
    }
    return false;
  }

  Future<bool> togglePeriodStatus(String periodId, String newStatus) async {
    final res = await service.changePeriodStatus(periodId, newStatus, authorizeReopen: true);
    if (res != null) {
      Get.snackbar(
        'Kỳ kế toán',
        'Trạng thái kỳ đã chuyển sang $newStatus',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF0F172A),
        colorText: Colors.white,
      );
      await load();
      return true;
    }
    return false;
  }
}
