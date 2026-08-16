import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/services/skill_registry_service.dart';

class SkillRegistryController extends GetxController {
  final SkillRegistryService _service = SkillRegistryService();

  final skills = <Map<String, dynamic>>[].obs;
  final isLoading = false.obs;
  final selectedDomain = 'ALL'.obs;
  final selectedStatus = 'ALL'.obs;
  final searchQuery = ''.obs;

  final domains = <String>[
    'ALL',
    'sales',
    'marketing',
    'finance',
    'legal',
    'operations',
    'tech',
  ].obs;

  @override
  void onInit() {
    super.onInit();
    loadSkills();
  }

  Future<void> loadSkills() async {
    isLoading.value = true;
    try {
      final domainFilter = selectedDomain.value == 'ALL' ? null : selectedDomain.value;
      final statusFilter = selectedStatus.value == 'ALL' ? null : selectedStatus.value;
      final data = await _service.listSkills(
        domain: domainFilter,
        status: statusFilter,
      );
      skills.assignAll(data);
    } catch (e) {
      debugPrint('Error loading skills: $e');
    } finally {
      isLoading.value = false;
    }
  }

  List<Map<String, dynamic>> get filteredSkills {
    return skills.where((s) {
      final matchesSearch = searchQuery.value.isEmpty ||
          (s['name']?.toString().toLowerCase().contains(searchQuery.value.toLowerCase()) ?? false) ||
          (s['domain']?.toString().toLowerCase().contains(searchQuery.value.toLowerCase()) ?? false) ||
          (s['description']?.toString().toLowerCase().contains(searchQuery.value.toLowerCase()) ?? false);

      final matchesStatus = selectedStatus.value == 'ALL' ||
          (s['status']?.toString().toLowerCase() == selectedStatus.value.toLowerCase());

      final matchesDomain = selectedDomain.value == 'ALL' ||
          (s['domain']?.toString().toLowerCase() == selectedDomain.value.toLowerCase());

      return matchesSearch && matchesStatus && matchesDomain;
    }).toList();
  }

  int countByStatus(String status) {
    return skills.where((s) => s['status']?.toString().toLowerCase() == status.toLowerCase()).length;
  }

  double get averageSuccessRate {
    final active = skills.where((s) => s['status'] == 'active').toList();
    if (active.isEmpty) return 0.0;
    final total = active.fold<double>(0.0, (acc, s) => acc + ((s['success_rate'] as num?)?.toDouble() ?? 0.0));
    return total / active.length;
  }

  Future<void> createCandidate({
    required String name,
    required String domain,
    required String instructions,
    String description = '',
    List<String> scope = const [],
    List<String> toolPermissions = const [],
    List<String> requiredContext = const [],
    String? createdByAgent,
  }) async {
    try {
      await _service.createCandidate(
        name: name,
        domain: domain,
        instructions: instructions,
        description: description,
        scope: scope,
        toolPermissions: toolPermissions,
        requiredContext: requiredContext,
        createdByAgent: createdByAgent,
      );
      await loadSkills();
      Get.snackbar(
        'Đã tạo ứng viên kỹ năng',
        'Kỹ năng mới đã được đưa vào hàng đợi kiểm thử Candidate',
        backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Lỗi tạo kỹ năng',
        '$e',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    }
  }

  Future<void> evaluateSkill(String skillId, double score, {Map<String, dynamic>? details}) async {
    try {
      await _service.evaluateSkill(
        skillId: skillId,
        evalScore: score,
        evalDetails: details,
      );
      await loadSkills();
      Get.snackbar(
        'Đánh giá hoàn tất',
        'Điểm kiểm thử: ${(score * 100).toInt()}%',
        backgroundColor: const Color(0xFF00E5FF).withValues(alpha: 0.8),
        colorText: Colors.black,
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Lỗi đánh giá',
        '$e',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    }
  }

  Future<void> promoteSkill(String skillId) async {
    try {
      await _service.promoteSkill(skillId);
      await loadSkills();
      Get.snackbar(
        'Phê duyệt thành công',
        'Kỹ năng đã được nâng cấp lên Production (Active)',
        backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Không thể phê duyệt',
        '$e',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    }
  }

  Future<void> deprecateSkill(String skillId, {String? reason}) async {
    try {
      await _service.deprecateSkill(skillId, reason: reason);
      await loadSkills();
      Get.snackbar(
        'Đã ngưng sử dụng',
        'Kỹ năng đã chuyển sang trạng thái Deprecated',
        backgroundColor: const Color(0xFFF59E0B).withValues(alpha: 0.8),
        colorText: Colors.black,
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Lỗi',
        '$e',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    }
  }
}
