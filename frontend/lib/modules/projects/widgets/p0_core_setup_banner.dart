import 'package:flutter/material.dart';

import '../../../core/network/api_result.dart';
import '../../hologram_hub/services/executive_advisory_board_service.dart';

/// Response tạo Project (Company) báo P0 Core chưa hội tụ: Project đã tồn tại
/// nhưng bốn vai trò P0 Core chưa được khởi tạo (plan 2026-09-25 Task 7).
bool isP0CoreBootstrapIncomplete(Map<String, dynamic> project) {
  final bootstrap = project['p0CoreBootstrap'];
  return bootstrap is Map && bootstrap['status'] == 'INCOMPLETE';
}

/// Banner "Hoàn tất thiết lập P0 Core" sau khi tạo Project mà bootstrap lỗi.
/// Gọi đúng action sửa sẵn có của Executive Board (server idempotent, tự quyết
/// định Project còn đủ điều kiện hay không). Chỉ ẩn khi server xác nhận thành công.
class P0CoreSetupBanner extends StatefulWidget {
  const P0CoreSetupBanner({super.key, required this.projectId, this.service, this.isEnglish = false});

  final String projectId;
  final ExecutiveAdvisoryBoardService? service;
  final bool isEnglish;

  @override
  State<P0CoreSetupBanner> createState() => _P0CoreSetupBannerState();
}

class _P0CoreSetupBannerState extends State<P0CoreSetupBanner> {
  late final ExecutiveAdvisoryBoardService _service = widget.service ?? ExecutiveAdvisoryBoardService();
  bool _busy = false;
  bool _done = false;
  String? _error;

  Future<void> _complete() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    final result = await _service.bootstrapP0Core(projectId: widget.projectId);
    if (!mounted) return;
    setState(() {
      _busy = false;
      switch (result) {
        case ApiSuccess(:final data) when data:
          _done = true;
        case ApiSuccess():
          _error = widget.isEnglish ? 'P0 Core setup was not confirmed.' : 'Chưa xác nhận được thiết lập P0 Core.';
        case ApiFailure(:final failure):
          _error = failure.message;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_done) return const SizedBox.shrink();
    final isEn = widget.isEnglish;
    return Container(
      key: const Key('p0-core-setup-banner'),
      margin: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF3B2F12),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.amber.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.warning_amber_rounded, color: Colors.amber, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  isEn
                      ? 'The project was created, but the P0 Core advisors were not set up yet.'
                      : 'Project đã được tạo nhưng bộ cố vấn P0 Core chưa được thiết lập xong.',
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                ),
              ),
            ],
          ),
          if (_error != null) ...[
            const SizedBox(height: 6),
            Text(_error!, key: const Key('p0-core-setup-error'), style: const TextStyle(color: Colors.redAccent, fontSize: 12)),
          ],
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerRight,
            child: OutlinedButton.icon(
              key: const Key('p0-core-setup-action'),
              onPressed: _busy ? null : _complete,
              icon: _busy
                  ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.rocket_launch_outlined, size: 16),
              label: Text(isEn ? 'Finish P0 Core setup' : 'Hoàn tất thiết lập P0 Core'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.amber,
                side: const BorderSide(color: Colors.amber),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
