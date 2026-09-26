import 'package:get/get.dart';
import '../../../core/network/api_result.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../modules/sales/services/sales_service.dart';
import '../../../data/models/commercial_models.dart';

/// Đợt 2 (plan 2026-09-26-dashboard-full-management) — CRM dashboard đọc/ghi
/// `services/company/commercial` thật qua [SalesService]. Trước đây controller
/// này dựa vào `RevenueEngineService` (`/workspaces/:id/revenue/crm/*` — route
/// chưa từng tồn tại) nên pipeline/lead/khách hàng luôn rỗng. Các view giữ
/// nguyên shape dữ liệu cũ (`pipeline.stages[].deals`, `crmAccounts[]`...) —
/// controller dựng shape đó từ bản ghi thật, không bịa số liệu.
class SalesController extends GetxController {
  SalesController({SalesService? salesService}) : _salesService = salesService ?? SalesService();

  final SalesService _salesService;

  /// Các cột Kanban — khớp màu cột trong `DealKanbanBoard`.
  static const pipelineStages = <String, String>{
    'DISCOVERY': 'Khám phá',
    'QUALIFIED': 'Đủ điều kiện',
    'PROPOSAL': 'Đề xuất',
    'NEGOTIATION': 'Đàm phán',
    'WON': 'Thắng',
    'LOST': 'Thua',
  };

  final currentTab = 0.obs;
  final leads = <dynamic>[].obs;
  final accounts = <dynamic>[].obs;
  final contacts = <dynamic>[].obs;
  final crmAccounts = <dynamic>[].obs;
  final typedLeads = <LeadModel>[].obs;
  final typedAccounts = <AccountModel>[].obs;
  final pipeline = Rxn<Map<String, dynamic>>();
  final isLoading = false.obs;
  final loadError = RxnString();

  // Account Filters
  final selectedAccountType = 'ALL'.obs;
  final searchQuery = ''.obs;
  final selectedTag = ''.obs;

  List<Map<String, dynamic>> _rawAccounts = const [];
  List<Map<String, dynamic>> _rawContacts = const [];
  List<Map<String, dynamic>> _rawOpportunities = const [];
  List<Map<String, dynamic>> _rawCustomers = const [];

  @override
  void onInit() {
    super.onInit();
    loadAll();
  }

  Future<void> loadAll() async {
    isLoading.value = true;
    loadError.value = null;
    try {
      final results = await Future.wait([
        _salesService.listAccounts(),
        _salesService.listContacts(),
        _salesService.listLeads(),
        _salesService.listOpportunities(),
        _salesService.listCustomers(),
      ]);
      final failure = results.whereType<ApiFailure<List<Map<String, dynamic>>>>().firstOrNull;
      if (failure != null) {
        loadError.value = failure.failure.message;
        AppToast.error('Không tải được dữ liệu CRM: ${failure.failure.message}');
      }
      _rawAccounts = results[0].dataOrNull ?? const [];
      _rawContacts = results[1].dataOrNull ?? const [];
      final rawLeads = results[2].dataOrNull ?? const [];
      _rawOpportunities = results[3].dataOrNull ?? const [];
      _rawCustomers = results[4].dataOrNull ?? const [];

      leads.assignAll(rawLeads.map(_leadView));
      typedLeads.assignAll(rawLeads.map(LeadModel.fromJson));
      accounts.assignAll(_rawAccounts);
      typedAccounts.assignAll(_rawAccounts.map(AccountModel.fromJson));
      contacts.assignAll(_rawContacts);
      pipeline.value = _buildPipeline();
      _applyAccountFilters();
    } finally {
      isLoading.value = false;
    }
  }

  Map<String, dynamic> _leadView(Map<String, dynamic> lead) => {
        ...lead,
        'fit_score': lead['fitScore'],
        'qualification_status': lead['qualificationStatus'] ?? lead['stage'],
      };

  String _accountName(String? accountId) =>
      _rawAccounts.firstWhereOrNull((a) => a['id'] == accountId)?['name']?.toString() ?? '—';

