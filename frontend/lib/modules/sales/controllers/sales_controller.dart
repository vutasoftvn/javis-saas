import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../modules/sales/services/sales_service.dart';
import '../../../modules/sales/services/revenue_engine_service.dart';
import '../../../data/models/commercial_models.dart';

class SalesController extends GetxController {
  final SalesService _salesService = SalesService();
  final RevenueEngineService _revenueService = RevenueEngineService();

  final currentTab = 0.obs;
  final leads = <dynamic>[].obs;
  final accounts = <dynamic>[].obs;
  final contacts = <dynamic>[].obs;
  final crmAccounts = <dynamic>[].obs;
  final typedLeads = <LeadModel>[].obs;
  final typedAccounts = <AccountModel>[].obs;
  final pipeline = Rxn<Map<String, dynamic>>();
  final isLoading = false.obs;

  // Account Filters
  final selectedAccountType = 'ALL'.obs;
  final searchQuery = ''.obs;
  final selectedTag = ''.obs;

  @override
  void onInit() {
    super.onInit();
    loadAll();
  }

  Future<void> loadAll() async {
    isLoading.value = true;
    try {
      final pipelineData = await _revenueService.getPipeline();
      final leadList = await _revenueService.getLeads();
      final crmAccList = await _revenueService.getAccounts(
        accountType: selectedAccountType.value == 'ALL' ? null : selectedAccountType.value,
        search: searchQuery.value.isEmpty ? null : searchQuery.value,
        tag: selectedTag.value.isEmpty ? null : selectedTag.value,
      );
      final accList = await _salesService.getAccounts();
      final conList = await _salesService.getContacts();

      pipeline.value = pipelineData;
      final finalLeads = leadList.isNotEmpty ? leadList : await _salesService.getLeads();
      leads.assignAll(finalLeads);
      typedLeads.assignAll(finalLeads.map((e) => LeadModel.fromJson(Map<String, dynamic>.from(e as Map))));
      crmAccounts.assignAll(crmAccList);
      accounts.assignAll(accList);
      typedAccounts.assignAll(accList.map((e) => AccountModel.fromJson(Map<String, dynamic>.from(e as Map))));
      contacts.assignAll(conList);
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> filterAccounts({String? type, String? search, String? tag}) async {
    if (type != null) selectedAccountType.value = type;
    if (search != null) searchQuery.value = search;
    if (tag != null) selectedTag.value = tag;

    final list = await _revenueService.getAccounts(
      accountType: selectedAccountType.value == 'ALL' ? null : selectedAccountType.value,
      search: searchQuery.value.isEmpty ? null : searchQuery.value,
      tag: selectedTag.value.isEmpty ? null : selectedTag.value,
    );
    crmAccounts.assignAll(list);
  }

  Future<bool> createAccount({
    required String name,
    String category = 'CUSTOMER',
    String? domain,
    String? industry,
    String? sizeSegment,
    String? source,
    String? lifecycleStatus,
    List<String>? tags,
    String? contactName,
    String? contactPhone,
    String? contactEmail,
  }) async {
    final res = await _revenueService.createAccount(
      name: name,
      category: category,
      domain: domain,
      industry: industry,
      sizeSegment: sizeSegment,
      source: source,
      lifecycleStatus: lifecycleStatus,
      tags: tags,
      contactName: contactName,
      contactPhone: contactPhone,
      contactEmail: contactEmail,
    );

    if (res != null && res['status'] == 'success') {
      Get.snackbar(
        'Thành công',
        res['message']?.toString() ?? 'Đã thêm $name vào CRM.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
      await loadAll();
      return true;
    }
    return false;
  }

  void setTab(int index) {
    currentTab.value = index;
  }

  Future<void> updateDealStage(String dealId, String newStage) async {
    final res = await _revenueService.updateOpportunityStage(
      opportunityId: dealId,
      stage: newStage,
    );
    if (res != null && res['status'] == 'success') {
      Get.snackbar(
        'Đã chuyển Stage',
        'Cơ hội bán hàng đã được cập nhật sang $newStage.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF0F172A),
        colorText: Colors.white,
        duration: const Duration(seconds: 2),
      );
      final pData = await _revenueService.getPipeline();
      if (pData != null) pipeline.value = pData;
    }
  }

  Future<void> scoreLead(String leadId) async {
    final res = await _revenueService.scoreLead(leadId);
    if (res != null && res['status'] == 'success') {
      Get.snackbar(
        'AI Đã Chấm Điểm',
        'Fit Score: ${res['data']?['fit_score']} | Phân loại: ${res['data']?['qualification_status']}',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF0F172A),
        colorText: Colors.white,
        duration: const Duration(seconds: 2),
      );
      final updatedLeads = await _revenueService.getLeads();
      leads.assignAll(updatedLeads);
    }
  }

  Future<void> convertLeadToOpportunity(String leadId, String name, String company) async {
    final res = await _revenueService.convertLeadToOpportunity(
      leadId: leadId,
      title: 'Hợp đồng $company ($name)',
    );
    if (res != null && res['status'] == 'success') {
      Get.snackbar(
        'Đã Tạo Cơ Hội Bán Hàng',
        'Lead $name đã được đưa vào Pipeline Kanban.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF0F172A),
        colorText: Colors.white,
        duration: const Duration(seconds: 2),
      );
      await loadAll();
    }
  }

  Future<Map<String, dynamic>?> generateOutreach({
    required String leadId,
    String channel = 'email',
    String tone = 'professional',
    String? focusPainPoint,
  }) async {
    final res = await _revenueService.generateOutreach(
      leadId: leadId,
      channel: channel,
      tone: tone,
      focusPainPoint: focusPainPoint,
    );
    if (res != null && res['status'] == 'success') {
      Get.snackbar(
        'Đã Gửi Duyệt Outreach',
        res['data']?['message']?.toString() ?? 'Bản nháp đã nằm trên CEO Command Center.',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF0F172A),
        colorText: Colors.white,
        duration: const Duration(seconds: 3),
      );
    }
    return res?['data'] as Map<String, dynamic>? ?? res;
  }
}
