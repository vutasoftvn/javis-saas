import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';

/// Nền thẻ dùng chung cho toàn bộ Marketing Cockpit (khớp sidebar/floating app bar).
const Color kMarketingCardColor = Color(0xFF141C2E);

/// Thẻ nội dung tiêu chuẩn của cockpit.
class MarketingCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? borderColor;

  const MarketingCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.borderColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: kMarketingCardColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: borderColor ?? Colors.white.withValues(alpha: 0.05)),
      ),
      child: child,
    );
  }
}

/// Tiêu đề mục kèm mô tả và nút hành động bên phải.
class MarketingSectionHeader extends StatelessWidget {
  final String title;
  final String? description;
  final Widget? action;

  const MarketingSectionHeader({
    super.key,
    required this.title,
    this.description,
    this.action,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              if (description != null) ...[
                const SizedBox(height: 4),
                Text(
                  description!,
                  style: const TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark, height: 1.4),
                ),
              ],
            ],
          ),
        ),
        if (action != null) ...[const SizedBox(width: 12), action!],
      ],
    );
  }
}

/// Nhãn trạng thái nhỏ.
class MarketingChip extends StatelessWidget {
  final String label;
  final Color color;
  final IconData? icon;

  const MarketingChip({super.key, required this.label, required this.color, this.icon});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(7),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[Icon(icon, size: 12, color: color), const SizedBox(width: 4)],
          Text(
            label,
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: color),
          ),
        ],
      ),
    );
  }
}

/// Trạng thái rỗng của một tab, kèm nút hành động chính.
class MarketingEmpty extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Widget? action;

  const MarketingEmpty({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    this.action,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 46, color: Colors.white.withValues(alpha: 0.18)),
            const SizedBox(height: 14),
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Colors.white),
            ),
            const SizedBox(height: 6),
            SizedBox(
              width: 420,
              child: Text(
                subtitle,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 12.5, color: AppTheme.textMutedDark, height: 1.5),
              ),
            ),
            if (action != null) ...[const SizedBox(height: 18), action!],
          ],
        ),
      ),
    );
  }
}

/// Cặp nhãn - giá trị dùng trong các thẻ chi tiết.
class MarketingKeyValue extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;

  const MarketingKeyValue({super.key, required this.label, required this.value, this.valueColor});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.primaryLight),
          ),
          const SizedBox(height: 3),
          Text(
            value,
            style: TextStyle(fontSize: 13, color: valueColor ?? Colors.white70, height: 1.45),
          ),
        ],
      ),
    );
  }
}

/// Thanh tiến độ theo phần trăm (0-100).
class MarketingProgressBar extends StatelessWidget {
  final double percent;
  final Color color;

  const MarketingProgressBar({super.key, required this.percent, this.color = AppTheme.primary});

  @override
  Widget build(BuildContext context) {
    final clamped = percent.clamp(0, 100) / 100;
    return ClipRRect(
      borderRadius: BorderRadius.circular(6),
      child: LinearProgressIndicator(
        value: clamped.toDouble(),
        minHeight: 7,
        backgroundColor: Colors.white.withValues(alpha: 0.07),
        valueColor: AlwaysStoppedAnimation<Color>(color),
      ),
    );
  }
}

/// Bảng màu và nhãn tiếng Việt cho các trạng thái nghiệp vụ.
class MarketingLabels {
  static const Map<String, String> campaignStatus = {
    'draft': 'Nháp',
    'pending_approval': 'Chờ phê duyệt',
    'active': 'Đang chạy',
    'paused': 'Tạm dừng',
    'completed': 'Đã kết thúc',
  };

  static const Map<String, String> experimentStatus = {
    'draft': 'Nháp',
    'running': 'Đang chạy',
    'win': 'Thắng',
    'lose': 'Thua',
    'inconclusive': 'Chưa kết luận',
    'iterate': 'Cần lặp lại',
  };

  static const Map<String, String> assetStatus = {
    'draft': 'Nháp',
    'pending_approval': 'Chờ phê duyệt',
    'approved': 'Đã duyệt',
    'rejected': 'Bị từ chối',
  };

  static const Map<String, String> confidence = {
    'high': 'Cao',
    'medium': 'Trung bình',
    'low': 'Thấp',
  };

  static const Map<String, String> metricCategory = {
    'acquisition': 'Thu hút',
    'conversion': 'Chuyển đổi',
    'revenue': 'Doanh thu',
    'retention': 'Giữ chân',
    'content': 'Nội dung',
  };

  static const Map<String, String> assetType = {
    'copy': 'Nội dung bán hàng',
    'email': 'Email',
    'landing_page': 'Trang đích',
    'ad_creative': 'Mẫu quảng cáo',
    'social_post': 'Bài mạng xã hội',
  };

  static String campaign(String? key) => campaignStatus[key] ?? key ?? '—';

  static String experiment(String? key) => experimentStatus[key] ?? key ?? '—';

  static String asset(String? key) => assetStatus[key] ?? key ?? '—';

  static Color campaignColor(String? key) {
    switch (key) {
      case 'active':
        return AppTheme.success;
      case 'pending_approval':
        return Colors.amberAccent;
      case 'paused':
        return Colors.orangeAccent;
      case 'completed':
        return AppTheme.textMutedDark;
      default:
        return AppTheme.primaryLight;
    }
  }

  static Color experimentColor(String? key) {
    switch (key) {
      case 'win':
        return AppTheme.success;
      case 'lose':
        return AppTheme.accent;
      case 'iterate':
        return Colors.amberAccent;
      case 'running':
        return AppTheme.primaryLight;
      default:
        return AppTheme.textMutedDark;
    }
  }

  static Color assetColor(String? key) {
    switch (key) {
      case 'approved':
        return AppTheme.success;
      case 'rejected':
        return AppTheme.accent;
      case 'pending_approval':
        return Colors.amberAccent;
      default:
        return AppTheme.textMutedDark;
    }
  }
}

/// Định dạng số cho UI tiếng Việt (phân tách hàng nghìn bằng dấu chấm).
String formatNumber(dynamic value, {int decimals = 0}) {
  final number = (value is num) ? value.toDouble() : double.tryParse('${value ?? ''}') ?? 0.0;
  final fixed = number.toStringAsFixed(decimals);
  final parts = fixed.split('.');
  final intPart = parts[0].replaceAllMapped(
    RegExp(r'(\d)(?=(\d{3})+$)'),
    (m) => '${m[1]}.',
  );
  return parts.length > 1 ? '$intPart,${parts[1]}' : intPart;
}

String formatPercent(dynamic value) => '${formatNumber(value, decimals: 1)}%';

String formatDate(String? iso) {
  if (iso == null || iso.isEmpty) return '—';
  final parsed = DateTime.tryParse(iso);
  if (parsed == null) return '—';
  final local = parsed.toLocal();
  String two(int n) => n.toString().padLeft(2, '0');
  return '${two(local.day)}/${two(local.month)}/${local.year}';
}
