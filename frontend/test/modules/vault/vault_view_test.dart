import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';

import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/vault/controllers/vault_controller.dart';
import 'package:frontend/modules/vault/models/vault_document.dart';
import 'package:frontend/modules/vault/services/vault_service.dart';
import 'package:frontend/modules/vault/views/vault_view.dart';

/// Task 12 (plan local-first-enterprise-knowledge) — Vault giờ có backend
/// thật (Task 7-11); UI render CHÍNH XÁC những gì backend đã lọc theo
/// authorization trả về, không tự thêm/bớt document hay action nào.
class _FakeVaultService implements VaultService {
  List<VaultDocument> documents = const [];
  ApiFailureDetail? listFailure;

  @override
  Future<ApiResult<List<VaultDocument>>> listDocuments() async {
    if (listFailure != null) return ApiFailure(listFailure!);
    return ApiSuccess(
      data: documents,
      meta: ApiResponseMeta(dataState: ApiDataState.populated, observedAt: DateTime.now()),
    );
  }

  @override
  Future<ApiResult<VaultDocument>> getDocument(String documentId) => throw UnimplementedError();

  @override
  Future<ApiResult<VaultDocumentUpload>> createDocument({
    required String title,
    required String mediaType,
    String? classification,
    String? visibility,
  }) =>
      throw UnimplementedError();

  @override
  Future<bool> uploadContent(String uploadUrl, List<int> bytes) => throw UnimplementedError();

  @override
  Future<ApiResult<VaultUploadStatus>> completeUpload(String uploadId) =>
      throw UnimplementedError();

  @override
  Future<ApiResult<VaultUploadStatus>> reviewDocument(
    String documentId, {
    required String reason,
    required String idempotencyKey,
  }) =>
      throw UnimplementedError();

  @override
  Future<ApiResult<VaultUploadStatus>> publishDocument(
    String documentId, {
    required String reason,
    required String idempotencyKey,
  }) =>
      throw UnimplementedError();

  @override
  Future<ApiResult<VaultArchiveOrPurgeResult>> archiveDocument(String documentId) =>
      throw UnimplementedError();

  @override
  Future<ApiResult<VaultArchiveOrPurgeResult>> purgeDocument(String documentId) =>
      throw UnimplementedError();
}

VaultDocument _doc({
  required String id,
  required String title,
  VaultDocumentState state = VaultDocumentState.published,
  bool canManage = false,
  bool canReview = false,
  bool canPublish = false,
}) {
  return VaultDocument(
    documentId: id,
    workspaceId: 'ws_1001',
    title: title,
    kind: 'document',
    state: state,
    createdBy: 'user_1',
    createdAt: DateTime(2026, 9, 1),
    updatedAt: DateTime(2026, 9, 1),
    canReview: canReview,
    canPublish: canPublish,
    canManage: canManage,
  );
}

void main() {
  tearDown(() {
    Get.delete<VaultController>(force: true);
  });

  testWidgets('member sees only documents returned by the authorized backend', (tester) async {
    final memberDocument = _doc(id: 'doc_member', title: 'My private note');
    final fakeService = _FakeVaultService()..documents = [memberDocument];
    Get.put<VaultController>(VaultController(service: fakeService));

    await tester.pumpWidget(const MaterialApp(home: VaultView()));
    await tester.pumpAndSettle();

    expect(find.text('Board plan'), findsNothing);
    expect(find.text(memberDocument.title), findsOneWidget);
  });

  testWidgets('empty list shows empty state, not a fabricated document', (tester) async {
    final fakeService = _FakeVaultService()..documents = [];
    Get.put<VaultController>(VaultController(service: fakeService));

    await tester.pumpWidget(const MaterialApp(home: VaultView()));
    await tester.pumpAndSettle();

    expect(find.textContaining('Chưa có tài liệu'), findsOneWidget);
  });

  testWidgets('backend failure shows error state with retry, not stale/fake content', (tester) async {
    final fakeService = _FakeVaultService()
      ..listFailure = const ApiFailureDetail(code: ApiFailureCode.unavailable, message: 'boom');
    Get.put<VaultController>(VaultController(service: fakeService));

    await tester.pumpWidget(const MaterialApp(home: VaultView()));
    await tester.pumpAndSettle();

    expect(find.text('boom'), findsOneWidget);
    expect(find.text('Thử lại'), findsOneWidget);
  });

  testWidgets('review/publish controls render only when backend grants them', (tester) async {
    final reviewable = _doc(
      id: 'doc_1',
      title: 'Pending doc',
      state: VaultDocumentState.reviewPending,
      canReview: true,
      canPublish: true,
    );
    final readOnly = _doc(
      id: 'doc_2',
      title: 'Read only doc',
      state: VaultDocumentState.reviewPending,
    );
    final fakeService = _FakeVaultService()..documents = [reviewable, readOnly];
    Get.put<VaultController>(VaultController(service: fakeService));

    await tester.pumpWidget(const MaterialApp(home: VaultView()));
    await tester.pumpAndSettle();

    expect(find.text('Xuất bản'), findsOneWidget);
    expect(find.text('Từ chối'), findsOneWidget);
  });

  testWidgets('archived document offers purge, not archive, when manage granted', (tester) async {
    final archived = _doc(
      id: 'doc_3',
      title: 'Archived doc',
      state: VaultDocumentState.archived,
      canManage: true,
    );
    final fakeService = _FakeVaultService()..documents = [archived];
    Get.put<VaultController>(VaultController(service: fakeService));

    await tester.pumpWidget(const MaterialApp(home: VaultView()));
    await tester.pumpAndSettle();

    expect(find.text('Xoá vĩnh viễn'), findsOneWidget);
    expect(find.text('Lưu trữ'), findsNothing);
  });
}
