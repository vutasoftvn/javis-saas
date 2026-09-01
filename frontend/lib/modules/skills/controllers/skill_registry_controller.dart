import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../modules/skills/services/skill_registry_service.dart';

class SkillRegistryController extends GetxController {
  final SkillRegistryService _service = SkillRegistryService();

  final skills = <Map<String, dynamic>>[].obs;
  final isLoading = false.obs;
  final selectedDomain = 'ALL'.obs;
  final selectedStatus = 'ALL'.obs;
  final searchQuery = ''.obs;
  final selectedSkill = Rxn<Map<String, dynamic>>();

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
      if (selectedSkill.value != null) {
        final found = data.firstWhereOrNull((s) => s['id']?.toString() == selectedSkill.value?['id']?.toString());
        if (found != null) {
          selectedSkill.value = found;
        }
      }
    } catch (e) {
      debugPrint('Error loading skills: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> syncBuiltInSkills() async {
    isLoading.value = true;
    try {
      final data = await _service.syncBuiltInSkills();
      skills.assignAll(data);
      AppToast.success(
        'Đã nạp ${data.length} kỹ năng tích hợp sẵn (Built-in Skills) vào Workspace',
        title: 'Đồng bộ thành công',
      );
    } catch (e) {
      AppToast.error(
        '$e',
        title: 'Lỗi đồng bộ',
      );
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
      AppToast.success(
        'Kỹ năng mới đã được đưa vào hàng đợi kiểm thử Candidate',
        title: 'Đã tạo ứng viên kỹ năng',
      );
    } catch (e) {
      AppToast.error(
        '$e',
        title: 'Lỗi tạo kỹ năng',
      );
    }
  }

  Future<void> updateSkill({
    required String skillId,
    String? name,
    String? description,
    String? instructions,
    List<String>? toolPermissions,
    String? domain,
    String? version,
  }) async {
    try {
      final updated = await _service.updateSkill(
        skillId: skillId,
        name: name,
        description: description,
        instructions: instructions,
        toolPermissions: toolPermissions,
        domain: domain,
        version: version,
      );
      await loadSkills();
      if (updated.isNotEmpty) {
        selectedSkill.value = updated;
      }
      AppToast.success(
        'Cập nhật thông tin kỹ năng thành công',
        title: 'Đã lưu thay đổi',
      );
    } catch (e) {
      AppToast.error(
        '$e',
        title: 'Lỗi cập nhật',
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
      AppToast.info(
        'Điểm kiểm thử: ${(score * 100).toInt()}%',
        title: 'Đánh giá hoàn tất',
      );
    } catch (e) {
      AppToast.error(
        '$e',
        title: 'Lỗi đánh giá',
      );
    }
  }

  Future<void> promoteSkill(
    String skillId, {
    String approvedBy = 'founder_admin',
    String approvalReason = 'Phê duyệt chuyển sang production qua Skill Registry console',
    String? version,
  }) async {
    try {
      await _service.promoteSkill(
        skillId: skillId,
        approvedBy: approvedBy,
        approvalReason: approvalReason,
        version: version,
      );
      await loadSkills();
      AppToast.success(
        'Kỹ năng đã được nâng cấp lên Production (Active)',
        title: 'Phê duyệt thành công',
      );
    } catch (e) {
      AppToast.error(
        '$e',
        title: 'Không thể phê duyệt',
      );
    }
  }

  Future<void> deprecateSkill(String skillId, {String? reason}) async {
    try {
      await _service.deprecateSkill(skillId, reason: reason);
      await loadSkills();
      AppToast.warning(
        'Kỹ năng đã chuyển sang trạng thái Deprecated',
        title: 'Đã ngưng sử dụng',
      );
    } catch (e) {
      AppToast.error(
        '$e',
        title: 'Lỗi',
      );
    }
  }
}