  Map<String, dynamic> _buildPipeline() {
    double totalValue = 0;
    double weightedValue = 0;
    final stages = pipelineStages.entries.map((stage) {
      final deals = _rawOpportunities.where((o) => (o['stage'] ?? 'DISCOVERY') == stage.key).map((o) {
        final value = (o['estimatedValue'] as num?)?.toDouble() ?? 0;
        final probability = (o['probability'] as num?)?.toDouble();
        return {
          'id': o['id'],
          'title': o['product'] ?? 'Cơ hội #${o['id']}',
          'company_name': _accountName(o['accountId']?.toString()),
          'value': value,
          'probability': probability,
          'next_action': o['expectedCloseDate'] == null ? null : 'Dự kiến chốt ${o['expectedCloseDate']}',
        };
      }).toList();
      final stageValue = deals.fold<double>(0, (sum, d) => sum + (d['value'] as double));
      if (stage.key != 'LOST') {
        totalValue += stageValue;
        for (final d in deals) {
          final p = d['probability'] as double?;
          weightedValue += (d['value'] as double) * ((p ?? 0) / (p != null && p > 1 ? 100 : 1));
        }
      }
      return {'id': stage.key, 'name': stage.value, 'deals': deals, 'stage_value': stageValue};
    }).toList();
    return {
      'stages': stages,
      'summary': {
        'total_value': totalValue,
        'weighted_value': weightedValue,
        'total_deals': _rawOpportunities.length,
      },
    };
  }

  /// Dựng danh sách khách hàng/đối tác cho `CustomerView` từ account thật +
  /// contact đầu tiên + opportunity của account đó.
  void _applyAccountFilters() {
    final customerAccountIds = _rawCustomers.map((c) => c['accountId']?.toString()).toSet();
    final query = searchQuery.value.trim().toLowerCase();
    final views = _rawAccounts.map((a) {
      final id = a['id']?.toString();
      final contact = _rawContacts.firstWhereOrNull((c) => c['accountId']?.toString() == id);
      final deals = _rawOpportunities.where((o) => o['accountId']?.toString() == id).toList();
      final wonRevenue = deals
          .where((o) => o['stage'] == 'WON')
          .fold<double>(0, (sum, o) => sum + ((o['estimatedValue'] as num?)?.toDouble() ?? 0));
      final tags = (a['tags'] as List?)?.map((e) => e.toString()).toList() ?? const <String>[];
      final category = customerAccountIds.contains(id)
          ? 'CUSTOMER'
          : (tags.contains('PARTNER') ? 'PARTNER' : (tags.contains('VENDOR') ? 'VENDOR' : 'PROSPECT'));
      return {
        ...a,
        'size_segment': a['sizeSegment'],
        'lifecycle_status': a['lifecycleStatus'],
        'category': category,
        'deals_count': deals.length,
        'won_revenue': wonRevenue,
        'contact_name': contact?['name'],
        'contact_phone': contact?['phone'],
        'contact_email': contact?['email'],
      };
    }).where((a) {
      if (selectedAccountType.value != 'ALL' && a['category'] != selectedAccountType.value) return false;
      if (selectedTag.value.isNotEmpty && !((a['tags'] as List?)?.contains(selectedTag.value) ?? false)) return false;
      if (query.isNotEmpty) {
        final haystack = '${a['name']} ${a['domain'] ?? ''} ${a['industry'] ?? ''}'.toLowerCase();
        if (!haystack.contains(query)) return false;
      }
      return true;
    }).toList();
    crmAccounts.assignAll(views);
  }

  Future<void> filterAccounts({String? type, String? search, String? tag}) async {
    if (type != null) selectedAccountType.value = type;
    if (search != null) searchQuery.value = search;
    if (tag != null) selectedTag.value = tag;
    _applyAccountFilters();
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
    // Đối tác/nhà cung cấp chưa có bảng riêng — đánh dấu bằng tag để lọc.
    final effectiveTags = {
      ...?tags,
      if (category == 'PARTNER' || category == 'VENDOR') category,
    }.toList();
    final accountResult = await _salesService.createAccount(
      name: name,
      domain: domain,
      industry: industry,
      sizeSegment: sizeSegment,
      source: source,
      tags: effectiveTags,
    );
    final account = accountResult.dataOrNull;
    if (account == null) {
      AppToast.error('Không tạo được khách hàng: ${accountResult.failureOrNull?.message ?? 'lỗi không xác định'}');
      return false;
    }
    final accountId = account['id']?.toString();
    if (accountId != null && contactName != null && contactName.trim().isNotEmpty) {
      await _salesService.createContact(
        name: contactName.trim(),
        accountId: accountId,
        phone: contactPhone,
        email: contactEmail,
      );
    }
    if (accountId != null && category == 'CUSTOMER') {
      await _salesService.createCustomer(accountId: accountId);
    }
    AppToast.success('Đã thêm $name vào CRM.', title: 'Thành công');
    await loadAll();
    return true;
  }

