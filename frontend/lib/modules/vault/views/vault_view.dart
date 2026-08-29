import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../controllers/vault_controller.dart';
import 'widgets/vault_folder_tree_sidebar.dart';
import 'widgets/vault_files_content_view.dart';
import 'widgets/vault_document_detail_view.dart';

class VaultView extends GetView<VaultController> {
  const VaultView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<VaultController>()) {
      Get.put(VaultController());
    }

    return Container(
      color: const Color(0xFF040711),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. Sidebar Thư mục
          VaultFolderTreeSidebar(controller: controller),

          // 2. Nội dung chính: Chi tiết tài liệu hoặc Danh sách file
          Expanded(
            child: Obx(() {
              if (controller.isViewingDocumentDetail) {
                return VaultDocumentDetailView(controller: controller);
              } else {
                return VaultFilesContentView(controller: controller);
              }
            }),
          ),
        ],
      ),
    );
  }
}
