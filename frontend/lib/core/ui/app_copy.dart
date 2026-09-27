/// Task 10 — nơi tập trung copy tiếng Việt hướng tới người dùng cho các màn
/// hình ĐÃ được migrate bởi plan "Frontend Trust and UX Hardening" (Hub,
/// Skill Registry). Đây KHÔNG phải một sweep toàn app — chỉ những chuỗi văn
/// bản thuộc các view mà task này thực sự chạm vào mới được đưa vào đây,
/// đúng tinh thần "migrate pages actually touched" của brief Task 10.
///
/// Quy tắc: KHÔNG đặt mã lỗi backend/system (vd. HTTP status, exception
/// class, correlation id) vào các chuỗi ở đây — người dùng chỉ thấy thông
/// điệp thân thiện; correlation id để trace lỗi phải log riêng qua
/// `debugPrint`/logger, không hiển thị trên UI (xem cách `AppToast.error`
/// trong `founder_command_center_controller.dart` đã tách log kỹ thuật khỏi
/// message hiển thị).
library;

import 'package:get/get.dart';

class AppCopy {
  AppCopy._();

  // ── Skill Registry — compact filter sheet (Task 10) ─────────────────────
  static String get skillRegistryFilterTooltip =>
      Get.locale?.languageCode == 'en' ? 'Filters' : 'Bộ lọc';
  static String get skillRegistryFilterSheetTitle =>
      Get.locale?.languageCode == 'en' ? 'Filter Skills' : 'Lọc kỹ năng';
  static String get skillRegistryFilterStatusSection =>
      Get.locale?.languageCode == 'en' ? 'Lifecycle Status' : 'Trạng thái vòng đời';
  static String get skillRegistryFilterDomainSection =>
      Get.locale?.languageCode == 'en' ? 'Domain' : 'Lĩnh vực';
  static String get skillRegistryFilterCloseButton =>
      Get.locale?.languageCode == 'en' ? 'Close' : 'Đóng';

  // ── Hub — dockable chat panel (Task 10, commit 2) ────────────────────────
  static String get hubChatPanelTitle =>
      Get.locale?.languageCode == 'en'
          ? 'Collaborate with COSA Co-Founder'
          : 'Trao đổi cùng COSA Co-Founder';
  static String get hubChatEmptyState =>
      Get.locale?.languageCode == 'en'
          ? 'Ask COSA about business progress, debate assumptions, or assign Missions!'
          : 'Hãy hỏi COSA về tiến độ kinh doanh, phản biện giả định hoặc giao Mission!';
  static String get hubChatInputHint =>
      Get.locale?.languageCode == 'en'
          ? 'Enter message for Co-Founder...'
          : 'Nhập tin nhắn trao đổi với Co-Founder...';
  static String get hubChatNewChatTooltip =>
      Get.locale?.languageCode == 'en'
          ? 'New Chat'
          : 'Tạo mới chat';

  // Thẻ duyệt hành động agent ngay trong chat (spec 2026-09-27-chat-business-actions).
  static String get hubApprovalHeading =>
      Get.locale?.languageCode == 'en'
          ? 'Co-Founder asks for your approval'
          : 'Co-Founder xin bạn duyệt';
  static String get hubApprovalApprove =>
      Get.locale?.languageCode == 'en' ? 'Approve' : 'Duyệt';
  static String get hubApprovalReject =>
      Get.locale?.languageCode == 'en' ? 'Reject' : 'Từ chối';
  static String get hubApprovalApproved =>
      Get.locale?.languageCode == 'en' ? 'Approved' : 'Đã duyệt';
  static String get hubApprovalRejected =>
      Get.locale?.languageCode == 'en' ? 'Rejected' : 'Đã từ chối';
  static String get hubApprovalExpired =>
      Get.locale?.languageCode == 'en' ? 'Expired' : 'Hết hạn';
  static String get hubApprovalFailed =>
      Get.locale?.languageCode == 'en'
          ? 'Could not record your decision. Please try again.'
          : 'Chưa ghi nhận được quyết định. Vui lòng thử lại.';

