import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:get/get.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../controllers/vault_controller.dart';

class VaultDocumentDetailView extends StatelessWidget {
  final VaultController controller;

  const VaultDocumentDetailView({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    final docPath = controller.selectedDocumentPath.value ?? '';
    final folder = controller.getFolderName(docPath);
    final fileName = controller.getFileName(docPath);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Navigation Header Bar
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          decoration: const BoxDecoration(
            color: Color(0xFF070C18),
            border: Border(bottom: BorderSide(color: Color(0xFF1E293B), width: 1)),
          ),
          child: Row(
            children: [
              Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: controller.backToFolderList,
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0F172A),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFF1E293B)),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.arrow_back_rounded, size: 15, color: Color(0xFF00F0FF)),
                        SizedBox(width: 6),
                        Text(
                          'Quay lại thư mục',
                          style: TextStyle(color: Color(0xFFE2E8F0), fontSize: 12, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 14),

              // Breadcrumbs
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      InkWell(
                        onTap: () => controller.selectFolder('all'),
                        child: const Text('Vault', style: TextStyle(color: Color(0xFF64748B), fontSize: 13, fontWeight: FontWeight.w600)),
                      ),
                      const Padding(padding: EdgeInsets.symmetric(horizontal: 6), child: Icon(Icons.chevron_right_rounded, size: 14, color: Color(0xFF475569))),
                      if (folder != 'root') ...[
                        InkWell(
                          onTap: () => controller.selectFolder(folder),
                          child: Text(folder, style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 13, fontWeight: FontWeight.w600)),
                        ),
                        const Padding(padding: EdgeInsets.symmetric(horizontal: 6), child: Icon(Icons.chevron_right_rounded, size: 14, color: Color(0xFF475569))),
                      ],
                      Text(fileName, style: const TextStyle(color: Colors.white, fontSize: 13.5, fontWeight: FontWeight.w700)),
                    ],
                  ),
                ),
              ),

              // Copy Markdown Button
              InkWell(
                onTap: () {
                  final content = controller.selectedDocumentContent.value ?? '';
                  if (content.isNotEmpty) {
                    Clipboard.setData(ClipboardData(text: content));
                    Get.snackbar(
                      'Đã sao chép',
                      'Nội dung Markdown đã được chép vào Clipboard',
                      backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.2),
                      colorText: const Color(0xFF10B981),
                      duration: const Duration(seconds: 2),
                    );
                  }
                },
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(color: const Color(0xFF0F172A), borderRadius: BorderRadius.circular(8), border: Border.all(color: const Color(0xFF1E293B))),
                  child: const Row(
                    children: [
                      Icon(Icons.copy_all_rounded, size: 15, color: Color(0xFF94A3B8)),
                      SizedBox(width: 5),
                      Text('Sao chép', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12, fontWeight: FontWeight.w600)),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 8),

              // Edit / Save Button
              Obx(() {
                final isEditing = controller.isEditing.value;
                return InkWell(
                  onTap: () => isEditing ? controller.saveDocument() : controller.toggleEdit(),
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      gradient: isEditing ? const LinearGradient(colors: [Color(0xFF059669), Color(0xFF10B981)]) : null,
                      color: isEditing ? null : const Color(0xFF0284C7).withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: isEditing ? const Color(0xFF10B981) : const Color(0xFF38BDF8), width: 1),
                    ),
                    child: Row(
                      children: [
                        Icon(isEditing ? Icons.save_rounded : Icons.edit_rounded, size: 15, color: Colors.white),
                        const SizedBox(width: 5),
                        Text(isEditing ? 'Lưu' : 'Chỉnh sửa', style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w700)),
                      ],
                    ),
                  ),
                );
              }),
            ],
          ),
        ),

        // Document Content Body
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 28),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 960),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Obx(() {
                      if (controller.isEditing.value) {
                        return Container(
                          decoration: BoxDecoration(
                            color: const Color(0xFF080D1A),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: const Color(0xFF1E293B)),
                          ),
                          padding: const EdgeInsets.all(20),
                          child: TextField(
                            controller: controller.textController,
                            maxLines: null,
                            style: const TextStyle(fontSize: 14.5, height: 1.65, fontFamily: 'monospace', color: Color(0xFFE2E8F0)),
                            decoration: const InputDecoration(border: InputBorder.none, hintText: 'Nhập nội dung Markdown...', hintStyle: TextStyle(color: Color(0xFF64748B))),
                          ),
                        );
                      }

                      final rawContent = controller.selectedDocumentContent.value ?? '';
                      if (rawContent.isEmpty) {
                        return const Center(
                          child: Padding(padding: EdgeInsets.symmetric(vertical: 40), child: Text('Tài liệu rỗng', style: TextStyle(color: Color(0xFF64748B), fontStyle: FontStyle.italic))),
                        );
                      }

                      return MarkdownBody(
                        data: rawContent,
                        selectable: true,
                        onTapLink: (text, href, title) {
                          if (href != null) {
                            if (href.startsWith('http://') || href.startsWith('https://')) {
                              final uri = Uri.tryParse(href);
                              if (uri != null) launchUrl(uri, mode: LaunchMode.externalApplication);
                            } else {
                              controller.openDocument(href);
                            }
                          }
                        },
                        styleSheet: MarkdownStyleSheet(
                          h1: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w800, height: 1.4, letterSpacing: -0.5),
                          h1Padding: const EdgeInsets.only(top: 10, bottom: 16),
                          h2: const TextStyle(color: Color(0xFF38BDF8), fontSize: 17.5, fontWeight: FontWeight.w700, height: 1.4),
                          h2Padding: const EdgeInsets.only(top: 20, bottom: 10),
                          h3: const TextStyle(color: Color(0xFFF1F5F9), fontSize: 15, fontWeight: FontWeight.w600, height: 1.4),
                          h3Padding: const EdgeInsets.only(top: 14, bottom: 8),
                          p: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 14.5, height: 1.65),
                          pPadding: const EdgeInsets.only(bottom: 12),
                          strong: const TextStyle(color: Color(0xFFF8FAFC), fontWeight: FontWeight.w700),
                          em: const TextStyle(color: Color(0xFF94A3B8), fontStyle: FontStyle.italic),
                          code: const TextStyle(color: Color(0xFF38BDF8), backgroundColor: Color(0xFF1E293B), fontFamily: 'monospace', fontSize: 13),
                          codeblockDecoration: BoxDecoration(color: const Color(0xFF080D1A), borderRadius: BorderRadius.circular(8), border: Border.all(color: const Color(0xFF1E293B))),
                          codeblockPadding: const EdgeInsets.all(14),
                          blockquote: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 14, height: 1.5, fontStyle: FontStyle.italic),
                          blockquoteDecoration: BoxDecoration(color: const Color(0xFF00F0FF).withValues(alpha: 0.05), borderRadius: BorderRadius.circular(6), border: const Border(left: BorderSide(color: Color(0xFF00F0FF), width: 3.5))),
                          blockquotePadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                          listBullet: const TextStyle(color: Color(0xFF00F0FF), fontSize: 15, fontWeight: FontWeight.bold),
                          tableHead: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13.5),
                          tableBody: const TextStyle(color: Color(0xFFCBD5E1), fontSize: 13.5),
                          tableBorder: TableBorder.all(color: const Color(0xFF1E293B), width: 1),
                          tableCellsPadding: const EdgeInsets.all(10),
                        ),
                      );
                    }),
                    const SizedBox(height: 32),
                    const Divider(color: Color(0xFF1E293B)),
                    const SizedBox(height: 16),

                    // Backlinks
                    _buildBacklinksSection(),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildBacklinksSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.hub_rounded, size: 16, color: Color(0xFF00F0FF)),
            SizedBox(width: 8),
            Text(
              'Liên kết hai chiều (Obsidian Wikilinks [[...]])',
              style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, color: Color(0xFF38BDF8)),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Obx(() {
          if (controller.backlinks.isEmpty) {
            return const Text(
              'Chưa có tài liệu nào liên kết ngược tới file này qua cú pháp [[...]]',
              style: TextStyle(fontSize: 12.5, color: Color(0xFF64748B), fontStyle: FontStyle.italic),
            );
          }
          return Wrap(
            spacing: 8,
            runSpacing: 8,
            children: controller.backlinks.map((link) {
              final title = link['source_title'] as String? ?? 'Tài liệu liên quan';
              final type = link['source_type'] as String? ?? 'note';
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(color: const Color(0xFF0B1220), borderRadius: BorderRadius.circular(8), border: Border.all(color: const Color(0xFF1E293B))),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.link_rounded, size: 14, color: Color(0xFF00F0FF)),
                    const SizedBox(width: 8),
                    Text(title, style: const TextStyle(fontSize: 12.5, color: Colors.white, fontWeight: FontWeight.w600)),
                    const SizedBox(width: 8),
                    Text(type.toUpperCase(), style: const TextStyle(fontSize: 9.5, color: Color(0xFF64748B), fontWeight: FontWeight.bold)),
                  ],
                ),
              );
            }).toList(),
          );
        }),
      ],
    );
  }
}
