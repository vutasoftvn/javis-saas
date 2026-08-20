import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../modules/vault/services/vault_service.dart';
import '../../../core/network/realtime_service.dart';

class VaultFolderNode {
  final String key;
  final String name;
  final String fullPath;
  final Map<String, VaultFolderNode> children;
  int fileCount;

  VaultFolderNode({
    required this.key,
    required this.name,
    required this.fullPath,
    Map<String, VaultFolderNode>? children,
    this.fileCount = 0,
  }) : children = children ?? {};
}

class VaultController extends GetxController {
  final VaultService _vaultService = VaultService();
  final RealtimeService _realtimeService = RealtimeService();

  static const String _viewModeStorageKey = 'vault_view_mode';

  final isLoading = false.obs;
  final documents = [].obs;
  final knowledgeObjects = <Map<String, dynamic>>[].obs;
  final backlinks = <Map<String, dynamic>>[].obs;
  final selectedKnowledgeType = ''.obs;
  final selectedKnowledgeStatus = ''.obs;
  final showKnowledgeStudio = false.obs;

  // View mode: 'list' or 'grid' (persisted locally)
  final viewMode = 'list'.obs;

  final selectedDocumentContent = RxnString();
  final isEditing = false.obs;
  final selectedDocumentPath = RxnString();
  final selectedDocumentRevision = RxnString();
  final selectedKnowledgeId = RxnString();
  final textController = TextEditingController();
  final searchQuery = ''.obs;

  // Folder navigation: 'all', 'root', or folder path (e.g. 'mID')
  final selectedFolder = 'all'.obs;
  final expandedFolders = <String, bool>{}.obs;

  bool get isViewingDocumentDetail => selectedDocumentPath.value != null;

  @override
  void onInit() {
    super.onInit();
    _loadSavedViewMode();
    loadDocuments();
    loadKnowledgeObjects();
    _realtimeService.addListener(_onRealtimeEvent);
  }

  @override
  void onClose() {
    _realtimeService.removeListener(_onRealtimeEvent);
    super.onClose();
  }

