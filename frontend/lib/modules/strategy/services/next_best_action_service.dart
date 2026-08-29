import '../../../core/network/workspace_scoped_service.dart';


class NextBestActionService extends WorkspaceService {
  Future<Map<String, dynamic>?> getActionContext() async {
    final data = await getJson('/operations/strategy/action-context');
    return data is Map && data['context'] is Map
        ? Map<String, dynamic>.from(data['context'] as Map)
        : null;
  }

  Future<List<dynamic>> getActionProposals({String? status}) async {
    final path = status != null
        ? '/operations/strategy/action-proposals?status=$status'
        : '/operations/strategy/action-proposals';
    final data = await getJson(path);
    return data is Map && data['proposals'] is List
        ? data['proposals'] as List<dynamic>
        : const [];
  }

  Future<Map<String, dynamic>?> createActionProposal(Map<String, dynamic> payload) async {
    final data = await postJson('/operations/strategy/action-proposals', payload);
    return data is Map ? Map<String, dynamic>.from(data) : null;
  }

  Future<Map<String, dynamic>?> acceptActionProposal(String proposalId) async {
    final data = await postJson('/operations/strategy/action-proposals/$proposalId/accept', {});
    return data is Map ? Map<String, dynamic>.from(data) : null;
  }

  Future<List<dynamic>> getWeeklyReviews() async {
    final data = await getJson('/operations/strategy/weekly-reviews');
    return data is Map && data['reviews'] is List
        ? data['reviews'] as List<dynamic>
        : const [];
  }

  Future<Map<String, dynamic>?> createWeeklyReview(Map<String, dynamic> payload) async {
    final data = await postJson('/operations/strategy/weekly-reviews', payload);
    return data is Map ? Map<String, dynamic>.from(data) : null;
  }

  Future<Map<String, dynamic>?> completeWeeklyReview(String reviewId) async {
    final data = await postJson('/operations/strategy/weekly-reviews/$reviewId/complete', {});
    return data is Map ? Map<String, dynamic>.from(data) : null;
  }
}