  void setTab(int index) {
    currentTab.value = index;
  }

  Future<void> updateDealStage(String dealId, String newStage) async {
    final result = await _salesService.updateOpportunityStage(dealId, newStage);
    switch (result) {
      case ApiSuccess():
        AppToast.info(
          'Cơ hội bán hàng đã được cập nhật sang ${pipelineStages[newStage] ?? newStage}.',
          title: 'Đã chuyển Stage',
          duration: const Duration(seconds: 2),
        );
        await loadAll();
      case ApiFailure(failure: final f):
        AppToast.error('Không cập nhật được stage: ${f.message}');
    }
  }

  /// Backend chưa có chấm điểm lead bằng AI — nói rõ thay vì giả kết quả.
  Future<void> scoreLead(String leadId) async {
    AppToast.info(
      'Chấm điểm lead tự động chưa được bật. Hãy nhờ COSA Co-Founder đánh giá lead trong khung chat.',
      title: 'Chưa hỗ trợ',
    );
  }

  /// Chuyển lead thành cơ hội bán hàng: đảm bảo có account (tạo theo tên
  /// công ty nếu lead chưa gắn), tạo opportunity trỏ về lead, đánh dấu lead
  /// CONVERTED.
  Future<void> convertLeadToOpportunity(String leadId, String name, String company) async {
    final lead = _rawLeadsById(leadId);
    var accountId = lead?['accountId']?.toString();
    if (accountId == null || accountId.isEmpty) {
      final accountName = company.trim().isNotEmpty ? company.trim() : name;
      final existing = _rawAccounts.firstWhereOrNull(
        (a) => a['name']?.toString().toLowerCase() == accountName.toLowerCase(),
      );
      accountId = existing?['id']?.toString();
      if (accountId == null) {
        final created = await _salesService.createAccount(name: accountName, source: 'lead');
        accountId = created.dataOrNull?['id']?.toString();
        if (accountId == null) {
          AppToast.error('Không tạo được account cho lead: ${created.failureOrNull?.message}');
          return;
        }
      }
    }
    final opp = await _salesService.createOpportunity(
      accountId: accountId,
      product: 'Hợp đồng $company ($name)',
      estimatedValue: (lead?['value'] as num?)?.toDouble(),
      sourceLeadId: leadId,
    );
    if (opp is ApiFailure) {
      AppToast.error('Không tạo được cơ hội bán hàng: ${opp.failureOrNull?.message}');
      return;
    }
    await _salesService.updateLeadStage(leadId, 'CONVERTED');
    AppToast.success(
      'Lead $name đã được đưa vào Pipeline Kanban.',
      title: 'Đã Tạo Cơ Hội Bán Hàng',
      duration: const Duration(seconds: 2),
    );
    await loadAll();
  }

  Map<String, dynamic>? _rawLeadsById(String leadId) {
    for (final lead in leads.whereType<Map<String, dynamic>>()) {
      if (lead['id']?.toString() == leadId) return lead;
    }
    return null;
  }

  /// Soạn outreach bằng AI chưa có endpoint riêng — outreach thật phải qua
  /// agent + approval (gửi tin nhắn ra ngoài là hành động rủi ro cao).
  Future<Map<String, dynamic>?> generateOutreach({
    required String leadId,
    String channel = 'email',
    String tone = 'professional',
    String? focusPainPoint,
  }) async {
    AppToast.info(
      'Soạn outreach tự động chưa được bật. Hãy nhờ COSA Co-Founder soạn nháp — gửi ra ngoài luôn cần phê duyệt.',
      title: 'Chưa hỗ trợ',
    );
    return null;
  }
}
