import '../services/secure_storage_service.dart';
import 'api_result.dart';

abstract interface class ApiAuthResolver {
  Future<String?> tokenFor(ApiPlane plane);
  Future<String?> workspaceId();
}

class DefaultApiAuthResolver implements ApiAuthResolver {
  const DefaultApiAuthResolver();

  @override
  Future<String?> tokenFor(ApiPlane plane) async {
    switch (plane) {
      case ApiPlane.platform:
        final primary = await SecureStorageService.read('platform_access_token');
        if (primary != null && primary.isNotEmpty) return primary;
        final legacy = await SecureStorageService.read('auth_token');
        return (legacy != null && legacy.isNotEmpty) ? legacy : null;
      case ApiPlane.company:
        final primary = await SecureStorageService.read('local_session_token');
        if (primary != null && primary.isNotEmpty) return primary;
        final legacy = await SecureStorageService.read('auth_token');
        return (legacy != null && legacy.isNotEmpty) ? legacy : null;
      case ApiPlane.agent:
        final primary = await SecureStorageService.read('local_session_token');
        if (primary != null && primary.isNotEmpty) return primary;
        final legacy = await SecureStorageService.read('auth_token');
        return (legacy != null && legacy.isNotEmpty) ? legacy : null;
      case ApiPlane.localWorker:
        final primary = await SecureStorageService.read('local_session_token');
        if (primary != null && primary.isNotEmpty) return primary;
        final legacy = await SecureStorageService.read('auth_token');
        return (legacy != null && legacy.isNotEmpty) ? legacy : null;
    }
  }

  @override
  Future<String?> workspaceId() async {
    return SecureStorageService.read('workspace_id');
  }
}
