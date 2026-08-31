import 'dart:convert';

import '../../../core/network/api_client.dart';
import '../../../data/models/workspace_company_identity_model.dart';

class CompanyIdentityException implements Exception {
  CompanyIdentityException(this.message);
  final String message;

  @override
  String toString() => message;
}

/// Đọc/ghi Vision/Mission/Core Values cấp workspace
/// (`services/company/identity` — `GET`/`PATCH /identity/workspaces/:id`).
class CompanyIdentityService {
  Future<WorkspaceCompanyIdentity> fetch(String workspaceId) async {
    final res = await ApiClient.get('/identity/workspaces/$workspaceId');
    if (res.statusCode != 200) {
      throw CompanyIdentityException(
        'Không tải được thông tin workspace (HTTP ${res.statusCode}).',
      );
    }
    return WorkspaceCompanyIdentity.fromJson(
      jsonDecode(res.body) as Map<String, dynamic>,
    );
  }

  Future<WorkspaceCompanyIdentity> save(
    String workspaceId, {
    required String vision,
    required String mission,
    required String coreValues,
  }) async {
    final res = await ApiClient.patch(
      '/identity/workspaces/$workspaceId/company-identity',
      body: {
        'vision': vision,
        'mission': mission,
        'coreValues': coreValues,
      },
    );
    if (res.statusCode != 200) {
      throw CompanyIdentityException(
        'Không lưu được Vision/Mission/Values (HTTP ${res.statusCode}).',
      );
    }
    return WorkspaceCompanyIdentity.fromJson(
      jsonDecode(res.body) as Map<String, dynamic>,
    );
  }
}
