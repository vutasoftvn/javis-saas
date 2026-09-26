import 'package:http/http.dart' as http;

import '../../../core/network/api_auth_resolver.dart';
import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../../../data/models/commercial_models.dart';

/// Đợt 2 (plan 2026-09-26-dashboard-full-management) — client CRM duy nhất,
/// gọi `services/company/commercial` qua `MvpRequestClient` + contract
/// `commercial.*`. Trước đây service này tự ghép URL tới
/// `/commercial/workspaces/:id/*` (chưa từng có backend) và nuốt mọi lỗi
/// thành danh sách rỗng — CRM trên dashboard luôn trống.
///
/// Method `list*`/`create*`/`update*` trả `ApiResult` thật. Các getter
/// `get*` trả `List<dynamic>` giữ lại cho controller cũ (`SalesToday`,
/// `Funnel`) — rỗng khi lỗi, nhưng controller mới dùng bản `ApiResult`.
class SalesService {
  SalesService({
    MvpRequestClient? client,
    http.Client? httpClient,
    ApiAuthResolver? authResolver,
  })  : _client = client ?? MvpRequestClient(httpClient: httpClient),
        _authResolver = authResolver ?? const DefaultApiAuthResolver();

  final MvpRequestClient _client;
  final ApiAuthResolver _authResolver;

  static List<Map<String, dynamic>> _listUnder(Object? raw, String key) {
    final list = raw is Map<String, dynamic> ? raw[key] : raw;
    return list is List ? list.whereType<Map<String, dynamic>>().toList() : const [];
  }

  static Map<String, dynamic> _asMap(Object? raw) {
    if (raw is Map<String, dynamic>) return raw;
    throw const FormatException('Expected JSON object in CRM response');
  }

  /// Body tạo bản ghi CRM bắt buộc `workspaceId` (service Company kiểm tra
  /// membership theo đúng id này) — lấy từ workspace đang chọn, không nhận
  /// từ caller để tránh ghi nhầm tenant.
  Future<String?> _workspaceId() => _authResolver.workspaceId();

  // ─── Accounts ───

  Future<ApiResult<List<Map<String, dynamic>>>> listAccounts() {
    return _client.request<List<Map<String, dynamic>>>(
      MvpEndpoint.commercialAccountsList,
      decode: (raw) => _listUnder(raw, 'accounts'),
    );
  }

  Future<ApiResult<Map<String, dynamic>>> createAccount({
    required String name,
    String? domain,
    String? industry,
    String? sizeSegment,
    String? source,
    List<String>? tags,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.commercialAccountCreate,
      body: {
        'workspaceId': await _workspaceId(),
        'name': name,
        'domain': ?_nonEmpty(domain),
        'industry': ?_nonEmpty(industry),
        'sizeSegment': ?_nonEmpty(sizeSegment),
        'source': ?_nonEmpty(source),
        if (tags != null && tags.isNotEmpty) 'tags': tags,
      },
      decode: _asMap,
    );
  }

  // ─── Contacts ───

  Future<ApiResult<List<Map<String, dynamic>>>> listContacts({String? accountId}) {
    return _client.request<List<Map<String, dynamic>>>(
      MvpEndpoint.commercialContactsList,
      query: {'accountId': ?accountId},
      decode: (raw) => _listUnder(raw, 'contacts'),
    );
  }

  Future<ApiResult<Map<String, dynamic>>> createContact({
    required String name,
    String? accountId,
    String? phone,
    String? email,
    String? title,
    String? projectId,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.commercialContactCreate,
      body: {
        'workspaceId': await _workspaceId(),
        'name': name,
        'accountId': ?accountId,
        'phone': ?_nonEmpty(phone),
        'email': ?_nonEmpty(email),
        'title': ?_nonEmpty(title),
        'projectId': ?projectId,
      },
      decode: _asMap,
    );
  }

  // ─── Leads ───

  Future<ApiResult<List<Map<String, dynamic>>>> listLeads() async {
    // `GET /commercial/leads` nhận workspaceId qua query (handler Company).
    final workspaceId = await _workspaceId();
    return _client.request<List<Map<String, dynamic>>>(
      MvpEndpoint.commercialLeadsList,
      query: {'workspaceId': ?workspaceId},
      decode: (raw) => _listUnder(raw, 'leads'),
    );
  }

  Future<ApiResult<Map<String, dynamic>>> createLead({
    required String name,
    String? company,
    double? value,
    String? source,
    String? accountId,
    String? projectId,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.commercialLeadCreate,
      body: {
        'workspaceId': await _workspaceId(),
        'name': name,
        'company': ?_nonEmpty(company),
        'value': ?value,
        'source': ?_nonEmpty(source),
        'accountId': ?accountId,
        'projectId': ?projectId,
      },
      decode: _asMap,
    );
  }

