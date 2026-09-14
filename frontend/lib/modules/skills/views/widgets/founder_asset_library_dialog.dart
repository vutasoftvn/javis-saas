import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../controllers/skill_registry_controller.dart';
import '../../models/founder_asset.dart';

/// Founder-configurable asset library — clone-only trên built-in
/// Role/Agent/Skill/Workflow, publish version mới immutable (docs/superpowers/
/// specs/2026-09-13-founder-configurable-agent-skill-workflow-design.md).
/// Built-in KHÔNG có nút sửa/xoá ở đây — chỉ Clone tạo draft mới, và Publish
/// cho draft đã evaluate xong.
class FounderAssetLibraryDialog extends StatefulWidget {
  const FounderAssetLibraryDialog({super.key});

  static void show(BuildContext context) {
    showDialog(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.75),
      builder: (context) => const FounderAssetLibraryDialog(),
    );
  }

  @override
  State<FounderAssetLibraryDialog> createState() => _FounderAssetLibraryDialogState();
}

class _FounderAssetLibraryDialogState extends State<FounderAssetLibraryDialog> {
  late final SkillRegistryController _controller;

  @override
  void initState() {
    super.initState();
    _controller = Get.find<SkillRegistryController>();
    _controller.loadFounderAssetLibrary();
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: const Color(0xFF090E1B),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: Colors.white.withValues(alpha: 0.08)),
      ),
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      child: Container(
        width: 680,
        height: 560,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.inventory_2_outlined, color: Color(0xFFA78BFA), size: 22),
                const SizedBox(width: 10),
                const Expanded(
                  child: Text(
                    'Kho Asset Founder (Workspace)',
                    style: TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w700),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Color(0xFF64748B), size: 20),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: 4),
            const Text(
              'Clone một asset built-in thành draft riêng của workspace, rồi publish '
              'thành version mới (immutable) sau khi evaluate đạt. Built-in không '
              'bao giờ bị sửa/xoá trực tiếp.',
              style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12, height: 1.4),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFFA78BFA),
                side: BorderSide(color: const Color(0xFFA78BFA).withValues(alpha: 0.5)),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              icon: const Icon(Icons.copy_all_outlined, size: 16),
              label: const Text('Clone một built-in Skill', style: TextStyle(fontSize: 12)),
              onPressed: () => _showCloneDialog(context),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: Obx(() {
                if (_controller.isLoadingFounderAssets.value) {
                  return const Center(child: CircularProgressIndicator());
                }
                final items = _controller.founderAssetLibrary;
                if (items.isEmpty) {
                  return const Center(
                    child: Text(
                      'Workspace chưa clone asset nào.',
                      style: TextStyle(color: Color(0xFF64748B), fontSize: 13),
                    ),
                  );
                }
                return ListView.separated(
                  itemCount: items.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 8),
                  itemBuilder: (context, index) => _buildLibraryRow(context, items[index]),
                );
              }),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLibraryRow(BuildContext context, FounderAssetLibraryItem item) {
    Color lifecycleColor = const Color(0xFF94A3B8);
    if (item.lifecycle == 'PUBLISHED') lifecycleColor = const Color(0xFF10B981);
    if (item.lifecycle == 'DRAFT' || item.lifecycle == 'PENDING') {
      lifecycleColor = const Color(0xFFF59E0B);
    }

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF131B2E),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      item.assetId,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        fontFamily: 'monospace',
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: lifecycleColor.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        item.lifecycle,
                        style: TextStyle(color: lifecycleColor, fontSize: 10, fontWeight: FontWeight.w700),
                      ),
                    ),
                  ],
                ),
                if (item.originAssetId != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    'Clone từ: ${item.originAssetId}',
                    style: const TextStyle(color: Color(0xFF64748B), fontSize: 11),
                  ),
                ],
              ],
            ),
          ),
          if (item.definitionHash != null && item.version != null && !item.isPublished)
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFF10B981),
                side: BorderSide(color: const Color(0xFF10B981).withValues(alpha: 0.5)),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              icon: const Icon(Icons.rocket_launch_outlined, size: 14),
              label: const Text('Publish', style: TextStyle(fontSize: 11)),
              onPressed: () => _controller.publishFounderAsset(
                assetKind: item.assetKind,
                assetId: item.assetId,
                version: item.version!,
                expectedHash: item.definitionHash!,
                reason: 'Publish từ Kho Asset Founder console',
              ),
            ),
        ],
      ),
    );
  }

  void _showCloneDialog(BuildContext context) {
    final assetIdController = TextEditingController();
    final versionController = TextEditingController(text: '1');
    showDialog(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: const Color(0xFF090E1B),
        title: const Text('Clone built-in Skill', style: TextStyle(color: Colors.white, fontSize: 15)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: assetIdController,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(
                labelText: 'Built-in asset id (vd: skill.sales.discovery_call)',
                labelStyle: TextStyle(color: Color(0xFF64748B)),
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: versionController,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(
                labelText: 'Version',
                labelStyle: TextStyle(color: Color(0xFF64748B)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Huỷ'),
          ),
          ElevatedButton(
            onPressed: () {
              final sourceAssetId = assetIdController.text.trim();
              if (sourceAssetId.isEmpty) return;
              _controller.cloneFounderAsset(
                assetKind: FounderAssetKind.skill,
                sourceAssetId: sourceAssetId,
                sourceVersion: versionController.text.trim().isEmpty
                    ? null
                    : versionController.text.trim(),
                reason: 'Clone qua Kho Asset Founder console',
              );
              Navigator.of(dialogContext).pop();
            },
            child: const Text('Clone'),
          ),
        ],
      ),
    );
  }
}
