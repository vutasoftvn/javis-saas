import 'package:get/get.dart';
import '../../auth/services/auth_service.dart';
import '../../../core/routing/app_routes.dart';
import '../../../core/session/session_controller.dart';

class WorkspacePickerController extends GetxController {
  // `sessionController` cho phép test tiêm fake implementation
  // (Completer-based) để kiểm chứng vòng đời isLoading mà không cần gọi
  // network thật. KHÔNG resolve `Get.find<SessionController>()` ngay trong
  // constructor — các test dựng controller với platformToken rỗng (early
  // return trước khi chạm SessionController) không cần SessionController
  // được đăng ký trước.
  WorkspacePickerController({SessionController? sessionController})
      : _injectedSessionController = sessionController;

  final SessionController? _injectedSessionController;
  SessionController get _sessionController =>
      _injectedSessionController ?? Get.find<SessionController>();

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

  /// Task 4 — switch workspace đi qua `SessionController.activateWorkspace`
  /// (verify identity + session-context trước khi commit) thay vì gọi
  /// `AuthService.finishAuthenticationForWorkspace` trực tiếp rồi tự quyết
  /// định điều hướng — tránh trùng lặp logic transaction giữa picker và
  /// login flow (`AuthController.login`).
  Future<void> selectWorkspace(String workspaceId) async {
    if (platformToken.isEmpty) {
      errorMessage.value = 'Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.';
      return;
    }

    isLoading.value = true;
    errorMessage.value = '';
    selectingWorkspaceId.value = workspaceId;

    final result = await _sessionController.activateWorkspace(workspaceId);

    isLoading.value = false;
    selectingWorkspaceId.value = null;

    if (result.isSuccess) {
      Get.offAllNamed(AppRoutes.hub);
    } else {
      errorMessage.value = result.failureMessage ??
          'Đồng bộ dữ liệu workspace thất bại. Vui lòng thử lại.';
    }
  }
}
