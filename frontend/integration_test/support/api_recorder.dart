// Task 11 — bằng chứng release cần "real evidence", không phải chỉ mock unit
// test: `ApiRecorder` bọc một `http.Client` THẬT (đi qua socket loopback tới
// `FixtureServer`, xem `fixture_server.dart`) và chỉ QUAN SÁT request thật đã
// được gửi đi — không tự chế response, không thay thế hành vi ApiClient/
// MvpRequestClient. Việc này cho phép các test integration khẳng định đúng
// tuyên bố cốt lõi của kế hoạch: sau khi chuyển workspace, KHÔNG còn request
// nào rò rỉ header `X-Workspace-Id` của tenant trước đó; khi runtime offline,
// KHÔNG có request mutation (POST/PUT/PATCH/DELETE) nào từng được gửi ra
// ngoài — không suy diễn qua UI text, đo trực tiếp trên wire.
library;

import 'package:http/http.dart' as http;

/// Một request đã thực sự được gửi ra ngoài qua socket (không phải suy đoán
/// từ trạng thái UI).
class RecordedRequest {
  RecordedRequest({
    required this.method,
    required this.uri,
    required this.headers,
  });

  final String method;
  final Uri uri;
  final Map<String, String> headers;
}

/// Các path bootstrap identity/session KHÔNG mang `X-Workspace-Id` (một số
/// gọi trước khi có workspace context, vd. `/platform/auth/sessions`,
/// `/identity/sync-from-platform` — cả hai đều `requiresAuth: false`) và
/// không phải là "business mutation" theo nghĩa plan này (chúng không ghi dữ
/// liệu nghiệp vụ của workspace nào cả) — loại trừ khỏi `businessPosts` để
/// assertion "không gửi mutation nghiệp vụ nào" không bị nhiễu bởi các bước
/// đăng nhập hợp lệ luôn phải xảy ra trước đó.
const _bootstrapPaths = <String>{
  '/platform/auth/sessions',
  '/identity/sync-from-platform',
};

class ApiRecorder {
  final List<RecordedRequest> requests = [];

  void clear() => requests.clear();

  /// Mọi giá trị header `X-Workspace-Id` đã thực sự đi kèm một request nào đó
  /// — dùng để khẳng định request SAU khi switch workspace-b không còn giá
  /// trị nào của workspace-a lẫn vào (brief Task 11 §2: "everyElement").
  List<String> get workspaceHeaders => requests
      .where((r) => r.headers.containsKey('X-Workspace-Id'))
      .map((r) => r.headers['X-Workspace-Id']!)
      .toList(growable: false);

  /// Mọi request có khả năng ghi dữ liệu nghiệp vụ (không phải GET, không
  /// phải bootstrap identity) — nếu danh sách này rỗng sau một thao tác bị
  /// gate chặn (vd. tap nút Approve khi offline) tức là gate đã chặn ĐÚNG
  /// TRƯỚC KHI có bất kỳ I/O nào ra ngoài, không chỉ chặn ở tầng hiển thị.
  List<RecordedRequest> get businessPosts => requests
      .where((r) => r.method != 'GET' && !_bootstrapPaths.contains(r.uri.path))
      .toList(growable: false);

  void _record(http.BaseRequest request) {
    requests.add(
      RecordedRequest(
        method: request.method,
        uri: request.url,
        headers: Map<String, String>.of(request.headers),
      ),
    );
  }

  /// Bọc [inner] (client thật, mặc định `http.Client()` gửi qua socket loopback
  /// tới `FixtureServer`) — ghi lại request TRƯỚC khi forward, không sửa đổi
  /// request/response.
  http.Client wrap(http.Client inner) => _RecordingClient(inner, this);
}

class _RecordingClient extends http.BaseClient {
  _RecordingClient(this._inner, this._recorder);

  final http.Client _inner;
  final ApiRecorder _recorder;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) {
    _recorder._record(request);
    return _inner.send(request);
  }

  @override
  void close() => _inner.close();
}
