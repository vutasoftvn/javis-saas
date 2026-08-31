import 'dart:convert';
import '../../../core/network/api_exception.dart';
import '../../../core/services/secure_storage_service.dart';
import '../models/strategy_list_result.dart';

export '../../../core/network/api_exception.dart';
export '../../../core/network/api_response_decoder.dart';

/// Lỗi từ Strategy API
class StrategyApiException extends ApiException {
  StrategyApiException(int statusCode, String message) : super(message, statusCode);
}

/// Base class for strategy domain services — shared helpers
abstract class StrategyServiceBase {
  Future<String?> getWorkspaceId() async {
    return SecureStorageService.read('workspace_id');
  }

  Future<String> requireWorkspaceId() async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      throw StrategyApiException(0, 'Chưa xác định workspace hiện tại');
    }
    return workspaceId;
  }

  dynamic decode(dynamic response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      return jsonDecode(response.body);
    }
    String detail = 'Yêu cầu thất bại (${response.statusCode})';
    try {
      final body = jsonDecode(response.body);
      if (body is Map && body['detail'] != null) {
        final d = body['detail'];
        detail = d is String ? d : jsonEncode(d);
      }
    } catch (_) {
      // giữ nguyên detail mặc định nếu body không phải JSON hợp lệ
    }
    throw StrategyApiException(response.statusCode, detail);
  }

  StrategyListResult<Map<String, dynamic>> decodeList(
    dynamic response,
    String key, {
    bool optionalOn404 = false,
  }) {
    if (response.statusCode == 404) {
      if (optionalOn404) return const StrategyListResult.unavailable();
      return StrategyListResult.failure('Không tìm thấy dữ liệu (404)');
    }
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return const StrategyListResult.success([]);
      try {
        final data = jsonDecode(response.body);
        if (data is Map && data[key] is List) {
          final items = (data[key] as List)
              .map((e) => e is Map<String, dynamic> ? e : Map<String, dynamic>.from(e as Map))
              .toList();
          return StrategyListResult.success(items);
        }
        return const StrategyListResult.failure('Phản hồi không đúng định dạng mong đợi');
      } catch (_) {
        return const StrategyListResult.failure('Không thể đọc dữ liệu phản hồi từ máy chủ');
      }
    }
    String detail = 'Yêu cầu thất bại (${response.statusCode})';
    try {
      final body = jsonDecode(response.body);
      if (body is Map && body['detail'] != null) {
        final d = body['detail'];
        detail = d is String ? d : jsonEncode(d);
      }
    } catch (_) {
      // giữ nguyên detail mặc định nếu body không phải JSON hợp lệ
    }
    return StrategyListResult.failure(detail);
  }
}
