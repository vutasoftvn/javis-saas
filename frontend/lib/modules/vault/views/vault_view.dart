import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/localization/app_translations.dart';
import '../controllers/vault_controller.dart';
import '../models/vault_document.dart';

/// Task 12 (plan local-first-enterprise-knowledge) — Vault UI thật, thay thế
/// màn hình "chưa khả dụng" (Task 5, Truthful MVP Hardening). Chỉ hiển thị
/// document + action mà backend thật trả về — không có state/quyền giả lập.
class VaultView extends GetView<VaultController> {
  const VaultView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<VaultController>()) {
      Get.put(VaultController());
    }

    return Container(
      color: const Color(0xFF040711),
      child: SafeArea(
        child: Column(
          children: [
            _Header(onCreate: () => _showCreateDialog(context)),
            Expanded(
              child: Obx(() {
                if (controller.isLoading.value && controller.documents.isEmpty) {
                  return const Center(
                    child: CircularProgressIndicator(color: Color(0xFF38BDF8)),
                  );
                }
                if (controller.errorMessage.value != null && controller.documents.isEmpty) {
                  return _ErrorState(
                    message: controller.errorMessage.value!,
                    onRetry: controller.loadDocuments,
                  );
                }
                if (controller.documents.isEmpty) {
                  return const _EmptyState();
                }
                return RefreshIndicator(
                  onRefresh: controller.loadDocuments,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: controller.documents.length,
                    itemBuilder: (context, index) =>
                        _DocumentCard(document: controller.documents[index]),
                  ),
                );
              }),
            ),
          ],
        ),
      ),
    );
  }

  void _showCreateDialog(BuildContext context) {
    final titleController = TextEditingController();
    final contentController = TextEditingController();

    showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          backgroundColor: const Color(0xFF0B1220),
          title: const Text('Tài liệu mới', style: TextStyle(color: Colors.white)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: titleController,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(labelText: 'Tiêu đề'),
              ),
              TextField(
                controller: contentController,
                style: const TextStyle(color: Colors.white),
                maxLines: 4,
                decoration: const InputDecoration(labelText: 'Nội dung'),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Huỷ'),
            ),
            TextButton(
              onPressed: () async {
                final title = titleController.text.trim();
                final content = contentController.text;
                if (title.isEmpty || content.isEmpty) return;
                Navigator.of(dialogContext).pop();
                await controller.createAndUpload(
                  title: title,
                  mediaType: 'text/plain',
                  bytes: utf8.encode(content),
                );
              },
              child: Text(L10nKey.vaultCreateUpload.tr),
            ),
          ],
        );
      },
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.onCreate});

  final VoidCallback onCreate;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          const Text(
            'Vault',
            style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w800),
          ),
          const Spacer(),
          FilledButton.icon(
            onPressed: onCreate,
            icon: const Icon(Icons.add, size: 18),
            label: Text(L10nKey.vaultNewDoc.tr),
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        L10nKey.vaultEmpty.tr,
        style: const TextStyle(color: Color(0xFF94A3B8)),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});

  final String message;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(message, style: const TextStyle(color: Color(0xFFF87171))),
          const SizedBox(height: 12),
          TextButton(onPressed: onRetry, child: Text(L10nKey.commonRetry.tr)),
        ],
      ),
    );
  }
}

String _stateLabel(VaultDocumentState state) {
  switch (state) {
    case VaultDocumentState.draft:
      return L10nKey.vaultStateDraft.tr;
    case VaultDocumentState.queued:
      return L10nKey.vaultStateQueued.tr;
    case VaultDocumentState.validating:
      return L10nKey.vaultStateValidating.tr;
    case VaultDocumentState.converting:
      return L10nKey.vaultStateConverting.tr;
    case VaultDocumentState.reviewPending:
      return L10nKey.vaultStateReviewPending.tr;
    case VaultDocumentState.published:
      return L10nKey.vaultStatePublished.tr;
    case VaultDocumentState.rejected:
      return L10nKey.vaultStateRejected.tr;
    case VaultDocumentState.failed:
      return L10nKey.vaultStateFailed.tr;
    case VaultDocumentState.archived:
      return L10nKey.vaultStateArchived.tr;
    case VaultDocumentState.purgePending:
      return L10nKey.vaultStatePurgePending.tr;
    case VaultDocumentState.purged:
      return L10nKey.vaultStatePurged.tr;
    case VaultDocumentState.unknown:
      return L10nKey.vaultStateUnknown.tr;
  }
}

Color _stateColor(VaultDocumentState state) {
  switch (state) {
    case VaultDocumentState.published:
      return const Color(0xFF34D399);
    case VaultDocumentState.rejected:
    case VaultDocumentState.failed:
      return const Color(0xFFF87171);
    case VaultDocumentState.archived:
    case VaultDocumentState.purgePending:
    case VaultDocumentState.purged:
      return const Color(0xFF94A3B8);
    default:
      return const Color(0xFF38BDF8);
  }
}

class _DocumentCard extends StatelessWidget {
  const _DocumentCard({required this.document});

  final VaultDocument document;

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<VaultController>();

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0B1220),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF1E293B)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  document.title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: _stateColor(document.state).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  _stateLabel(document.state),
                  style: TextStyle(
                    color: _stateColor(document.state),
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          if (document.canReview || document.canPublish || document.canManage) ...[
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              children: [
                if (document.canReview && document.state == VaultDocumentState.reviewPending)
                  OutlinedButton(
                    onPressed: () => controller.reviewDocument(
                      document.documentId,
                      reason: 'Rejected from Vault UI',
                    ),
                    child: const Text('Từ chối'),
                  ),
                if (document.canPublish && document.state == VaultDocumentState.reviewPending)
                  FilledButton(
                    onPressed: () => controller.publishDocument(
                      document.documentId,
                      reason: 'Approved from Vault UI',
                    ),
                    child: const Text('Xuất bản'),
                  ),
                if (document.canManage &&
                    document.state != VaultDocumentState.archived &&
                    document.state != VaultDocumentState.purged &&
                    document.state != VaultDocumentState.purgePending)
                  TextButton(
                    onPressed: () => controller.archiveDocument(document.documentId),
                    child: const Text('Lưu trữ'),
                  ),
                if (document.canManage && document.state == VaultDocumentState.archived)
                  TextButton(
                    onPressed: () => controller.purgeDocument(document.documentId),
                    child: const Text('Xoá vĩnh viễn'),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
