import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/workspace_picker_controller.dart';
import '../../auth/services/auth_service.dart';
import '../../../core/theme/app_theme.dart';

/// M5 §6 — chip hiển thị runtime_mode + presence + last heartbeat của workspace
/// trên picker (chỉ khi platform trả kèm dữ liệu).
class _RuntimeChip extends StatelessWidget {
  final WorkspaceSummary workspace;
  const _RuntimeChip({required this.workspace});

  @override
  Widget build(BuildContext context) {
    final presence = workspace.presenceStatus;
    final mode = workspace.runtimeMode;
    final Color dot = presence == 'ONLINE'
        ? const Color(0xFF3FB950)
        : presence == 'DEGRADED'
            ? const Color(0xFFD29922)
            : presence == 'OFFLINE'
                ? const Color(0xFFF85149)
                : AppTheme.textMutedDark;

    final parts = <String>[
      if (mode != null) _modeLabel(mode),
      if (presence != null) _presenceLabel(presence),
    ];
    final hb = workspace.lastHeartbeatAt;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: 8, height: 8, decoration: BoxDecoration(color: dot, shape: BoxShape.circle)),
        const SizedBox(width: 6),
        Flexible(
          child: Text(
            hb != null ? '${parts.join(' · ')} · ${_ago(hb)}' : parts.join(' · '),
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 11),
          ),
        ),
      ],
    );
  }

  static String _modeLabel(String m) {
    switch (m) {
      case 'LOCAL_ONLY':
        return 'Local';
      case 'REMOTE_ACCESS':
        return 'Remote';
      case 'CLOUD_CONTINUITY':
        return 'Cloud';
      default:
        return m;
    }
  }

  static String _presenceLabel(String p) {
    switch (p) {
      case 'ONLINE':
        return 'trực tuyến';
      case 'DEGRADED':
        return 'chập chờn';
      case 'OFFLINE':
        return 'offline';
      default:
        return p.toLowerCase();
    }
  }

  static String _ago(DateTime utc) {
    final diff = DateTime.now().toUtc().difference(utc);
    if (diff.inSeconds < 60) return 'vừa xong';
    if (diff.inMinutes < 60) return '${diff.inMinutes} phút trước';
    if (diff.inHours < 24) return '${diff.inHours} giờ trước';
    return '${diff.inDays} ngày trước';
  }
}

class WorkspacePickerView extends GetView<WorkspacePickerController> {
  const WorkspacePickerView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundDark,
      body: Container(
        decoration: const BoxDecoration(gradient: AppTheme.backgroundRadialGradient),
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Center(
                    child: Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppTheme.primary.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.4)),
                      ),
                      child: const Icon(Icons.workspaces_outlined, size: 40, color: AppTheme.primary),
                    ),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Chọn workspace',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: Colors.white),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Tài khoản của bạn thuộc nhiều workspace - chọn workspace muốn làm việc trên máy này',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 13, color: AppTheme.textMutedDark),
                  ),
                  const SizedBox(height: 24),

                  Obx(() => controller.errorMessage.value.isNotEmpty
                      ? Container(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                          margin: const EdgeInsets.only(bottom: 16),
                          decoration: BoxDecoration(
                            color: AppTheme.accent.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppTheme.accent.withValues(alpha: 0.6)),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.error_outline, size: 20, color: AppTheme.accent),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  controller.errorMessage.value,
                                  style: const TextStyle(color: AppTheme.accentLight, fontSize: 13),
                                ),
                              ),
                            ],
                          ),
                        )
                      : const SizedBox.shrink()),

                  ...controller.workspaces.map((w) => _WorkspaceTile(workspace: w)),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _WorkspaceTile extends StatelessWidget {
  final WorkspaceSummary workspace;

  const _WorkspaceTile({required this.workspace});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<WorkspacePickerController>();
    return Obx(() {
      final isSelecting = controller.selectingWorkspaceId.value == workspace.workspaceId;
      final isDisabled = controller.isLoading.value;

      return Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Material(
          color: AppTheme.surfaceDark.withValues(alpha: 0.85),
          borderRadius: BorderRadius.circular(12),
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: isDisabled ? null : () => controller.selectWorkspace(workspace.workspaceId),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.borderDark),
              ),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: AppTheme.primary.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.workspaces, color: AppTheme.primary, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          workspace.name ?? 'Workspace',
                          style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          workspace.roleId,
                          style: const TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
                        ),
                        if (workspace.runtimeMode != null ||
                            workspace.presenceStatus != null) ...[
                          const SizedBox(height: 4),
                          _RuntimeChip(workspace: workspace),
                        ],
                      ],
                    ),
                  ),
                  if (isSelecting)
                    const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.primary),
                    )
                  else
                    const Icon(Icons.chevron_right, color: AppTheme.textMutedDark),
                ],
              ),
            ),
          ),
        ),
      );
    });
  }
}
