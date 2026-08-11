import 'dart:async';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../data/services/connectors_service.dart';

class ConnectionsController extends GetxController {
  final ConnectorsService _connectorsService = ConnectorsService();

  final isLoading = false.obs;
  final connectors = <Map<String, dynamic>>[].obs;
  final selectedCategory = 'Tất cả'.obs;

  // Catalog Categories matching screenshot
  final categories = [
    'Tất cả',
    'Kho ứng dụng',
    'Bán hàng',
    'Nhắn tin',
    'Marketing',
    'Văn phòng',
    'Quảng cáo',
    'Mạng xã hội',
    'Sáng tạo'
  ];

  // Catalog items
  final catalogItems = [
    {
      'id': 'zalo_mcp',
      'name': 'Zalo Agent MCP',
      'category': 'Nhắn tin',
      'auth_badge': 'QUÉT QR',
      'is_beta': true,
      'description':
          'MCP chuẩn của zalo-agent-cli: đọc tin mới/lịch sử, tìm cuộc chat, xem media và gửi tin bằng tài khoản Zalo cá nhân.',
      'type': 'qr',
    },
    {
      'id': 'google_workspace',
      'name': 'Google Workspace (Gmail & Docs)',
      'category': 'Văn phòng',
      'auth_badge': 'OAUTH 2.0',
      'is_beta': true,
      'description':
          'Đọc/tìm kiếm email Gmail, tóm tắt hòm thư, tự động soạn & gửi email, xem lịch và làm việc với Google Docs qua MCP.',
      'type': 'oauth',
    },
    {
      'id': 'botcake',
      'name': 'Botcake',
      'category': 'Nhắn tin',
      'auth_badge': 'DÁN KEY',
      'is_beta': true,
      'description':
          'Khách hàng, tag, flow và gửi tin từ chatbot Botcake (qua Public API - Javis tự dựng cầu nối, không cần cài gì thêm).',
      'type': 'key',
    },
    {
      'id': 'slack',
      'name': 'Slack',
      'category': 'Nhắn tin',
      'auth_badge': 'ĐĂNG NHẬP TÀI KHOẢN',
      'is_beta': true,
      'description':
          'Tìm kiếm và đọc/gửi tin nhắn Slack, xem kênh và thành viên, quản lý canvas qua MCP chính chủ của Slack.',
      'type': 'oauth',
    },
  ];

  // Zalo QR state
  final isQrStarting = false.obs;
  final qrDataUrl = ''.obs;
  final qrState = 'starting'.obs;
  final qrError = ''.obs;
  String? currentSid;
  Timer? _qrTimer;

  @override
  void onInit() {
    super.onInit();
    loadConnectors();
    loadGoogleStatus();
  }

  @override
  void onClose() {
    stopQrPolling();
    _googlePollTimer?.cancel();
    super.onClose();
  }

  Future<void> loadConnectors() async {
    isLoading.value = true;
    try {
      final data = await _connectorsService.getConnectors();
      connectors.value = data.cast<Map<String, dynamic>>();
    } catch (e) {
      Get.snackbar('Lỗi', 'Không nạp được danh sách kết nối: $e');
    } finally {
      isLoading.value = false;
    }
  }

  bool isCatalogItemConnected(String catalogId) {
    if (catalogId == 'google_workspace') {
      return connectors.any((c) => c['type'] == 'google_workspace' || (c['name'] ?? '').toString().contains('Google'));
    } else if (catalogId == 'zalo_mcp') {
      return connectors.any((c) => (c['name'] ?? '').toString().toLowerCase().contains('zalo'));
    } else if (catalogId == 'botcake') {
      return connectors.any((c) => (c['name'] ?? '').toString().toLowerCase().contains('botcake'));
    } else if (catalogId == 'slack') {
      return connectors.any((c) => (c['name'] ?? '').toString().toLowerCase().contains('slack'));
    }
    return connectors.any((c) => c['id'] == catalogId);
  }

  List<Map<String, dynamic>> getConnectedAccountsForCatalog(String catalogId) {
    if (catalogId == 'google_workspace') {
      return connectors.where((c) => c['type'] == 'google_workspace' || (c['name'] ?? '').toString().contains('Google')).toList();
    } else if (catalogId == 'zalo_mcp') {
      return connectors.where((c) => (c['name'] ?? '').toString().toLowerCase().contains('zalo')).toList();
    }
    return connectors.where((c) => c['id'] == catalogId).toList();
  }

  Future<void> createConnector(String name, Map<String, dynamic> config) async {
    final result = await _connectorsService.createConnector(name, config);
    if (result != null) {
      connectors.insert(0, result);
      Get.snackbar(
        'Thành công',
        'Đã thêm kết nối $name thành công',
        backgroundColor: Colors.green.withValues(alpha: 0.9),
        colorText: Colors.white,
      );
    }
  }

  Future<void> deleteConnector(String id) async {
    final success = await _connectorsService.deleteConnector(id);
    if (success) {
      connectors.removeWhere((c) => c['id'] == id);
      Get.snackbar(
        'Đã xóa',
        'Đã ngắt kết nối thành công',
        backgroundColor: Colors.blue.withValues(alpha: 0.9),
        colorText: Colors.white,
      );
    }
  }

  // --- Google Workspace OAuth2 ---

