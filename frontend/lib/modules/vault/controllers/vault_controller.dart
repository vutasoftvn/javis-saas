import 'package:get/get.dart';
import '../models/vault_feature_state.dart';

/// Task 5 (Truthful MVP Hardening) — Vault trước đây gọi các route
/// `/vault/*` legacy và hiển thị document/knowledge/backlink GIẢ (không có
/// storage/indexing/retrieval thật phía sau). Controller này KHÔNG còn gọi
/// bất kỳ API nào, không giữ document list, không có edit/save/promote — chỉ
/// công khai lý do tính năng chưa khả dụng.
class VaultController extends GetxController {
  static const VaultFeatureState _unavailableState = VaultFeatureState.unavailable(
    'Vault (Lưu trữ tri thức) hiện chưa khả dụng. Kho lưu trữ tài liệu, lập '
    'chỉ mục và truy xuất tri thức thật vẫn đang được xây dựng — mọi hành vi '
    '"đã lưu trữ" trước đây trong bản dựng này chỉ là giả lập.',
  );

  final VaultFeatureState featureState = _unavailableState;
}
