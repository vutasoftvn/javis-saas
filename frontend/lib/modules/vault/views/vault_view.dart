import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/services/feature_flags_controller.dart';
import '../controllers/vault_controller.dart';

/// Task 5 (Truthful MVP Hardening) — Vault (Lưu trữ tri thức) chưa có storage/
/// indexing/retrieval thật ở backend. Màn hình này CHỈ công khai lý do chưa
/// khả dụng: KHÔNG gọi bất kỳ route `/vault/*` nào, không có nút chỉnh sửa,
/// lưu, phê duyệt hay truy xuất tri thức — tất cả affordance đó đã bị gỡ bỏ
/// cùng với `vault_folder_tree_sidebar.dart`, `vault_files_content_view.dart`,
/// `vault_document_detail_view.dart`, `vault_knowledge_studio_panel.dart`.
///
/// Điều kiện mở lại (xem `.superpowers/sdd/2026-09-01-truthful-mvp-hardening/
/// task-5-brief.md`): có E2E test thật upload byte, server verify MIME/size/
/// SHA-256, scan/ingestion qua structured state, retrieval trả chunk text +
/// citation, và cách ly workspace được chứng minh.
class VaultView extends GetView<VaultController> {
  const VaultView({super.key});

  /// Flag key khớp với `KNOWLEDGE_INGESTION_ENABLED` ở backend
  /// (`apps/cosa/knowledge_ingestion/contracts.py`) — canonical ingestion
  /// path tạm thời cho M3, KHÔNG phải Vault/retrieval thật.
  static const String _knowledgeIngestionFlagKey = 'knowledge_ingestion';
  static const String _knowledgeIngestionDocsPath = 'docs/features/knowledge.md';

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<VaultController>()) {
      Get.put(VaultController());
    }

    final knowledgeIngestionDocsEnabled = Get.isRegistered<FeatureFlagsController>() &&
        Get.find<FeatureFlagsController>().isEnabled(_knowledgeIngestionFlagKey);

    return Container(
      color: const Color(0xFF040711),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0B1220),
                    shape: BoxShape.circle,
                    border: Border.all(color: const Color(0xFF1E293B)),
                  ),
                  child: const Icon(
                    Icons.lock_clock_rounded,
                    size: 40,
                    color: Color(0xFF64748B),
                  ),
                ),
                const SizedBox(height: 20),
                const Text(
                  'Vault chưa khả dụng',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  controller.featureState.message,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Color(0xFF94A3B8),
                    fontSize: 13.5,
                    height: 1.55,
                  ),
                ),
                if (knowledgeIngestionDocsEnabled) ...[
                  const SizedBox(height: 20),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0B1220),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFF1E293B)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.description_outlined, size: 15, color: Color(0xFF38BDF8)),
                        const SizedBox(width: 8),
                        Flexible(
                          child: Text(
                            'Tài liệu Knowledge Ingestion (M3): $_knowledgeIngestionDocsPath',
                            style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 12, fontWeight: FontWeight.w600),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