  final googleConnected = false.obs;
  final googleEmail = ''.obs;
  final googleNeedsReconnect = false.obs;
  final googleServerConfigured = true.obs;
  final isGoogleConnecting = false.obs;
  Timer? _googlePollTimer;

  Future<void> loadGoogleStatus() async {
    final status = await _connectorsService.getGoogleStatus();
    if (status == null) return;
    googleConnected.value = status['connected'] == true;
    googleEmail.value = (status['email'] ?? '') as String;
    googleNeedsReconnect.value = status['needs_reconnect'] == true;
    googleServerConfigured.value = status['server_configured'] == true;
  }

  /// Mở màn hình đồng ý của Google bằng trình duyệt ngoài rồi chờ callback.
  ///
  /// Không nhúng WebView trong app: người dùng cần thấy thanh địa chỉ accounts.google.com
  /// thật để biết mình đang gõ mật khẩu cho Google chứ không phải cho COSA OS. Vì cửa sổ
  /// nằm ngoài app nên không có sự kiện "xong" nào bắn về - phải poll trạng thái.
  Future<void> connectGoogle({String? loginHint}) async {
    isGoogleConnecting.value = true;
    try {
      final url = await _connectorsService.startGoogleOAuth(loginHint: loginHint);
      if (url == null) {
        Get.snackbar('Lỗi', 'Không lấy được liên kết đăng nhập Google');
        return;
      }

      final opened = await launchUrl(
        Uri.parse(url),
        mode: LaunchMode.externalApplication,
      );
      if (!opened) {
        Get.snackbar('Lỗi', 'Không mở được trình duyệt để đăng nhập Google');
        return;
      }
      _startGooglePolling();
    } catch (e) {
      isGoogleConnecting.value = false;
      Get.snackbar(
        'Chưa kết nối được',
        e.toString().replaceFirst('Exception: ', ''),
        backgroundColor: Colors.red.withValues(alpha: 0.9),
        colorText: Colors.white,
        duration: const Duration(seconds: 8),
      );
    }
  }

  void _startGooglePolling() {
    _googlePollTimer?.cancel();
    var elapsed = 0;
    _googlePollTimer = Timer.periodic(const Duration(seconds: 2), (timer) async {
      elapsed += 2;
      await loadGoogleStatus();

      if (googleConnected.value) {
        timer.cancel();
        isGoogleConnecting.value = false;
        await loadConnectors();
        Get.snackbar(
          'Đã kết nối Gmail',
          'Hòm thư ${googleEmail.value} đã sẵn sàng. Thử hỏi "tóm tắt 3 email mới nhất".',
          backgroundColor: Colors.green.withValues(alpha: 0.9),
          colorText: Colors.white,
          duration: const Duration(seconds: 6),
        );
      } else if (elapsed >= 180) {
        // Bỏ cuộc sau 3 phút: người dùng đóng tab giữa chừng thì timer này không được
        // phép chạy mãi và gọi API 2 giây một lần cho tới khi thoát app.
        timer.cancel();
        isGoogleConnecting.value = false;
      }
    });
  }

  // --- Zalo QR Flow ---

  Future<bool> startZaloQrFlow() async {
    isQrStarting.value = true;
    qrDataUrl.value = '';
    qrState.value = 'starting';
    qrError.value = '';
    currentSid = null;

    try {
      final res = await _connectorsService.startZaloQr();
      if (res != null && res['id'] != null) {
        currentSid = res['id'].toString();
        startQrPolling();
        return true;
      } else {
        qrError.value = 'Không khởi tạo được phiên đăng nhập QR';
        return false;
      }
    } catch (e) {
      qrError.value = 'Lỗi kết nối server: $e';
      return false;
    } finally {
      isQrStarting.value = false;
    }
  }

  void startQrPolling() {
    stopQrPolling();
    _qrTimer = Timer.periodic(const Duration(milliseconds: 1500), (_) async {
      if (currentSid == null) return;
      final status = await _connectorsService.getZaloQrStatus(currentSid!);
      if (status != null) {
        qrState.value = status['state'] ?? 'starting';
        qrError.value = status['error'] ?? '';
        if (status.containsKey('qr') && (status['qr'] as String).isNotEmpty) {
          qrDataUrl.value = status['qr'];
        }

        if (qrState.value == 'done') {
          stopQrPolling();
          Get.back(); // Đóng Modal dialog QR
          await loadConnectors(); // Nạp lại kết nối vừa thêm
          Get.snackbar(
            'Thành công',
            'Đăng nhập tài khoản Zalo Agent MCP thành công!',
            snackPosition: SnackPosition.BOTTOM,
            backgroundColor: Colors.green.withValues(alpha: 0.9),
            colorText: Colors.white,
          );
        } else if (qrState.value == 'error') {
          stopQrPolling();
        }
      }
    });
  }

  void stopQrPolling() {
    _qrTimer?.cancel();
    _qrTimer = null;
  }

  void cancelZaloQr() {
    if (currentSid != null) {
      _connectorsService.cancelZaloQr(currentSid!);
    }
    stopQrPolling();
    currentSid = null;
  }

  List<Map<String, dynamic>> get filteredCatalog {
    if (selectedCategory.value == 'Tất cả') {
      return catalogItems;
    }
    return catalogItems
        .where((item) => item['category'] == selectedCategory.value)
        .toList();
  }
}
