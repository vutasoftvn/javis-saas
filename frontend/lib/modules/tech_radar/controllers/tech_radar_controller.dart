import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/services/tech_radar_service.dart';

class TechRadarController extends GetxController {
  final TechRadarService _service = TechRadarService();

  final items = <Map<String, dynamic>>[].obs;
  final isLoading = false.obs;
  final selectedCategory = 'ALL'.obs;
  final selectedStatus = 'ALL'.obs;
  final searchQuery = ''.obs;

  final categories = <String>[
    'ALL',
    'AI & Models',
    'Orchestration & Agents',
    'Memory & State',
    'Execution & Sandbox',
    'Workflow & Automation',
    'Quality & Security',
    'Database & Storage',
    'Channels & Protocols',
  ].obs;

  @override
  void onInit() {
    super.onInit();
    loadItems();
  }

  Future<void> loadItems() async {
    isLoading.value = true;
    try {
      final categoryFilter = selectedCategory.value == 'ALL' ? null : selectedCategory.value;
      final statusFilter = selectedStatus.value == 'ALL' ? null : selectedStatus.value;
      final data = await _service.listItems(
        category: categoryFilter,
        status: statusFilter,
      );
      items.assignAll(data);
    } catch (e) {
      debugPrint('Error loading tech radar items: $e');
    } finally {
      isLoading.value = false;
    }
  }

  List<Map<String, dynamic>> get filteredItems {
    return items.where((item) {
      final matchesSearch = searchQuery.value.isEmpty ||
          (item['name']?.toString().toLowerCase().contains(searchQuery.value.toLowerCase()) ?? false) ||
          (item['category']?.toString().toLowerCase().contains(searchQuery.value.toLowerCase()) ?? false) ||
          (item['description']?.toString().toLowerCase().contains(searchQuery.value.toLowerCase()) ?? false);
      
      final matchesStatus = selectedStatus.value == 'ALL' ||
          (item['status']?.toString().toUpperCase() == selectedStatus.value);

      final matchesCategory = selectedCategory.value == 'ALL' ||
          (item['category']?.toString().toLowerCase() == selectedCategory.value.toLowerCase());

      return matchesSearch && matchesStatus && matchesCategory;
    }).toList();
  }

  int countByStatus(String status) {
    return items.where((item) => item['status']?.toString().toUpperCase() == status).length;
  }

  Future<void> seedDefaults() async {
    isLoading.value = true;
    try {
      final seeded = await _service.seedDefaults();
      items.assignAll(seeded);
      Get.snackbar(
        'Radar Công nghệ',
        'Đã khởi tạo ${seeded.length} công nghệ mẫu từ Spec §104',
        backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Lỗi',
        'Không thể khởi tạo mẫu: $e',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> createItem({
    required String name,
    required String category,
    String status = 'WATCH',
    String maturity = 'experimental',
    String potential = 'high',
    String cosaUse = 'pattern',
    String integration = 'no',
    String? description,
  }) async {
    try {
      await _service.createItem(
        name: name,
        category: category,
        status: status,
        maturity: maturity,
        potential: potential,
        cosaUse: cosaUse,
        integration: integration,
        description: description,
        lastReviewed: DateTime.now().toIso8601String().split('T').first,
      );
      await loadItems();
      Get.snackbar(
        'Thành công',
        'Đã thêm công nghệ mới vào Radar',
        backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Lỗi',
        'Không thể thêm: $e',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    }
  }

  Future<void> updateItemStatus(String itemId, String newStatus) async {
    try {
      await _service.updateItem(
        itemId: itemId,
        status: newStatus,
        lastReviewed: DateTime.now().toIso8601String().split('T').first,
      );
      final index = items.indexWhere((it) => it['id']?.toString() == itemId);
      if (index != -1) {
        items[index]['status'] = newStatus;
        items.refresh();
      }
      Get.snackbar(
        'Cập nhật Radar',
        'Đã chuyển trạng thái sang $newStatus',
        backgroundColor: const Color(0xFF00E5FF).withValues(alpha: 0.8),
        colorText: Colors.black,
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Lỗi',
        'Không thể cập nhật: $e',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    }
  }
}
