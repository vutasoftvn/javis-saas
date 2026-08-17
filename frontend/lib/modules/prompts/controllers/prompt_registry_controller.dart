import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../data/services/auth_service.dart';
import '../../../data/services/prompt_registry_service.dart';

class PromptRegistryController extends GetxController {
  PromptRegistryController({
    PromptRegistryService? service,
    Future<String?> Function()? roleLoader,
  })  : _service = service ?? PromptRegistryService(),
        _roleLoader = roleLoader ?? AuthService().getCachedRole {
    contentController.addListener(_onContentChanged);
  }

  final PromptRegistryService _service;
  final Future<String?> Function() _roleLoader;

  final prompts = <Map<String, dynamic>>[].obs;
  final isLoading = false.obs;
  final isOwner = false.obs;

  // Selected State & Filter
  final selectedDomain = 'all'.obs;
  final searchQuery = ''.obs;
  final selectedPrompt = Rxn<Map<String, dynamic>>();
  final selectedDetail = Rxn<Map<String, dynamic>>();
  final isLoadingDetail = false.obs;
  final isSaving = false.obs;
  final isResetting = false.obs;
  final hasUnsavedChanges = false.obs;
  final selectedDetailTab = 0.obs; // 0: Editor, 1: Revisions, 2: Default Template

  final contentController = TextEditingController();
  final searchController = TextEditingController();

  @override
  void onInit() {
    super.onInit();
    loadRole();
    loadPrompts();
  }

  @override
  void onClose() {
    contentController.removeListener(_onContentChanged);
    contentController.dispose();
    searchController.dispose();
    super.onClose();
  }

  void _onContentChanged() {
    final original = selectedDetail.value?['content'] as String? ?? '';
    hasUnsavedChanges.value = contentController.text != original;
  }

  Future<void> loadRole() async {
    var role = await _roleLoader();
    if (role == null || role.isEmpty) {
      final me = await AuthService().getMe();
      role = me?['role'] as String?;
    }
    isOwner.value = role == 'owner';
  }

  List<String> get availableDomains {
    final set = <String>{};
    for (final p in prompts) {
      final d = p['domain'] as String?;
      if (d != null && d.isNotEmpty) {
        set.add(d);
      }
    }
    final list = set.toList()..sort();
    return ['all', ...list];
  }

  List<Map<String, dynamic>> get filteredPrompts {
    final query = searchQuery.value.trim().toLowerCase();
    final domain = selectedDomain.value;

    return prompts.where((p) {
      final pDomain = (p['domain'] as String? ?? '').toLowerCase();
      final pName = (p['name'] as String? ?? '').toLowerCase();

      if (domain != 'all' && pDomain != domain.toLowerCase()) {
        return false;
      }

      if (query.isNotEmpty) {
        final matchName = pName.contains(query);
        final matchDomain = pDomain.contains(query);
        if (!matchName && !matchDomain) {
          return false;
        }
      }
      return true;
    }).toList();
  }

  int getDomainCount(String domain) {
    if (domain == 'all') return prompts.length;
    return prompts.where((p) => p['domain'] == domain).length;
  }

  List<String> get detectedVariables {
    final content = contentController.text;
    final exp = RegExp(r'\$\{([a-zA-Z0-9_]+)\}');
    final matches = exp.allMatches(content);
    final vars = <String>{};
    for (final m in matches) {
      final v = m.group(1);
      if (v != null) vars.add(v);
    }
    return vars.toList()..sort();
  }

