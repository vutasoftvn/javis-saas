import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../../../core/network/api_client.dart';
import '../../../data/models/company_pulse_model.dart';
import '../../../data/models/founder_decision_model.dart';
import '../../../data/models/workforce_pack_model.dart';

/// G2 P0.8 / G3 §10.4: `chatWithCoFounder` used to collapse every failure
/// (non-200 status, network exception, JSON decode error) into a `null`
/// return, which the caller then displayed as a fabricated "I've noted this
/// and I'm coordinating..." success message. Thrown on failure now, so the
/// caller can render a real error instead of pretending the message landed.
class CoFounderChatException implements Exception {
  final String message;
  CoFounderChatException(this.message);

  @override
  String toString() => message;
}

class CoFounderApiService {
  /// Lấy thông tin nhịp tim tổng thể của doanh nghiệp (Company Pulse) từ Backend
  static Future<CompanyPulseModel> getCompanyPulse({dynamic workspaceId, dynamic projectId}) async {
    try {
      final wId = workspaceId?.toString() ?? '1';
      final pId = projectId?.toString() ?? '1';

      // 1. Fetch tasks
      final tasksRes = await ApiClient.get('/operations/tasks?workspaceId=$wId');
      int activeGoals = 0;
      int goalsOnTrack = 0;
      if (tasksRes.statusCode == 200) {
        final data = jsonDecode(utf8.decode(tasksRes.bodyBytes));
        final tasksList = (data is Map ? data['tasks'] : data) as List? ?? [];
        activeGoals = tasksList.length;
        goalsOnTrack = tasksList.where((t) => t['status'] == 'completed' || t['status'] == 'in_progress').length;
      }

      // 2. Fetch decisions
      final decisions = await listPendingDecisions(workspaceId: wId);

      // 3. Fetch Next Best Actions
      final top3 = await getTop3Focus(workspaceId: wId, projectId: pId);

      return CompanyPulseModel(
        goalsOnTrack: goalsOnTrack,
        totalActiveGoals: activeGoals > 0 ? activeGoals : 1,
        activeMissions: top3.length,
        needsDecisionCount: decisions.length,
        pendingApprovalsCount: 0,
        majorRisksCount: 0,
        updatedAt: DateTime.now(),
      );
    } catch (e) {
      debugPrint('[CoFounderApiService] getCompanyPulse exception: $e');
    }
    return CompanyPulseModel(
      goalsOnTrack: 0,
      totalActiveGoals: 0,
      activeMissions: 0,
      needsDecisionCount: 0,
      pendingApprovalsCount: 0,
      majorRisksCount: 0,
      updatedAt: DateTime.now(),
    );
  }

