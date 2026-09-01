import 'package:flutter/foundation.dart';

/// Trạng thái khả dụng của tính năng Vault (Lưu trữ tri thức).
///
/// Release này CHƯA có object storage, pipeline scan/ingest hay embedding/
/// retrieval thật ở backend (xem `apps/cosa/api/vault_routes.py`, các route
/// legacy trả 501). Vì vậy `unavailable` là giá trị DUY NHẤT được phát hành —
/// không dựng full state machine (loading/populated/error...) cho một tính
/// năng chưa tồn tại, tránh gợi ý sai rằng có dữ liệu thật phía sau.
enum VaultAvailability { unavailable, available }

@immutable
class VaultFeatureState {
  const VaultFeatureState.unavailable(this.message) : availability = VaultAvailability.unavailable;

  final VaultAvailability availability;
  final String message;
}
