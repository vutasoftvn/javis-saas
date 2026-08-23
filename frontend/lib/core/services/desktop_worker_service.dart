import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../network/api_client.dart';

class DesktopWorkerHealth {
  final String status;
  final String plane;
  final String platform;
  final int? pid;
  final List<String> capabilities;

  const DesktopWorkerHealth({
    required this.status,
    required this.plane,
    required this.platform,
    this.pid,
    this.capabilities = const [],
  });

  factory DesktopWorkerHealth.fromJson(Map<String, dynamic> json) {
    return DesktopWorkerHealth(
      status: json['status']?.toString() ?? 'offline',
      plane: json['plane']?.toString() ?? 'local_worker',
      platform: json['platform']?.toString() ?? 'unknown',
      pid: json['pid'] is int ? json['pid'] as int : int.tryParse(json['pid']?.toString() ?? ''),
      capabilities: (json['capabilities'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
    );
  }
}

class DesktopWorkerTaskResult {
  final int exitCode;
  final String stdout;
  final String stderr;
  final String status;

  const DesktopWorkerTaskResult({
    required this.exitCode,
    required this.stdout,
    required this.stderr,
    required this.status,
  });

  bool get isSuccess => exitCode == 0 && status == 'completed';

  factory DesktopWorkerTaskResult.fromJson(Map<String, dynamic> json) {
    return DesktopWorkerTaskResult(
      exitCode: (json['exit_code'] as num?)?.toInt() ?? 1,
      stdout: json['stdout']?.toString() ?? '',
      stderr: json['stderr']?.toString() ?? '',
      status: json['status']?.toString() ?? 'failed',
    );
  }
}

class DesktopWorkerService {
  /// Kiểm tra trạng thái kết nối tới Local Desktop Worker (:8765)
  static Future<DesktopWorkerHealth?> checkHealth() async {
    try {
      final response = await ApiClient.get('/local-worker/health', requiresAuth: false);
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return DesktopWorkerHealth.fromJson(data);
      }
    } catch (e) {
      debugPrint('[DesktopWorkerService] checkHealth error: $e');
    }
    return null;
  }

  /// Thực thi tác vụ local loopback trên máy trạm (an toàn, chỉ chạy qua 127.0.0.1)
  static Future<DesktopWorkerTaskResult?> executeTask(
    String command, {
    String? cwd,
    Map<String, String>? env,
    int timeoutSeconds = 120,
  }) async {
    try {
      final response = await ApiClient.post(
        '/local-worker/execute-task',
        requiresAuth: false,
        body: {
          'command': command,
          'cwd': ?cwd,
          'env': ?env,
          'timeout_seconds': timeoutSeconds,
        },
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return DesktopWorkerTaskResult.fromJson(data);
      }
    } catch (e) {
      debugPrint('[DesktopWorkerService] executeTask error: $e');
    }
    return null;
  }
}