  Future<ApiResult<Map<String, dynamic>>> updateLeadStage(String leadId, String stage) {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.commercialLeadStageUpdate,
      pathParams: {'id': leadId},
      body: {'stage': stage},
      decode: _asMap,
    );
  }

  // ─── Opportunities ───

  Future<ApiResult<List<Map<String, dynamic>>>> listOpportunities({String? stage, String? accountId}) {
    return _client.request<List<Map<String, dynamic>>>(
      MvpEndpoint.commercialOpportunitiesList,
      query: {'stage': ?stage, 'accountId': ?accountId},
      decode: (raw) => _listUnder(raw, 'opportunities'),
    );
  }

  Future<ApiResult<Map<String, dynamic>>> createOpportunity({
    required String accountId,
    String? product,
    double? estimatedValue,
    String? sourceLeadId,
    String? primaryContactId,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.commercialOpportunityCreate,
      body: {
        'workspaceId': await _workspaceId(),
        'accountId': accountId,
        'product': ?_nonEmpty(product),
        'estimatedValue': ?estimatedValue,
        'sourceLeadId': ?sourceLeadId,
        'primaryContactId': ?primaryContactId,
      },
      decode: _asMap,
    );
  }

  Future<ApiResult<Map<String, dynamic>>> updateOpportunityStage(String opportunityId, String stage) {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.commercialOpportunityStageUpdate,
      pathParams: {'id': opportunityId},
      body: {'stage': stage},
      decode: _asMap,
    );
  }

  // ─── Customers ───

  Future<ApiResult<List<Map<String, dynamic>>>> listCustomers() {
    return _client.request<List<Map<String, dynamic>>>(
      MvpEndpoint.commercialCustomersList,
      decode: (raw) => _listUnder(raw, 'customers'),
    );
  }

  Future<ApiResult<Map<String, dynamic>>> createCustomer({
    required String accountId,
    String? acquiredFromOpportunityId,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.commercialCustomerCreate,
      body: {
        'workspaceId': await _workspaceId(),
        'accountId': accountId,
        'acquiredFromOpportunityId': ?acquiredFromOpportunityId,
      },
      decode: _asMap,
    );
  }

  // ─── Getter giữ tương thích cho controller cũ ───

  Future<List<AccountModel>> getTypedAccounts() async =>
      (await getAccounts()).map((e) => AccountModel.fromJson(Map<String, dynamic>.from(e as Map))).toList();

  Future<List<LeadModel>> getTypedLeads() async =>
      (await getLeads()).map((e) => LeadModel.fromJson(Map<String, dynamic>.from(e as Map))).toList();

  Future<List<OpportunityModel>> getTypedOpportunities({String? stage, String? accountId}) async =>
      (await getOpportunities(stage: stage, accountId: accountId))
          .map((e) => OpportunityModel.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();

  Future<List<CustomerModel>> getTypedCustomers() async =>
      (await getCustomers()).map((e) => CustomerModel.fromJson(Map<String, dynamic>.from(e as Map))).toList();

  Future<List<dynamic>> getAccounts() async => (await listAccounts()).dataOrNull ?? const [];

  Future<List<dynamic>> getContacts({String? accountId}) async =>
      (await listContacts(accountId: accountId)).dataOrNull ?? const [];

  Future<List<dynamic>> getLeads() async => (await listLeads()).dataOrNull ?? const [];

  Future<List<dynamic>> getOpportunities({String? stage, String? accountId}) async =>
      (await listOpportunities(stage: stage, accountId: accountId)).dataOrNull ?? const [];

  Future<List<dynamic>> getCustomers() async => (await listCustomers()).dataOrNull ?? const [];

  Future<Map<String, dynamic>?> changeOpportunityStage(String oppId, String targetStage) async =>
      (await updateOpportunityStage(oppId, targetStage)).dataOrNull;

  /// Chưa có endpoint funnel tổng hợp ở backend — dựng từ dữ liệu thật
  /// (opportunity đang mở) thay vì gọi route không tồn tại.
  Future<Map<String, dynamic>?> getFunnelMetrics() async {
    final result = await listOpportunities();
    final opportunities = result.dataOrNull;
    if (opportunities == null) return null;
    final open = opportunities.where((o) => !const {'WON', 'LOST'}.contains(o['stage'])).toList();
    return {'open_opportunities': open, 'total_opportunities': opportunities.length};
  }

  static String? _nonEmpty(String? value) {
    final trimmed = value?.trim();
    return trimmed == null || trimmed.isEmpty ? null : trimmed;
  }
}
