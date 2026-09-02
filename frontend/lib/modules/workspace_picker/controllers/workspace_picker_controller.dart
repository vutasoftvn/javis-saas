import 'package:get/get.dart';
import '../../auth/services/auth_service.dart';
import '../../../core/routing/app_routes.dart';

class WorkspacePickerController extends GetxController {
  // `authService` cho phép test tiêm fake implementation (Completer-based)
  // để kiểm chứng vòng đời isLoading mà không cần gọi network thật.
  WorkspacePickerController({AuthService? authService})
      : _authService = authService ?? AuthService();

  final AuthService _authService;

  late final String platformToken;
  late final List<WorkspaceSummary> workspaces;

  final isLoading = false.obs;
  final errorMessage = ''.obs;
  final selectingWorkspaceId = Rxn<String>();

  @override
  void onInit() {
    super.onInit();
    final args = (Get.arguments as Map?) ?? const {};
    platformToken = args['platformToken'] as String? ?? '';
    workspaces = (args['workspaces'] as List<WorkspaceSummary>?) ?? const [];
  }

  Future<void> selectWorkspace(String workspaceId) async {
    if (platformToken.isEmpty) {
      errorMessage.value = 'Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.';
      return;
    }

    isLoading.value = true;
    errorMessage.value = '';
    selectingWorkspaceId.value = workspaceId;

    final ok = await _authService.finishAuthenticationForWorkspace(
      platformToken: platformToken,
      workspaceId: workspaceId,
    );

    isLoading.value = false;
    selectingWorkspaceId.value = null;

    if (ok) {
      Get.offAllNamed(AppRoutes.hub);
    } else {
      errorMessage.value = 'Đồng bộ dữ liệu workspace thất bại. Vui lòng thử lại.';
    }
  }
}
