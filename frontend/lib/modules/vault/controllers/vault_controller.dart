import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../data/services/vault_service.dart';
import '../../../core/network/realtime_service.dart';

class VaultController extends GetxController {
  final VaultService _vaultService = VaultService();
  final RealtimeService _realtimeService = RealtimeService();

  final isLoading = false.obs;
  final documents = [].obs;
  final knowledgeObjects = <Map<String, dynamic>>[].obs;
  final backlinks = <Map<String, dynamic>>[].obs;
  final selectedKnowledgeType = ''.obs;
  final selectedKnowledgeStatus = ''.obs;

  final selectedDocumentContent = RxnString();
  final isViewingDocument = false.obs;
  final isEditing = false.obs;
  final selectedDocumentPath = RxnString();
  final selectedDocumentRevision = RxnString();
  final selectedKnowledgeId = RxnString();
  final textController = TextEditingController();
  final searchQuery = ''.obs;

  @override
  void onInit() {
    super.onInit();
    loadDocuments();
    loadKnowledgeObjects();
    _realtimeService.addListener(_onRealtimeEvent);
  }

  @override
  void onClose() {
    _realtimeService.removeListener(_onRealtimeEvent);
    super.onClose();
  }

  void _onRealtimeEvent(String eventType, Map<String, dynamic> data) {
    // 'system.connected' fires on every (re)connect, including reconnects
    // after a dropped network - refetch then so state reconciles against the
    // durable tables instead of staying stale from before the drop.
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
    documents.value = await _vaultService.getDocuments();
    isLoading.value = false;
  }
  
  List<dynamic> get filteredDocuments {
    if (searchQuery.value.isEmpty) return documents;
    return documents.where((doc) {
      final String path = doc['path'] ?? '';
      return path.toLowerCase().contains(searchQuery.value.toLowerCase());
    }).toList();
  }

  Future<void> openDocument(String path) async {
    isViewingDocument.value = true;
    isEditing.value = false;
    selectedDocumentPath.value = path;
    selectedDocumentContent.value = 'Loading...';
    textController.text = '';
    
    final doc = await _vaultService.getDocumentContent(path);
    if (doc != null) {
      selectedDocumentContent.value = doc['content'] ?? 'Empty document.';
      textController.text = doc['content'] ?? '';
      selectedDocumentRevision.value = doc['current_revision_id'];
    } else {
      selectedDocumentContent.value = 'Failed to load document content.';
    }
  }

  void closeDocument() {
    isViewingDocument.value = false;
    isEditing.value = false;
    selectedDocumentContent.value = null;
    selectedDocumentPath.value = null;
  }

  void toggleEdit() {
    isEditing.value = !isEditing.value;
    if (!isEditing.value) {
      // Revert edits
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
        baseRevisionId: selectedDocumentRevision.value
      );
      selectedDocumentContent.value = newContent;
      isEditing.value = false;
      loadDocuments();
    } catch (e) {
      Get.snackbar('Error', 'Failed to save document');
    }
  }
}