  Future<void> loadPrompts({bool keepSelection = true}) async {
    isLoading.value = true;
    try {
      final data = await _service.listPrompts();
      prompts.assignAll(data);

      if (keepSelection && selectedPrompt.value != null) {
        final currDomain = selectedPrompt.value!['domain'];
        final currName = selectedPrompt.value!['name'];
        final found = prompts.firstWhereOrNull(
          (p) => p['domain'] == currDomain && p['name'] == currName,
        );
        if (found != null) {
          selectedPrompt.value = found;
        } else if (filteredPrompts.isNotEmpty) {
          await selectPrompt(filteredPrompts.first);
        }
      } else if (filteredPrompts.isNotEmpty && selectedPrompt.value == null) {
        await selectPrompt(filteredPrompts.first);
      }
    } catch (e) {
      debugPrint('Error loading prompts: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> selectDomain(String domain) async {
    selectedDomain.value = domain;
    final currentList = filteredPrompts;
    if (currentList.isNotEmpty) {
      final curr = selectedPrompt.value;
      if (curr == null || !currentList.any((p) => p['domain'] == curr['domain'] && p['name'] == curr['name'])) {
        await selectPrompt(currentList.first);
      }
    }
  }

  Future<void> updateSearch(String query) async {
    searchQuery.value = query;
    final currentList = filteredPrompts;
    if (currentList.isNotEmpty) {
      final curr = selectedPrompt.value;
      if (curr == null || !currentList.any((p) => p['domain'] == curr['domain'] && p['name'] == curr['name'])) {
        await selectPrompt(currentList.first);
      }
    }
  }

  Future<void> selectPrompt(Map<String, dynamic> prompt) async {
    selectedPrompt.value = prompt;
    final domain = prompt['domain'] as String;
    final name = prompt['name'] as String;

    isLoadingDetail.value = true;
    try {
      final detail = await _service.getPrompt(domain, name);
      selectedDetail.value = detail;
      final content = detail['content'] as String? ?? '';
      contentController.text = content;
      hasUnsavedChanges.value = false;
    } catch (e) {
      debugPrint('Error loading prompt detail: $e');
      _showSnackbar(
        'Lỗi tải chi tiết',
        '$e',
        bg: const Color(0xFFEF4444).withValues(alpha: 0.85),
      );
    } finally {
      isLoadingDetail.value = false;
    }
  }

  Future<Map<String, dynamic>> loadDetail(String domain, String name) {
    return _service.getPrompt(domain, name);
  }

  void discardChanges() {
    final original = selectedDetail.value?['content'] as String? ?? '';
    contentController.text = original;
    hasUnsavedChanges.value = false;
  }

  void restoreRevision(String revisionContent) {
    contentController.text = revisionContent;
    _onContentChanged();
    selectedDetailTab.value = 0; // Switch to editor
    _showSnackbar(
      'Đã nạp nội dung phiên bản',
      'Nội dung phiên bản cũ đã được điền vào trình soạn thảo. Bấm "Lưu phiên bản" để áp dụng.',
      bg: const Color(0xFF00E5FF).withValues(alpha: 0.85),
      fg: const Color(0xFF04070E),
    );
  }

  Future<void> saveCurrentPrompt() async {
    final curr = selectedPrompt.value;
    if (curr == null) return;
    final domain = curr['domain'] as String;
    final name = curr['name'] as String;
    final content = contentController.text;

    isSaving.value = true;
    try {
      await _service.updatePrompt(domain, name, content);
      await loadPrompts(keepSelection: true);
      // Refresh detail
      final detail = await _service.getPrompt(domain, name);
      selectedDetail.value = detail;
      hasUnsavedChanges.value = false;

      _showSnackbar(
        'Đã lưu thành công',
        'Prompt "$domain/$name" đã được cập nhật phiên bản mới',
        bg: const Color(0xFF10B981).withValues(alpha: 0.85),
      );
    } catch (e) {
      _showSnackbar(
        'Lỗi lưu prompt',
        '$e',
        bg: const Color(0xFFEF4444).withValues(alpha: 0.85),
      );
    } finally {
      isSaving.value = false;
    }
  }

  Future<void> resetCurrentPrompt() async {
    final curr = selectedPrompt.value;
    if (curr == null) return;
    final domain = curr['domain'] as String;
    final name = curr['name'] as String;

    isResetting.value = true;
    try {
      await _service.resetPrompt(domain, name);
      await loadPrompts(keepSelection: true);
      final detail = await _service.getPrompt(domain, name);
      selectedDetail.value = detail;
      contentController.text = detail['content'] as String? ?? '';
      hasUnsavedChanges.value = false;

      _showSnackbar(
        'Đã đặt lại mặc định',
        'Prompt "$domain/$name" đã được khôi phục về bản gốc của hệ thống',
        bg: const Color(0xFF00E5FF).withValues(alpha: 0.85),
        fg: const Color(0xFF04070E),
      );
    } catch (e) {
      _showSnackbar(
        'Lỗi đặt lại prompt',
        '$e',
        bg: const Color(0xFFEF4444).withValues(alpha: 0.85),
      );
    } finally {
      isResetting.value = false;
    }
  }

  Future<void> savePrompt(String domain, String name, String content) async {
    try {
      await _service.updatePrompt(domain, name, content);
      await loadPrompts();
      _showSnackbar(
        'Đã lưu',
        'Prompt "$domain/$name" đã được cập nhật',
        bg: const Color(0xFF10B981).withValues(alpha: 0.8),
      );
    } catch (e) {
      _showSnackbar(
        'Lỗi lưu prompt',
        '$e',
        bg: const Color(0xFFEF4444).withValues(alpha: 0.8),
      );
    }
  }

  Future<void> resetPrompt(String domain, String name) async {
    try {
      await _service.resetPrompt(domain, name);
      await loadPrompts();
      _showSnackbar(
        'Đã đặt lại mặc định',
        'Prompt "$domain/$name" đã trở về nội dung mặc định',
        bg: const Color(0xFF00E5FF).withValues(alpha: 0.8),
        fg: Colors.black,
      );
    } catch (e) {
      _showSnackbar(
        'Lỗi đặt lại prompt',
        '$e',
        bg: const Color(0xFFEF4444).withValues(alpha: 0.8),
      );
    }
  }

  void _showSnackbar(String title, String message, {Color? bg, Color? fg}) {
    if (Get.context == null) return;
    Get.snackbar(
      title,
      message,
      backgroundColor: bg ?? const Color(0xFF10B981).withValues(alpha: 0.85),
      colorText: fg ?? Colors.white,
      snackPosition: SnackPosition.BOTTOM,
      margin: const EdgeInsets.all(12),
      duration: const Duration(seconds: 3),
    );
  }
}