  // ── Hub — card vận hành 4 tab (spec 2026-09-27-hub-operations-workspace-design) ──
  static String _l(String en, String vi) => Get.locale?.languageCode == 'en' ? en : vi;

  static String get hubOpsTitle => _l('Project operations', 'Vận hành dự án');
  static String get hubOpsTabTasks => _l('Tasks', 'Tasks');
  static String get hubOpsTabSchedules => _l('Schedules', 'Lịch');
  static String get hubOpsTabTools => _l('Tools', 'Công cụ');
  static String get hubOpsTabAgents => _l('Agents', 'Agent');
  static String get hubOpsViewAll => _l('View all', 'Xem tất cả');
  static String get hubOpsRetry => _l('Retry', 'Thử lại');
  static String get hubOpsLoadFailed =>
      _l('Could not load this tab. Please try again.', 'Chưa tải được dữ liệu. Vui lòng thử lại.');
  static String get hubOpsActionFailed =>
      _l('The action did not go through. Please try again.', 'Thao tác chưa thành công. Vui lòng thử lại.');
  static String get hubOpsCancel => _l('Cancel', 'Huỷ');

  static String get hubOpsFilterMine => _l('Mine', 'Của tôi');
  static String get hubOpsFilterAgent => _l('Agent', 'Agent');
  static String get hubOpsFilterAll => _l('All', 'Tất cả');
  static String get hubOpsNoTasks => _l('No tasks yet.', 'Chưa có task nào.');
  static String get hubOpsAgentDraft => _l('Drafted by agent', 'Nháp do agent');
  static String get hubOpsAgentCreated => _l('Created by agent', 'Do agent tạo');
  static String get hubOpsChangeStatus => _l('Change status', 'Đổi trạng thái');
  static String hubOpsTaskStatus(String status) {
    switch (status.toLowerCase()) {
      case 'draft':
        return _l('Draft', 'Nháp');
      case 'todo':
        return _l('To do', 'Cần làm');
      case 'in_progress':
        return _l('In progress', 'Đang làm');
      case 'done':
        return _l('Done', 'Hoàn thành');
      case 'blocked':
        return _l('Blocked', 'Bị chặn');
      default:
        return _l('Other', 'Khác');
    }
  }

  static String get hubOpsNoSchedules =>
      _l('No background schedules for this project.', 'Dự án chưa có lịch chạy nền.');
  static String get hubOpsScheduleEnabled => _l('On', 'Đang bật');
  static String get hubOpsSchedulePaused => _l('Paused', 'Tạm dừng');
  static String get hubOpsRunNow => _l('Run now', 'Chạy ngay');
  static String get hubOpsPause => _l('Pause', 'Tạm dừng');
  static String get hubOpsResume => _l('Resume', 'Tiếp tục');
  static String get hubOpsArchive => _l('Archive', 'Lưu trữ');
  static String get hubOpsArchiveConfirmTitle => _l('Archive this schedule?', 'Lưu trữ lịch này?');
  static String get hubOpsArchiveConfirmBody => _l(
        'It stops for good and cannot be reopened. Run history is kept.',
        'Lịch sẽ dừng hẳn và không mở lại được. Lịch sử chạy vẫn được giữ.',
      );
  static String hubOpsDaily(String time) => _l('Daily at $time', 'Hằng ngày lúc $time');
  static String hubOpsWeekdays(String time) => _l('Weekdays at $time', 'Ngày thường lúc $time');
  static String hubOpsOnce(String when) => _l('Once, $when', 'Một lần, $when');
  static String get hubOpsNeverRun => _l('Not run yet', 'Chưa chạy lần nào');
  static String hubOpsLastRun(String state, String when) =>
      _l('Last run: $state ($when)', 'Lần chạy gần nhất: $state ($when)');
  static String hubOpsExecutionState(String state) {
    switch (state) {
      case 'queued':
      case 'enqueue_retry':
        return _l('queued', 'đang chờ');
      case 'running':
        return _l('running', 'đang chạy');
      case 'succeeded':
        return _l('succeeded', 'thành công');
      case 'blocked_reauth':
        return _l('needs reconnect', 'cần kết nối lại');
      case 'cancelled':
        return _l('cancelled', 'đã huỷ');
      case 'failed':
      case 'enqueue_failed':
        return _l('failed', 'thất bại');
      default:
        return _l('other', 'khác');
    }
  }

