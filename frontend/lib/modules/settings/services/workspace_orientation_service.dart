import 'dart:convert';

import '../../../core/network/api_client.dart';
import '../models/workspace_orientation.dart';

class WorkspaceOrientationException implements Exception {
  WorkspaceOrientationException(this.message);
  final String message;

  @override
  String toString() => message;
}

class WorkspaceOrientationService {
  Future<WorkspaceOrientation> fetch(String workspaceId) async {
    final res = await ApiClient.get('/identity/workspaces/$workspaceId');
    if (res.statusCode != 200) {
      throw WorkspaceOrientationException(
        'Không tải được thông tin workspace (HTTP ${res.statusCode}).',
      );
    }
    return WorkspaceOrientation.fromJson(
      jsonDecode(res.body) as Map<String, dynamic>,
    );
  }

  Future<WorkspaceOrientation> update(
    String workspaceId, {
    required String? vision,
    required String? mission,
    required String? coreValues,
  }) async {
    final res = await ApiClient.patch(
      '/identity/workspaces/$workspaceId/company-identity',
      body: {
        'vision': vision?.trim().isEmpty ?? true ? null : vision?.trim(),
        'mission': mission?.trim().isEmpty ?? true ? null : mission?.trim(),
        'coreValues': coreValues?.trim().isEmpty ?? true ? null : coreValues?.trim(),
      },
    );
    if (res.statusCode != 200) {
      throw WorkspaceOrientationException(
        'Không lưu được định hướng workspace (HTTP ${res.statusCode}).',
      );
    }
    return WorkspaceOrientation.fromJson(
      jsonDecode(res.body) as Map<String, dynamic>,
    );
  }
}
