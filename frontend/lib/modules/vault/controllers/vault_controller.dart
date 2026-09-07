import 'package:get/get.dart';
import '../../../core/network/api_result.dart';
import '../../../core/widgets/app_toast.dart';
import '../models/vault_document.dart';
import '../services/vault_service.dart';

/// Task 12 (plan local-first-enterprise-knowledge) — Vault giờ có backend
/// thật (Task 7-11: local upload ticket, review/publish, archive/purge, tất
/// cả authorization-filtered). Controller CHỈ hiển thị những gì backend trả
/// — không suy diễn document/quyền nào ngoài response thật.
class VaultController extends GetxController {
  final VaultService _service;

  VaultController({VaultService? service}) : _service = service ?? VaultService();

  final documents = <VaultDocument>[].obs;
  final isLoading = false.obs;
  final isUploading = false.obs;
  final errorMessage = Rxn<String>();

  @override
  void onInit() {
    super.onInit();
    loadDocuments();
  }

  Future<void> loadDocuments() async {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      final result = await _service.listDocuments();
      switch (result) {
        case ApiSuccess(data: final data):
          documents.value = data;
        case ApiFailure(failure: final f):
          errorMessage.value = f.message;
      }
    } finally {
      isLoading.value = false;
    }
  }

  /// Toàn bộ flow create → upload → complete. Trả `true` nếu QUEUED thành
  /// công. Lỗi ở bất kỳ bước nào đều dừng ngay, không âm thầm bỏ qua bước
  /// còn lại (vd. upload fail thì KHÔNG gọi complete — sẽ tạo attempt
  /// QUEUED trỏ tới nội dung chưa từng ghi).
  Future<bool> createAndUpload({
    required String title,
    required String mediaType,
    required List<int> bytes,
    String? classification,
    String? visibility,
  }) async {
    isUploading.value = true;
    try {
      final createResult = await _service.createDocument(
        title: title,
        mediaType: mediaType,
        classification: classification,
        visibility: visibility,
      );
      final VaultDocumentUpload upload;
      switch (createResult) {
        case ApiSuccess(data: final data):
          upload = data;
        case ApiFailure(failure: final f):
          AppToast.error('Không tạo được document: ${f.message}');
          return false;
      }

      final uploaded = await _service.uploadContent(upload.uploadUrl, bytes);
      if (!uploaded) {
        AppToast.error('Upload nội dung thất bại');
        return false;
      }

      final completeResult = await _service.completeUpload(upload.uploadId);
      switch (completeResult) {
        case ApiSuccess():
          await loadDocuments();
          return true;
        case ApiFailure(failure: final f):
          AppToast.error('Không hoàn tất upload: ${f.message}');
          return false;
      }
    } finally {
      isUploading.value = false;
    }
  }

  Future<void> reviewDocument(String documentId, {required String reason}) async {
    final result = await _service.reviewDocument(
      documentId,
      reason: reason,
      idempotencyKey: 'review-$documentId-${DateTime.now().microsecondsSinceEpoch}',
    );
    await _handleActionResult(result, documentId, successMessage: 'Đã từ chối tài liệu');
  }

  Future<void> publishDocument(String documentId, {required String reason}) async {
    final result = await _service.publishDocument(
      documentId,
      reason: reason,
      idempotencyKey: 'publish-$documentId-${DateTime.now().microsecondsSinceEpoch}',
    );
    await _handleActionResult(result, documentId, successMessage: 'Đã xuất bản tài liệu');
  }

  Future<void> archiveDocument(String documentId) async {
    final result = await _service.archiveDocument(documentId);
    await _handleActionResult(result, documentId, successMessage: 'Đã lưu trữ tài liệu');
  }

  Future<void> purgeDocument(String documentId) async {
    final result = await _service.purgeDocument(documentId);
    await _handleActionResult(result, documentId, successMessage: 'Đã yêu cầu xoá vĩnh viễn');
  }

  /// Task 12 Step 4 — 403/404 (quyền vừa bị thu hồi/document không còn thấy
  /// được) LÀM MỚI list thay vì giữ nguyên nội dung cũ có thể đã sai lệch.
  Future<void> _handleActionResult(
    ApiResult<dynamic> result,
    String documentId, {
    required String successMessage,
  }) async {
    switch (result) {
      case ApiSuccess():
        AppToast.success(successMessage);
        await loadDocuments();
      case ApiFailure(failure: final f):
        if (f.statusCode == 403 || f.statusCode == 404) {
          await loadDocuments();
        } else {
          AppToast.error(f.message);
        }
    }
  }
}
