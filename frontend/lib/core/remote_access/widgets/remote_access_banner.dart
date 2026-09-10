import 'package:flutter/material.dart';
import '../models/runtime_status.dart';

/// M5 §5 — banner cảnh báo runtime: OFFLINE (đỏ, chỉ đọc + as_of) / DEGRADED
/// (hổ phách). Ẩn hoàn toàn khi LOCAL_ONLY hoặc node ONLINE bình thường.
class RemoteAccessBanner extends StatelessWidget {
  final RuntimeStatus? status;

  const RemoteAccessBanner({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    final s = status;
    if (s == null || !s.needsBanner) return const SizedBox.shrink();

    final scheme = Theme.of(context).colorScheme;
    final bool severe = s.isOffline;
    final Color bg = severe ? scheme.errorContainer : const Color(0xFFFFF3CD);
    final Color fg = severe ? scheme.onErrorContainer : const Color(0xFF664D03);
    final IconData icon =
        severe ? Icons.cloud_off_rounded : Icons.sync_problem_rounded;

    return Semantics(
      liveRegion: true,
      label: severe ? 'Runtime node offline' : 'Runtime node degraded',
      child: Container(
        width: double.infinity,
        color: bg,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        child: Row(
          children: [
            Icon(icon, size: 18, color: fg),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    s.presenceLabel,
                    style: TextStyle(color: fg, fontWeight: FontWeight.w600, fontSize: 13),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    s.bannerMessage,
                    style: TextStyle(color: fg, fontSize: 12),
                  ),
                  if (s.stalenessLabel != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      s.stalenessLabel!,
                      style: TextStyle(
                        color: fg,
                        fontSize: 11,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