  static String get hubOpsConnectorsHeading =>
      _l('Connections (whole organization)', 'Kết nối (toàn tổ chức)');
  static String get hubOpsManageConnectors => _l('Manage', 'Quản lý');
  static String get hubOpsNoConnectors => _l('No connections yet.', 'Chưa có kết nối nào.');
  static String hubOpsConnectorState(String state) {
    switch (state) {
      case 'enabled':
        return _l('Connected', 'Đã kết nối');
      case 'expired':
        return _l('Needs reconnect', 'Cần kết nối lại');
      case 'revoked':
        return _l('Revoked', 'Đã thu hồi');
      case 'unavailable':
        return _l('Unavailable', 'Không khả dụng');
      default:
        return _l('Not connected', 'Chưa kết nối');
    }
  }

  static String hubOpsConnectorName(String key) {
    switch (key) {
      case 'email-read':
        return _l('Email (read)', 'Email (đọc)');
      case 'calendar-read':
        return _l('Calendar (read)', 'Lịch làm việc (đọc)');
      case 'customer-channel-read':
        return _l('Customer channels (read)', 'Kênh khách hàng (đọc)');
      case 'cas':
        return _l('Bank account (read)', 'Tài khoản ngân hàng (đọc)');
      case 'sandbox-read':
        return _l('Sandbox data (read)', 'Dữ liệu thử (đọc)');
      default:
        return _l('Other connection', 'Kết nối khác');
    }
  }

  static String get hubOpsGrantsHeading =>
      _l('What agents may do in this project', 'Agent được phép làm gì trong dự án');
  static String get hubOpsNoGrants =>
      _l('No agent permissions in this project.', 'Chưa có agent nào được cấp quyền trong dự án.');
  static String get hubOpsWorkspaceScope => _l('whole organization', 'toàn tổ chức');
  static String get hubOpsRevoke => _l('Revoke', 'Thu hồi');
  static String get hubOpsRevokeConfirmTitle => _l('Revoke this permission?', 'Thu hồi quyền này?');
  static String get hubOpsRevokeConfirmBody => _l(
        'The agent can no longer do this in the project, effective immediately.',
        'Agent sẽ không làm được việc này trong dự án nữa, có hiệu lực ngay.',
      );
  static String get hubOpsRevokeReason => _l('Revoked by founder from the hub', 'Founder thu hồi ở hub');
  static String hubOpsRecentlyRevoked(int n) =>
      _l('$n permission(s) revoked recently', 'Đã thu hồi gần đây: $n quyền');

  static String get hubOpsNoAgents => _l('No agents in this project.', 'Dự án chưa có agent nào.');
  static String get hubOpsAgentActive => _l('Active', 'Đang hoạt động');
  static String get hubOpsAgentPaused => _l('Paused', 'Tạm dừng');
  static String get hubOpsAgentTemplate => _l('Not activated', 'Chưa kích hoạt');
  static String get hubOpsAgentRetired => _l('Retired', 'Ngừng dùng');
  static String get hubOpsAgentNotReady => _l('Not available yet', 'Chưa sẵn sàng');
  static String get hubOpsActivate => _l('Activate', 'Kích hoạt');
  static String hubOpsPinnedVersion(String v) => _l('Version $v', 'Phiên bản $v');
  static String get hubOpsUpdateAvailable => _l(
        'A newer version exists. Pause and activate again to update.',
        'Có phiên bản mới — tạm dừng rồi kích hoạt lại để cập nhật.',
      );
  static String get hubOpsDefaultAgent => _l('Agent', 'Agent');
}

