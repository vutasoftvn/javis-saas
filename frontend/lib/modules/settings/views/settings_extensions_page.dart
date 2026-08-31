import 'package:flutter/material.dart';

/// Trang cài đặt Extensions: transport workspace-extensions cũ (không xác thực,
/// không có contract Company/Control-Plane đã duyệt) đã bị gỡ hoàn toàn
/// (Task 10, AgentOS auth-contract-frontend-parity plan). Trang này chỉ
/// hiển thị thông báo "chưa khả dụng", không gọi mạng, không có state loading
/// hay toggle — khi có API chính thức mới khôi phục luồng dữ liệu thật.
class SettingsExtensionsPage extends StatelessWidget {
  const SettingsExtensionsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Extensions Settings')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Card(
            elevation: 2,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.extension_off_outlined, size: 48, color: Theme.of(context).colorScheme.outline),
                  const SizedBox(height: 16),
                  Text(
                    'Tiện ích mở rộng (Extensions)',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Tính năng tiện ích mở rộng hiện chưa khả dụng trong phiên bản này. Các công cụ và kỹ năng hiện được điều phối trực tiếp qua COSA Capabilities; trang này sẽ hoạt động trở lại khi có API Extensions chính thức từ Company/Control Plane.',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