  Future<void> _loadSavedViewMode() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString(_viewModeStorageKey);
      if (saved != null && (saved == 'list' || saved == 'grid')) {
        viewMode.value = saved;
      }
    } catch (_) {}
  }

  Future<void> setViewMode(String mode) async {
    viewMode.value = mode;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_viewModeStorageKey, mode);
    } catch (_) {}
  }

  void _onRealtimeEvent(String eventType, Map<String, dynamic> data) {
    if (eventType.startsWith('knowledge.') || eventType == 'system.connected') {
      loadKnowledgeObjects();
    }
  }

  Future<void> loadKnowledgeObjects() async {
    final list = await _vaultService.getKnowledgeObjects(
      type: selectedKnowledgeType.value.isNotEmpty ? selectedKnowledgeType.value : null,
      status: selectedKnowledgeStatus.value.isNotEmpty ? selectedKnowledgeStatus.value : null,
    );
    knowledgeObjects.value = list.cast<Map<String, dynamic>>();
  }

  Future<void> loadBacklinks(String objectId) async {
    final list = await _vaultService.getBacklinks(objectId);
    backlinks.value = list.cast<Map<String, dynamic>>();
  }

  Future<void> promoteObject(String objectId) async {
    final success = await _vaultService.promoteKnowledgeObject(objectId);
    if (success) {
      Get.snackbar(
        'Đã Phê duyệt',
        'Tri thức đã được nâng cấp lên trạng thái Chính thức (Approved)',
        backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.2),
        colorText: const Color(0xFF10B981),
      );
      await loadKnowledgeObjects();
    }
  }

  Future<void> loadDocuments() async {
    isLoading.value = true;
    final docs = await _vaultService.getDocuments();
    documents.value = docs;
    isLoading.value = false;

    // If currently selected document is no longer active in documents, reset detail view
    if (selectedDocumentPath.value != null) {
      final exists = docs.any((d) => d['path'] == selectedDocumentPath.value);
      if (!exists) {
        selectedDocumentPath.value = null;
        selectedDocumentContent.value = null;
      }
    }
  }

  String getFolderName(String path) {
    if (!path.contains('/')) return 'root';
    return path.substring(0, path.lastIndexOf('/'));
  }

  String getFileName(String path) {
    return path.split('/').last;
  }

  void selectFolder(String folder) {
    selectedFolder.value = folder;
    selectedDocumentPath.value = null; // Return to file list of this folder
  }

  void backToFolderList() {
    selectedDocumentPath.value = null;
    isEditing.value = false;
  }

  void toggleFolderExpansion(String folderPath) {
    expandedFolders[folderPath] = !(expandedFolders[folderPath] ?? true);
  }

  bool isFolderExpanded(String folderPath) {
    return expandedFolders[folderPath] ?? true;
  }

  /// Builds a parent -> child tree hierarchy of folders from documents
  VaultFolderNode get folderTree {
    final root = VaultFolderNode(key: 'root', name: 'Root', fullPath: '');

    for (final doc in documents) {
      final String path = doc['path'] ?? '';
      if (!path.contains('/')) {
        root.fileCount++;
        continue;
      }

      final segments = path.split('/');
      // remove the last segment (the file name)
      segments.removeLast();

      VaultFolderNode current = root;
      String currentPath = '';

      for (int i = 0; i < segments.length; i++) {
        final seg = segments[i];
        currentPath = currentPath.isEmpty ? seg : '$currentPath/$seg';

        if (!current.children.containsKey(seg)) {
          current.children[seg] = VaultFolderNode(
            key: seg,
            name: seg,
            fullPath: currentPath,
          );
        }
        current = current.children[seg]!;
      }
      current.fileCount++;
    }

    return root;
  }

  List<dynamic> get filteredDocuments {
    return documents.where((doc) {
      final String path = doc['path'] ?? '';
      final matchesSearch = searchQuery.value.isEmpty ||
          path.toLowerCase().contains(searchQuery.value.toLowerCase());
      if (!matchesSearch) return false;

      if (selectedFolder.value == 'all') return true;
      if (selectedFolder.value == 'root') {
        return !path.contains('/');
      }

      // Check if file is in the selected folder or a subfolder of it
      final folder = getFolderName(path);
      return folder == selectedFolder.value || folder.startsWith('${selectedFolder.value}/');
    }).toList();
  }

  Future<void> openDocument(String path) async {
    selectedDocumentPath.value = path;
    isEditing.value = false;
    selectedDocumentContent.value = 'Đang tải nội dung...';
    textController.text = '';

    final doc = await _vaultService.getDocumentContent(path);
    if (doc != null) {
      selectedDocumentContent.value = doc['content'] ?? '';
      textController.text = doc['content'] ?? '';
      selectedDocumentRevision.value = doc['current_revision_id'];
    } else {
      selectedDocumentContent.value = 'Không thể tải nội dung tài liệu.';
    }
  }

  void toggleEdit() {
    isEditing.value = !isEditing.value;
    if (!isEditing.value) {
      textController.text = selectedDocumentContent.value ?? '';
    }
  }

  Future<void> saveDocument() async {
    if (selectedDocumentPath.value == null) return;
    try {
      final newContent = textController.text;
      await _vaultService.writeDocument(
        selectedDocumentPath.value!,
        newContent,
        baseRevisionId: selectedDocumentRevision.value,
      );
      selectedDocumentContent.value = newContent;
      isEditing.value = false;
      loadDocuments();
      Get.snackbar(
        'Đã lưu',
        'Tài liệu đã được cập nhật thành công vào Vault',
        backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.2),
        colorText: const Color(0xFF10B981),
      );
    } catch (e) {
      Get.snackbar('Lỗi', 'Không thể lưu tài liệu');
    }
  }
}
