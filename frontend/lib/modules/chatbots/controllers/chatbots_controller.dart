import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/services/channels_service.dart';

class ChatbotsController extends GetxController {
  final ChannelsService _channelsService = ChannelsService();

  final isLoading = false.obs;
  final isSaving = false.obs;
  final isTesting = false.obs;
  final chatbots = <dynamic>[].obs;
  final searchQuery = ''.obs;
  final selectedChannelFilter = ''.obs; // '', 'telegram', 'zalo'

  @override
  void onInit() {
    super.onInit();
    loadData();
  }

  Future<void> loadData() async {
    isLoading.value = true;
    try {
      final list = await _channelsService.getChatbots();
      chatbots.assignAll(list);
    } catch (e) {
      Get.snackbar('Lỗi', 'Không nạp được danh sách bot: $e');
    } finally {
      isLoading.value = false;
    }
  }

  List<dynamic> get filteredChatbots {
    return chatbots.where((b) {
      final channel = (b['channel'] ?? 'telegram').toString().toLowerCase();
      final name = (b['name'] ?? '').toString().toLowerCase();
      final username = (b['bot_username'] ?? '').toString().toLowerCase();

      // Check channel filter
      if (selectedChannelFilter.value.isNotEmpty && channel != selectedChannelFilter.value) {
        return false;
      }

      // Check search query
      if (searchQuery.value.isNotEmpty) {
        final q = searchQuery.value.toLowerCase();
        return name.contains(q) || username.contains(q);
      }

      return true;
    }).toList();
  }

  Future<void> toggleBot(Map<String, dynamic> bot) async {
    final channel = (bot['channel'] ?? 'telegram').toString().toLowerCase();
    final currentEnabled = bot['is_enabled'] == true || bot['status'] == 'running';
    final newEnabled = !currentEnabled;

    isSaving.value = true;
    try {
      Map<String, dynamic> res;
      if (channel == 'telegram') {
        res = await _channelsService.saveTelegramChannel(
          isEnabled: newEnabled,
          botToken: (bot['bot_token'] ?? '').toString(),
          allowedChatIds: (bot['allowed_chat_ids'] ?? '').toString(),
        );
      } else {
        res = await _channelsService.saveZaloChannel(
          isEnabled: newEnabled,
          botToken: (bot['bot_token'] ?? '').toString(),
          allowedChatIds: (bot['allowed_chat_ids'] ?? '').toString(),
        );
      }

      if (res['status'] == 'success') {
        await loadData();
        Get.snackbar(
          'Thành công',
          newEnabled ? 'Đã BẬT bot thành công' : 'Đã TẮT bot thành công',
          backgroundColor: newEnabled ? Colors.green.withValues(alpha: 0.9) : Colors.orange.withValues(alpha: 0.9),
          colorText: Colors.white,
        );
      } else {
        Get.snackbar('Lỗi', res['message'] ?? 'Không cập nhật được trạng thái bot', backgroundColor: Colors.red);
      }
    } catch (e) {
      Get.snackbar('Lỗi', 'Lỗi kết nối: $e', backgroundColor: Colors.red);
    } finally {
      isSaving.value = false;
    }
  }

  Future<void> saveBotConfig({
    required String channel,
    required String token,
    required String allowedChatIds,
    required bool isEnabled,
  }) async {
    if (token.trim().isEmpty) {
      Get.snackbar('Cảnh báo', 'Vui lòng nhập Bot Token', backgroundColor: Colors.amber);
      return;
    }

    isSaving.value = true;
    try {
      Map<String, dynamic> res;
      if (channel == 'telegram') {
        res = await _channelsService.saveTelegramChannel(
          isEnabled: isEnabled,
          botToken: token.trim(),
          allowedChatIds: allowedChatIds.trim(),
        );
      } else {
        res = await _channelsService.saveZaloChannel(
          isEnabled: isEnabled,
          botToken: token.trim(),
          allowedChatIds: allowedChatIds.trim(),
        );
      }

      if (res['status'] == 'success') {
        Get.back(); // Đóng Modal Form
        await loadData();
        Get.snackbar(
          'Thành công',
          res['message'] ?? 'Đã lưu cấu hình Bot thành công',
          backgroundColor: Colors.green.withValues(alpha: 0.9),
          colorText: Colors.white,
        );
      } else {
        Get.snackbar('Lỗi cấu hình', res['message'] ?? 'Không lưu được bot', backgroundColor: Colors.red.withValues(alpha: 0.9), colorText: Colors.white);
      }
    } catch (e) {
      Get.snackbar('Lỗi hệ thống', 'Lỗi: $e', backgroundColor: Colors.red);
    } finally {
      isSaving.value = false;
    }
  }

  Future<void> testBot(Map<String, dynamic> bot) async {
    final channel = (bot['channel'] ?? 'telegram').toString().toLowerCase();
    isTesting.value = true;
    try {
      Map<String, dynamic> res;
      if (channel == 'telegram') {
        res = await _channelsService.testTelegramChannel();
      } else {
        res = await _channelsService.testZaloChannel();
      }

      if (res['status'] == 'success') {
        Get.snackbar(
          'Thành công',
          res['message'] ?? 'Kiểm tra gửi tin nhắn thành công!',
          backgroundColor: Colors.green.withValues(alpha: 0.9),
          colorText: Colors.white,
          duration: const Duration(seconds: 4),
        );
      } else {
        Get.snackbar('Lỗi kiểm tra', res['message'] ?? 'Không gửi được tin thử nghiệm', backgroundColor: Colors.red.withValues(alpha: 0.9), colorText: Colors.white);
      }
    } catch (e) {
      Get.snackbar('Lỗi kết nối', 'Lỗi: $e', backgroundColor: Colors.red);
    } finally {
      isTesting.value = false;
    }
  }
}
