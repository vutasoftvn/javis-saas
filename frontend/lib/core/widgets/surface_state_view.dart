import 'package:flutter/material.dart';

import '../services/workspace_capability_manifest_model.dart';

/// Hiển thị một surface theo `surfaceStatus` server-owned. Năm trạng thái phải
/// PHÂN BIỆT RÕ (spec §7.2):
///  - AVAILABLE: render [child] (module/action live).
///  - PILOT: render [child] + badge Pilot + [pilotNote].
///  - CONFIGURATION_REQUIRED: thông báo thiếu cấu hình + CTA [onConfigure].
///  - PLANNED: roadmap card (release note), KHÔNG có action.
///  - UNAVAILABLE: unavailable + [onRetry].
class SurfaceStateView extends StatelessWidget {
  const SurfaceStateView({
    super.key,
    required this.status,
    required this.child,
    this.surface,
    this.pilotNote,
    this.onConfigure,
    this.onRetry,
  });

  final SurfaceStatus status;
  final Widget child;
  final CapabilityManifestSurface? surface;
  final String? pilotNote;
  final VoidCallback? onConfigure;
  final VoidCallback? onRetry;

  String get _releaseNote => surface?.releaseNote ?? '';

  @override
  Widget build(BuildContext context) {
    switch (status) {
      case SurfaceStatus.available:
        return child;

      case SurfaceStatus.pilot:
        return Column(
          key: const Key('surface_state_pilot'),
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Chip(label: Text('Pilot')),
                const SizedBox(width: 8),
                if ((pilotNote ?? _releaseNote).isNotEmpty)
                  Expanded(child: Text(pilotNote ?? _releaseNote)),
              ],
            ),
            const SizedBox(height: 8),
            child,
          ],
        );

      case SurfaceStatus.configurationRequired:
        return _MessageCard(
          key: const Key('surface_state_configuration_required'),
          icon: Icons.settings_suggest_outlined,
          title: 'Cần cấu hình',
          body: _releaseNote.isNotEmpty
              ? _releaseNote
              : 'Tính năng này cần cấu hình thêm trước khi dùng.',
          actionLabel: onConfigure != null ? 'Thiết lập' : null,
          onAction: onConfigure,
        );

      case SurfaceStatus.planned:
        return _MessageCard(
          key: const Key('surface_state_planned'),
          icon: Icons.flag_outlined,
          title: 'Đã lên lộ trình',
          body: _releaseNote.isNotEmpty
              ? _releaseNote
              : 'Tính năng này sẽ có ở bản phát hành sau.',
          // PLANNED không có action thao tác được.
          actionLabel: null,
          onAction: null,
        );

      case SurfaceStatus.unavailable:
        return _MessageCard(
          key: const Key('surface_state_unavailable'),
          icon: Icons.cloud_off_outlined,
          title: 'Không khả dụng',
          body: 'Không tải được trạng thái tính năng. Thử lại hoặc liên hệ hỗ trợ.',
          actionLabel: onRetry != null ? 'Thử lại' : null,
          onAction: onRetry,
        );
    }
  }
}

class _MessageCard extends StatelessWidget {
  const _MessageCard({
    super.key,
    required this.icon,
    required this.title,
    required this.body,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final String title;
  final String body;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 20),
                const SizedBox(width: 8),
                Text(title, style: theme.textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 8),
            Text(body, style: theme.textTheme.bodyMedium),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.tonal(
                  onPressed: onAction,
                  child: Text(actionLabel!),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
