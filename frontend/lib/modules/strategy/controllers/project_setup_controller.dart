import 'package:get/get.dart';

import '../../../core/routing/app_routes.dart';
import '../../../core/routing/module_routes.dart';
import '../../../core/session/session_controller.dart';
import '../../../data/models/project_operating_setup_model.dart';
import '../../hologram_hub/controllers/founder_command_center_controller.dart';
import '../services/strategy_service.dart';

/// Hai pha của luồng thiết lập project: nhập tên/mô tả rồi tới kickoff 3 bước.
enum ProjectSetupPhase { form, kickoff }

/// Điều phối route `/projects/new`. Mode-aware: onboarding (`projectCount == 0`)
/// không cho Huỷ; project thứ N có Huỷ. Kickoff tái dùng `ProjectKickoffView`.
class ProjectSetupController extends GetxController {
  final Rx<ProjectSetupPhase> phase = ProjectSetupPhase.form.obs;
  final RxnString createdProjectId = RxnString();
  final RxBool isSubmitting = false.obs;
  final RxnString formError = RxnString();

  /// FIX 4 (final review) — worker chờ FCC tải xong khi controller được tạo
  /// trong lúc `loadDashboardData()` còn chạy (cold entry). Dispose ở `onClose`.
  Worker? _resumeWorker;

  /// FCC do shell sở hữu (`permanent: true`). Nhưng khi guard redirect từ
  /// `/hub` bằng `offAllNamed`, FCC non-permanent của `DashboardBinding` có
  /// thể bị dispose ngay sau khi `/projects/new` đã mount — để controller này
  /// mất chỗ dựa. Tự tạo lại (permanent) nếu thiếu thay vì để `Get.find` ném.
  FounderCommandCenterController get _fcc {
    if (!Get.isRegistered<FounderCommandCenterController>()) {
      Get.put<FounderCommandCenterController>(
        FounderCommandCenterController(),
        permanent: true,
      );
    }
    return Get.find<FounderCommandCenterController>();
  }

  bool get isOnboarding => _fcc.projectsList.isEmpty;

  @override
  void onInit() {
    super.onInit();
    if (_fcc.projectsLoadedOnce.value) {
      _decidePhaseFromLoadedState();
    } else {
      // FIX 4 (final review) — cold entry (browser refresh, bookmark, hoặc
      // luồng post-activate của FIX 1): `_fcc.loadDashboardData()` còn đang
      // chạy nên `projectsList` chưa phản ánh state thật. Nếu quyết định pha
      // ngay, Founder thấy form tạo và có thể tạo project thứ 2 trùng
      // (→ `needsProjectSetup` false vĩnh viễn, guard bị vô hiệu). Hoãn quyết
      // định tới khi FCC tải xong.
      // KHÔNG dispose worker ngay trong callback: GetX hoãn việc gỡ
      // subscription bằng `Timer(Duration.zero)` khi đang ở giữa chu kỳ
      // notify, để lại pending timer. `_decidePhaseFromLoadedState()` đã
      // guard idempotent nên cứ để worker sống tới `onClose`.
      _resumeWorker = ever<bool>(_fcc.projectsLoadedOnce, (loaded) {
        // Guard: một continuation async của FCU có thể set cờ sau khi
        // controller đã bị huỷ (test/hot-restart) — bỏ qua nếu FCC không còn.
        if (loaded == true &&
            Get.isRegistered<FounderCommandCenterController>()) {
          _decidePhaseFromLoadedState();
        }
      });
    }
  }

  /// Resume: đúng 1 project và setup của nó chưa ACTIVE -> vào thẳng kickoff.
  /// Chỉ áp dụng khi vẫn ở pha `form` và chưa có `createdProjectId` — không ghi
  /// đè form Founder đang nhập dở hay project vừa tạo qua `submitForm`.
  void _decidePhaseFromLoadedState() {
    if (phase.value != ProjectSetupPhase.form) return;
    if ((createdProjectId.value ?? '').isNotEmpty) return;
    if (_fcc.projectsList.length == 1 &&
        _fcc.activeProjectSetup.value?.status != OperatingSetupStatus.active) {
      final id = _fcc.projectsList.first['id']?.toString();
      if (id != null && id.isNotEmpty) {
        createdProjectId.value = id;
        phase.value = ProjectSetupPhase.kickoff;
      }
    }
  }

  @override
  void onClose() {
    _resumeWorker?.dispose();
    super.onClose();
  }

  Future<void> submitForm({required String title, String? description}) async {
    final trimmed = title.trim();
    if (trimmed.isEmpty) {
      formError.value = 'Vui lòng nhập tên dự án';
      return;
    }
    formError.value = null;
    isSubmitting.value = true;
    try {
      final project = await StrategyService()
          .createBasicProject(title: trimmed, description: description?.trim());
      final id = project['id']?.toString();
      if (id == null || id.isEmpty) {
        formError.value = 'Tạo dự án thất bại. Vui lòng thử lại.';
        return;
      }
      createdProjectId.value = id;
      await _fcc.loadDashboardData();
      phase.value = ProjectSetupPhase.kickoff;
    } catch (e) {
      formError.value = 'Đã có lỗi xảy ra: $e';
    } finally {
      isSubmitting.value = false;
    }
  }

  Future<void> onKickoffActivated(String projectId) async {
    // FIX 1 (final review) — guard /hub đọc `activeProjectSetup` của FCC; phải
    // refresh trước khi rời màn, nếu không middleware thấy setup CŨ (chưa
    // ACTIVE) và đẩy ngược lại đây (bounce loop vô hạn). `loadDashboardData()`
    // chạy khi currentRoute vẫn là `/projects/new` nên backstop của nó no-op.
    await _fcc.loadDashboardData();
    Get.offAllNamed(AppRoutes.hub);
  }

  void onKickoffBack() {
    if (isOnboarding) return;
    Get.offAllNamed(AppRoutes.hub);
  }

  void onOpenAdvancedRoadmap() => Get.toNamed(WorkspaceModule.strategy.path);

  void cancel() => Get.offAllNamed(AppRoutes.hub);

  /// FIX 2 (final review) — lối thoát bắt buộc trong onboarding: nếu
  /// `createBasicProject` liên tục lỗi và mọi route guard bounce về đây,
  /// Founder vẫn phải đăng xuất được. Tái dùng teardown phiên chuẩn của
  /// `SessionController` (Task 4: stop realtime → clear runtime → xoá token →
  /// route `/login`) — không dựng cơ chế đăng xuất riêng cho màn này.
  void logout() => Get.find<SessionController>().logout();

  /// FIX 2 (final review) — đổi workspace là lối thoát thứ hai khi bị kẹt ở
  /// onboarding của workspace hiện tại.
  void switchWorkspace() => Get.offAllNamed(AppRoutes.workspacePicker);
}