  /// Lấy Top 3 hành động tốt nhất hôm nay (Next Best Action) từ Backend
  static Future<List<NextBestActionModel>> getTop3Focus({dynamic workspaceId, dynamic projectId}) async {
    try {
      final pId = projectId?.toString() ?? '1';
      final response = await ApiClient.get('/operations/strategy/projects/$pId/next-best-actions');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final items = (data['items'] as List<dynamic>?) ?? [];
        return items.map((e) => NextBestActionModel.fromJson(e as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('[CoFounderApiService] getTop3Focus exception: $e');
    }
    return [];
  }

  /// Lấy danh sách các quyết định đang chờ Founder duyệt ('Waiting for You') từ Backend
  static Future<List<FounderDecisionModel>> listPendingDecisions({dynamic workspaceId}) async {
    try {
      final q = workspaceId != null ? '?workspaceId=${workspaceId.toString()}' : '';
      final response = await ApiClient.get('/operations/strategy/decision-records$q');
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final List<dynamic> list = data is List ? data : (data['decisionRecords'] as List? ?? data['records'] as List? ?? []);
        return list.map((e) => FounderDecisionModel.fromJson(e as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('[CoFounderApiService] listPendingDecisions exception: $e');
    }
    return [];
  }

  /// Chốt quyết định chiến lược
  static Future<bool> resolveDecision({
    required dynamic decisionId,
    required String decisionMade,
    String? founderNotes,
  }) async {
    try {
      final response = await ApiClient.patch(
        '/operations/strategy/decision-records/${decisionId.toString()}',
        body: {
          'decision': decisionMade,
          'rationale': founderNotes ?? 'Decided by founder',
        },
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[CoFounderApiService] resolveDecision error: $e');
      return false;
    }
  }

  /// Trò chuyện và nhận chỉ đạo từ Co-Founder.
  static Future<Map<String, dynamic>> chatWithCoFounder({
    required String message,
    int? workspaceId,
    int? projectId,
  }) async {
    final http.Response response;
    try {
      response = await ApiClient.post(
        '/cofounder/chat',
        body: {
          'message': message,
          'workspace_id': workspaceId,
          'project_id': projectId,
        },
      );
    } catch (e) {
      debugPrint('[CoFounderApiService] chatWithCoFounder network exception: $e');
      throw CoFounderChatException('Không thể kết nối tới COSA runtime: $e');
    }

    if (response.statusCode != 200) {
      debugPrint('[CoFounderApiService] chatWithCoFounder error status: ${response.statusCode}');
      throw CoFounderChatException(
        'COSA runtime phản hồi lỗi (HTTP ${response.statusCode}).',
      );
    }

    try {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      debugPrint('[CoFounderApiService] chatWithCoFounder decode exception: $e');
      throw CoFounderChatException('Không thể đọc phản hồi từ COSA runtime.');
    }
  }

  /// Lấy danh sách toàn bộ các 5 Core Domains và Optional Packs từ Backend
  static Future<List<WorkforcePackModel>> listWorkforcePacks({int? workspaceId}) async {
    try {
      final q = workspaceId != null ? '?workspace_id=$workspaceId' : '';
      final response = await ApiClient.get('/workforce/packs$q');
      if (response.statusCode == 200) {
        final List<dynamic> list = jsonDecode(response.body);
        return list.map((e) => WorkforcePackModel.fromJson(e as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('[CoFounderApiService] listWorkforcePacks exception: $e');
    }
    return [
      WorkforcePackModel(
        key: 'strategy',
        name: 'Strategic Co-Founder',
        roleTitle: 'AI Co-Founder & Strategy Lead',
        department: 'Executive',
        category: 'ORCHESTRATOR',
        isCore: true,
        isActive: true,
        description: 'Chiến lược, OKRs và 12-Week Year Execution Planning',
      ),
      WorkforcePackModel(
        key: 'sales',
        name: 'Sales & Revenue',
        roleTitle: 'Revenue Specialist',
        department: 'Commercial',
        category: 'DOMAIN',
        isCore: true,
        isActive: true,
        description: 'Quản lý Pipeline, Leads và Opportunities',
      ),
      WorkforcePackModel(
        key: 'marketing',
        name: 'Growth Marketing',
        roleTitle: 'Campaign Strategist',
        department: 'Commercial',
        category: 'DOMAIN',
        isCore: true,
        isActive: true,
        description: 'Chiến dịch, Content và Phễu chuyển đổi khách hàng',
      ),
      WorkforcePackModel(
        key: 'operations',
        name: 'Operations & Execution',
        roleTitle: 'Chief of Staff',
        department: 'Operations',
        category: 'DOMAIN',
        isCore: true,
        isActive: true,
        description: 'Kanban, Task Dependencies và Execution Score',
      ),
      WorkforcePackModel(
        key: 'finance_legal',
        name: 'Finance & Legal',
        roleTitle: 'Finance & Compliance Lead',
        department: 'Finance-Legal',
        category: 'DOMAIN',
        isCore: true,
        isActive: true,
        description: 'Kế toán TT58, Dòng tiền và Pháp lý doanh nghiệp',
      ),
    ];
  }

  /// Bật/Tắt một Optional Pack
  static Future<bool> toggleOptionalPack({
    required String packKey,
    required bool isActive,
    int? workspaceId,
  }) async {
    try {
      final response = await ApiClient.post(
        '/workforce/packs/$packKey/toggle',
        body: {
          'is_active': isActive,
          'workspace_id': workspaceId,
        },
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('[CoFounderApiService] toggleOptionalPack error: $e');
      return false;
    }
  }
}
