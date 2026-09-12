import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../localization/locale_controller.dart';
import '../localization/supported_locale.dart';
import '../theme/app_theme.dart';

enum ToastType {
  success,
  error,
  warning,
  info,
}

/// Shared Toast Notification Component (COSA Design System)
/// Displays a sleek glassmorphic toast notification at the Top-Right corner.
class AppToast {
  /// Test hook to allow verifying toast UI rendering in widget tests.
  static bool allowInTest = false;

  static bool get isEnglish {
    if (Get.isRegistered<LocaleController>()) {
      return Get.find<LocaleController>().current.value == SupportedLocale.enUS;
    }
    return Get.locale?.languageCode == 'en';
  }

  static void success(
    String message, {
    String? title,
    Duration? duration = const Duration(seconds: 4),
    VoidCallback? onTap,
  }) {
    show(
      message: message,
      title: title ?? (isEnglish ? 'Success' : 'Thành công'),
      type: ToastType.success,
      duration: duration,
      onTap: onTap,
    );
  }

  static void error(
    String message, {
    String? title,
    Duration? duration = const Duration(seconds: 5),
    VoidCallback? onTap,
  }) {
    show(
      message: message,
      title: title ?? (isEnglish ? 'Error' : 'Đã có lỗi xảy ra'),
      type: ToastType.error,
      duration: duration,
      onTap: onTap,
    );
  }

  static void warning(
    String message, {
    String? title,
    Duration? duration = const Duration(seconds: 4),
    VoidCallback? onTap,
  }) {
    show(
      message: message,
      title: title ?? (isEnglish ? 'Warning' : 'Cảnh báo'),
      type: ToastType.warning,
      duration: duration,
      onTap: onTap,
    );
  }

  static void info(
    String message, {
    String? title,
    Duration? duration = const Duration(seconds: 4),
    VoidCallback? onTap,
  }) {
    show(
      message: message,
      title: title ?? (isEnglish ? 'Notice' : 'Thông báo'),
      type: ToastType.info,
      duration: duration,
      onTap: onTap,
    );
  }

  static void show({
    required String message,
    String? title,
    ToastType type = ToastType.info,
    Duration? duration = const Duration(seconds: 4),
    VoidCallback? onTap,
  }) {
    // Safety check if Get overlay context is not available (e.g. headless unit tests without UI)
    final isTestEnv = !allowInTest &&
        (Get.testMode ||
            (!kIsWeb && Platform.environment.containsKey('FLUTTER_TEST')) ||
            (Get.context == null && Get.overlayContext == null));
    if (isTestEnv) {
      debugPrint('[AppToast] [${type.name.toUpperCase()}] $title: $message');
      return;
    }

    try {
      final isEn = isEnglish;
      final resolvedTitle = isEn ? _translateTitle(title, type) : title;
      final resolvedMessage = isEn ? _translateMessage(message) : message;

      final Color accentColor = _getAccentColor(type);
      final IconData icon = _getIcon(type);

      double screenWidth = 400;
      final ctx = Get.context ?? Get.overlayContext;
      if (ctx != null) {
        screenWidth = MediaQuery.of(ctx).size.width;
      }

      const double toastWidth = 400.0;
      final double leftMargin = screenWidth > (toastWidth + 40)
          ? screenWidth - toastWidth - 20
          : 16.0;

      Get.rawSnackbar(
        snackPosition: SnackPosition.TOP,
        backgroundColor: Colors.transparent,
        margin: EdgeInsets.only(
          top: 16,
          right: 16,
          left: leftMargin,
          bottom: 0,
        ),
        padding: EdgeInsets.zero,
        duration: duration ?? const Duration(seconds: 4),
        isDismissible: true,
        messageText: _ToastWidget(
          title: resolvedTitle,
          message: resolvedMessage,
          accentColor: accentColor,
          icon: icon,
          isEn: isEn,
          onTap: onTap,
          onClose: () {
            if (Get.isSnackbarOpen) {
              Get.closeCurrentSnackbar();
            }
          },
        ),
      );
    } catch (e) {
      debugPrint('[AppToast] Error displaying toast: $e');
    }
  }

  static String? _translateTitle(String? title, ToastType type) {
    if (title == null || title.isEmpty) {
      switch (type) {
        case ToastType.success:
          return 'Success';
        case ToastType.error:
          return 'Error';
        case ToastType.warning:
          return 'Warning';
        case ToastType.info:
          return 'Notice';
      }
    }
    const titleMap = {
      'Thành công': 'Success',
      'Đã có lỗi xảy ra': 'Error',
      'Lỗi': 'Error',
      'Cảnh báo': 'Warning',
      'Thông báo': 'Notice',
      'Đã xoá': 'Deleted',
      'Đã xóa': 'Deleted',
      'Thất bại': 'Failed',
      'Thao tác thất bại': 'Action Failed',
      'Thiếu thông tin': 'Missing Information',
      'Không thể thực hiện': 'Action Failed',
      'Không thực hiện được': 'Action Failed',
      'Đã lưu': 'Saved',
      'Đã cập nhật': 'Updated',
      'Hoàn thành nghĩa vụ': 'Obligation Completed',
      'Chưa khả dụng': 'Feature Unavailable',
      'Đã chuyển Stage': 'Stage Transitioned',
      'Đã phê duyệt': 'Approved',
      'Đã từ chối': 'Rejected',
      'Đã gửi yêu cầu sửa': 'Revision Requested',
      'Đã chấp thuận': 'Approved',
      'Đã tạm đình chỉ': 'Suspended',
      'Đã phục hồi': 'Restored',
      'Đồng bộ thành công': 'Sync Successful',
      'Lỗi tạo kỹ năng': 'Skill Creation Error',
      'Lỗi đánh giá': 'Evaluation Error',
      'Lỗi đồng bộ': 'Sync Error',
      'Lỗi phân tích': 'Analysis Error',
      'Đã rà soát hợp đồng': 'Contract Reviewed',
      'Phê duyệt thất bại': 'Approval Failed',
      'Báo cáo thất bại': 'Report Failed',
      'Đã chốt quyết định': 'Decision Finalized',
      'Đã Tạo Cơ Hội Bán Hàng': 'Deal Created',
      'Đã Gửi Duyệt Outreach': 'Outreach Submitted for Approval',
      'Cập nhật Workforce Pack': 'Workforce Pack Updated',
      'Không thể tạo dự án': 'Cannot Create Project',
      'Chưa chọn dự án active': 'No Active Project Selected',
      'Hồ sơ chế độ kế toán': 'Accounting Regime Profile',
      'Chuyển đổi thành công': 'Conversion Successful',
      'Đánh giá hoàn tất': 'Evaluation Completed',
      'Không tải được chiến dịch': 'Cannot Load Campaign',
      'Không đánh giá được': 'Cannot Evaluate',
      'Không chạy được skill': 'Cannot Run Skill',
      'Đã hủy chứng từ': 'Voucher Cancelled',
      'Chúc mừng': 'Congratulations',
    };
    return titleMap[title] ?? title;
  }

  static String _translateMessage(String message) {
    if (_knownTranslations.containsKey(message)) {
      return _knownTranslations[message]!;
    }

    if (message.startsWith('Exception: ')) {
      return 'Exception: ${_translateMessage(message.substring('Exception: '.length))}';
    }

    final reqFailedRegex = RegExp(r'Yêu cầu thất bại \((\d+)\)');
    final match = reqFailedRegex.firstMatch(message);
    if (match != null) {
      return message.replaceAll(reqFailedRegex, 'Request failed (${match.group(1)})');
    }

    if (message.startsWith('Không tạo được document: ')) {
      return 'Could not create document: ${message.substring('Không tạo được document: '.length)}';
    }
    if (message.startsWith('Không hoàn tất upload: ')) {
      return 'Failed to complete upload: ${message.substring('Không hoàn tất upload: '.length)}';
    }
    if (message.startsWith('Không thể tạo chứng từ: ')) {
      return 'Cannot create voucher: ${message.substring('Không thể tạo chứng từ: '.length)}';
    }
    if (message.startsWith('Không thể hủy chứng từ: ')) {
      return 'Cannot cancel voucher: ${message.substring('Không thể hủy chứng từ: '.length)}';
    }
    if (message.startsWith('Lỗi khi chuyển trạng thái nghĩa vụ: ')) {
      return 'Error updating obligation status: ${message.substring('Lỗi khi chuyển trạng thái nghĩa vụ: '.length)}';
    }
    if (message.startsWith('Lỗi hoàn thành nghĩa vụ: ')) {
      return 'Error completing obligation: ${message.substring('Lỗi hoàn thành nghĩa vụ: '.length)}';
    }
    if (message.startsWith('Không thể duyệt yêu cầu: ')) {
      return 'Cannot approve request: ${message.substring('Không thể duyệt yêu cầu: '.length)}';
    }
    if (message.startsWith('Không thể từ chối yêu cầu: ')) {
      return 'Cannot reject request: ${message.substring('Không thể từ chối yêu cầu: '.length)}';
    }
    if (message.startsWith('Không thể đặt mục tiêu: ')) {
      return 'Cannot set goal: ${message.substring('Không thể đặt mục tiêu: '.length)}';
    }
    if (message.startsWith('Không đổi được cài đặt: ')) {
      return 'Cannot change settings: ${message.substring('Không đổi được cài đặt: '.length)}';
    }
    if (message.startsWith('Không thể bỏ kế hoạch: ')) {
      return 'Cannot discard plan: ${message.substring('Không thể bỏ kế hoạch: '.length)}';
    }
    if (message.startsWith('Lỗi: ')) {
      return 'Error: ${message.substring('Lỗi: '.length)}';
    }
    if (message.startsWith('Rà soát pháp lý tham khảo: ')) {
      return 'Reference legal review: ${message.substring('Rà soát pháp lý tham khảo: '.length)}';
    }

    final weekMatch = RegExp(r'^Đã tạo kế hoạch tuần (\d+)$').firstMatch(message);
    if (weekMatch != null) {
      return 'Created plan for Week ${weekMatch.group(1)}';
    }
    final portfolioMatch = RegExp(r'^Đã khởi tạo Portfolio "(.*)"$').firstMatch(message);
    if (portfolioMatch != null) {
      return 'Initialized Portfolio "${portfolioMatch.group(1)}"';
    }
    final cycleMatch = RegExp(r'^Đã khởi tạo chu kỳ danh mục "(.*)"$').firstMatch(message);
    if (cycleMatch != null) {
      return 'Initialized portfolio cycle "${cycleMatch.group(1)}"';
    }
    final taskSavedMatch = RegExp(r'^Đã lưu nhiệm vụ từ (.*) vào danh sách tuần!$').firstMatch(message);
    if (taskSavedMatch != null) {
      return 'Saved task from ${taskSavedMatch.group(1)} to weekly backlog!';
    }
    final accountingPeriodMatch = RegExp(r'^Đã mở kỳ kế toán mới \((.*) đến (.*)\)$').firstMatch(message);
    if (accountingPeriodMatch != null) {
      return 'Opened new accounting period (${accountingPeriodMatch.group(1)} to ${accountingPeriodMatch.group(2)})';
    }
    final crmAddMatch = RegExp(r'^Đã thêm (.*) vào CRM\.$').firstMatch(message);
    if (crmAddMatch != null) {
      return 'Added ${crmAddMatch.group(1)} to CRM.';
    }
    final crmDealStageMatch = RegExp(r'^Cơ hội bán hàng đã được cập nhật sang (.*)\.$').firstMatch(message);
    if (crmDealStageMatch != null) {
      return 'Sales deal updated to ${crmDealStageMatch.group(1)}.';
    }
    final modeSetMatch = RegExp(r'^Đã thiết lập chế độ (.*)$').firstMatch(message);
    if (modeSetMatch != null) {
      return 'Configured ${modeSetMatch.group(1)} mode';
    }
    final periodStatusMatch = RegExp(r'^Trạng thái kỳ đã chuyển sang (.*)$').firstMatch(message);
    if (periodStatusMatch != null) {
      return 'Period status changed to ${periodStatusMatch.group(1)}';
    }
    final attributionMatch = RegExp(r'^Đã tính toán phân bổ chuyển đổi \((.*)\)$').firstMatch(message);
    if (attributionMatch != null) {
      return 'Calculated conversion attribution (${attributionMatch.group(1)})';
    }
    final routineSuccessMatch = RegExp(r'^Kích hoạt quy trình "(.*)" thành công!$').firstMatch(message);
    if (routineSuccessMatch != null) {
      return 'Activated routine "${routineSuccessMatch.group(1)}" successfully!';
    }
    final routineErrorMatch = RegExp(r'^Lỗi khi kích hoạt quy trình "(.*)"$').firstMatch(message);
    if (routineErrorMatch != null) {
      return 'Error activating routine "${routineErrorMatch.group(1)}"';
    }
    final testScoreMatch = RegExp(r'^Điểm kiểm thử: (\d+)%$').firstMatch(message);
    if (testScoreMatch != null) {
      return 'Test score: ${testScoreMatch.group(1)}%';
    }

    return message;
  }

  static const Map<String, String> _knownTranslations = {
    'Vui lòng nhập tên giai đoạn': 'Please enter a stage name',
    'Đã hoàn tất khớp nối chính sách cho dự án.': 'Policy matching completed for project.',
    'Chưa thể lưu Tactic: tính năng này chưa khả dụng.': 'Unable to save Tactic: feature not yet available.',
    'Chưa thể cập nhật Tactic: tính năng này chưa khả dụng.': 'Unable to update Tactic: feature not yet available.',
    'Chưa thể tạo Weekly Review: tính năng này chưa khả dụng.': 'Unable to create Weekly Review: feature not yet available.',
    'Đã chuyển Stage dự án thành công!': 'Project stage transitioned successfully!',
    'Đã lưu review tuần': 'Weekly review saved',
    'Đã thêm Dự án Chiến lược': 'Strategic Project added',
    'Đã xoá Dự án Chiến lược': 'Strategic Project deleted',
    'Chưa có chu kỳ 12 tuần nào để biên dịch': 'No 12-week cycle to compile',
    'Chưa có chu kỳ 12 tuần nào để chuyển dịch': 'No 12-week cycle to transition',
    'Đã thêm dự án vào Portfolio': 'Project added to Portfolio',
    'Đã thêm điểm cộng hưởng': 'Synergy point added',
    'Đã xóa quan hệ cộng hưởng': 'Synergy relationship removed',
    'Đã ghi nhận phụ thuộc': 'Dependency recorded',
    'Đã xóa quan hệ phụ thuộc': 'Dependency removed',
    'Đã thêm Tùy Chọn Chiến Lược': 'Strategic Option added',
    'Đã cập nhật trạng thái tùy chọn': 'Option status updated',
    'Đã cập nhật cấu hình WIP Limit': 'WIP Limit configuration updated',
    'Kích hoạt Chu kỳ Portfolio 12WY thành công': '12WY Portfolio Cycle activated successfully',
    'Đã xếp hạng lại danh sách Next Best Actions': 'Next Best Actions re-ranked',
    'Đã cập nhật trạng thái': 'Status updated',
    'Đã cập nhật cấu hình Model Profile': 'Model Profile configuration updated',
    'Upload nội dung thất bại': 'Content upload failed',
    'Đã lưu hợp đồng cam kết chu kỳ 12 tuần': '12-week cycle commitment contract saved',
    'Đã thêm cam kết công việc': 'Work commitment added',
    'Đã lưu Weekly Mission': 'Weekly Mission saved',
    'Không thể ghi sổ chứng từ': 'Cannot post accounting voucher',
    'Nghĩa vụ đã chuyển sang trạng thái Đang thực hiện': 'Obligation moved to In Progress',
    'Không thể chuyển trạng thái nghĩa vụ': 'Unable to update obligation status',
    'Nghĩa vụ đã được đánh dấu hoàn thành': 'Obligation marked as completed',
    'Máy chủ từ chối ghi nhận hoàn thành': 'Server rejected completion status',
    'Đã tạo chu kỳ OKR mới': 'New OKR cycle created',
    'Đã thêm mục tiêu OKR': 'OKR objective added',
    'Đã xóa mục tiêu OKR': 'OKR objective deleted',
    'Đã thêm Kết quả Then chốt (Key Result)': 'Key Result added',
    'Đã cập nhật tiến độ Key Result': 'Key Result progress updated',
    'Đã xóa Key Result': 'Key Result deleted',
    'Đã phê duyệt hành động của agent': 'Agent action approved',
    'Vui lòng nhập tên chiến dịch': 'Please enter campaign name',
    'Đã kích hoạt chế độ nhà phát triển': 'Developer mode enabled',
    'Đã tắt chế độ nhà phát triển': 'Developer mode disabled',
    'Chưa xác định workspace hiện tại': 'Current workspace not identified',
    'Không tìm thấy dữ liệu (404)': 'Data not found (404)',
    'Phản hồi không đúng định dạng mong đợi': 'Response is not in expected format',
    'Không thể đọc dữ liệu phản hồi từ máy chủ': 'Cannot parse response data from server',
    'Đã sao chép vào bộ nhớ tạm': 'Copied to clipboard',
    'Thao tác thành công': 'Operation successful',
    'Đã lưu thay đổi': 'Changes saved',
    'Bản nháp đã nằm trên CEO Command Center.': 'Draft is now on CEO Command Center.',
    'Đã bỏ kế hoạch đề xuất.': 'Proposed plan discarded.',
    'Kỹ năng mới đã được đưa vào hàng đợi kiểm thử Candidate': 'New skill queued for Candidate testing',
    'Đã vô hiệu hóa gói mở rộng.': 'Extension pack disabled.',
    'Agent sẽ cập nhật lại nội dung theo chỉ dẫn': 'Agent will update content per instructions',
    'Cần nhập ít nhất quan sát và bài học': 'Observation and key lesson are required',
    'Trạng thái chiến dịch đã được cập nhật.': 'Campaign status updated.',
    'Lý do từ chối đã được ghi nhận.': 'Rejection reason recorded.',
    'Yêu cầu từ chối chưa được ghi nhận ở backend. Vui lòng thử lại.': 'Rejection request not acknowledged by backend. Please retry.',
    'Đã lưu nhiệm vụ vào kế hoạch tuần!': 'Task saved to weekly plan!',
    'Không tìm thấy phòng ban để tuyển dụng': 'Department for recruitment not found',
    'Cần nhập tiêu đề và nội dung': 'Title and content are required',
    'Lệnh đã được phê duyệt và đang tiếp tục thực thi': 'Order approved and execution resumed',
    'Bắt buộc đính kèm bằng chứng (evidence) để hoàn thành nghĩa vụ': 'Evidence attachment is required to complete obligation',
    'Đã định tuyến năng lực': 'Capability routed successfully',
    'Hành động cần người phê duyệt trước khi thực thi.': 'Action requires human approval before execution.',
    'Máy chủ từ chối yêu cầu tạm đình chỉ': 'Server rejected suspension request',
    'Máy chủ từ chối yêu cầu phục hồi (yêu cầu quyền Founder)': 'Server rejected restoration request (Founder role required)',
    'Không thể thực thi phiên chạy': 'Cannot execute run session',
    'Hệ thống AI đã chuyển sang trạng thái SUSPENDED': 'AI system has transitioned to SUSPENDED state',
    'Đã hoàn thành phiên chạy thử nghiệm': 'Test run session completed',
    'Đang thực thi thử nghiệm với Agent...': 'Executing test run with Agent...',
    'Mục tiêu tuần không được để trống.': 'Weekly goal cannot be empty.',
    'Đã ghi mục tiêu tuần. AI đang lập kế hoạch triển khai — kế hoạch sẽ hiện ở đây trong giây lát.': 'Weekly goal recorded. AI is compiling execution plan — it will appear shortly.',
    'Cần có đánh giá rủi ro (assessment) và thời hạn hợp lệ để phê duyệt': 'Risk assessment and valid deadline required for approval',
    'Triển khai này chưa có đánh giá rủi ro (assessment) hoặc hạn đánh giá hợp lệ': 'Deployment lacks risk assessment or valid evaluation deadline',
    'Cần nhập tên mục tiêu và chỉ số theo dõi': 'Objective name and metric tracking required',
    'Mã và tên chỉ số là bắt buộc': 'Metric code and name are required',
    'Cần nhập tên chiến dịch': 'Campaign name is required',
    'Chưa khả dụng': 'Feature unavailable',
    'Chuyển đổi thành công': 'Conversion successful',
    'Đánh giá hoàn tất': 'Evaluation completed',
    'Đã chốt quyết định': 'Decision finalized',
    'Đã Tạo Cơ Hội Bán Hàng': 'Deal created',
    'Đã Gửi Duyệt Outreach': 'Outreach submitted for approval',
    'Không thể tạo dự án': 'Cannot create project',
    'Chưa chọn dự án active': 'No active project selected',
    'Đã hủy chứng từ': 'Voucher cancelled',
    'Đã phê duyệt': 'Approved',
    'Đã từ chối': 'Rejected',
    'Đã gửi yêu cầu sửa': 'Revision requested',
    'Đã chấp thuận': 'Approved',
    'Đã tạm đình chỉ': 'Suspended',
    'Đã phục hồi': 'Restored',
    'Phê duyệt thất bại': 'Approval failed',
    'Báo cáo thất bại': 'Report failed',
    'Đồng bộ thành công': 'Sync successful',
    'Lỗi tạo kỹ năng': 'Skill creation error',
    'Lỗi đánh giá': 'Evaluation error',
    'Lỗi đồng bộ': 'Sync error',
    'Lỗi phân tích': 'Analysis error',
    'Đã rà soát hợp đồng': 'Contract reviewed',
  };

  static Color _getAccentColor(ToastType type) {
    switch (type) {
      case ToastType.success:
        return AppTheme.success;
      case ToastType.error:
        return AppTheme.error;
      case ToastType.warning:
        return AppTheme.warning;
      case ToastType.info:
        return AppTheme.info;
    }
  }

  static IconData _getIcon(ToastType type) {
    switch (type) {
      case ToastType.success:
        return Icons.check_circle_rounded;
      case ToastType.error:
        return Icons.error_rounded;
      case ToastType.warning:
        return Icons.warning_amber_rounded;
      case ToastType.info:
        return Icons.info_rounded;
    }
  }
}

class _ToastWidget extends StatelessWidget {
  final String? title;
  final String message;
  final Color accentColor;
  final IconData icon;
  final bool isEn;
  final VoidCallback? onTap;
  final VoidCallback onClose;

  const _ToastWidget({
    this.title,
    required this.message,
    required this.accentColor,
    required this.icon,
    this.isEn = false,
    this.onTap,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          decoration: BoxDecoration(
            color: AppTheme.surfaceDark.withValues(alpha: 0.95),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: accentColor.withValues(alpha: 0.35),
              width: 1.2,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.45),
                blurRadius: 16,
                offset: const Offset(0, 8),
              ),
              BoxShadow(
                color: accentColor.withValues(alpha: 0.12),
                blurRadius: 12,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Left Accent Indicator Bar
                  Container(
                    width: 4,
                    color: accentColor,
                  ),
                  const SizedBox(width: 12),

                  // Status Icon
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    child: Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: accentColor.withValues(alpha: 0.15),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        icon,
                        size: 20,
                        color: accentColor,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),

                  // Content (Title & Message)
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (title != null && title!.isNotEmpty) ...[
                            Text(
                              title!,
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                                color: AppTheme.textDark,
                                letterSpacing: 0.2,
                              ),
                            ),
                            const SizedBox(height: 3),
                          ],
                          Text(
                            message,
                            style: const TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w400,
                              color: AppTheme.textMutedDark,
                              height: 1.35,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  // Dismiss Button
                  Padding(
                    padding: const EdgeInsets.all(8),
                    child: IconButton(
                      icon: const Icon(
                        Icons.close_rounded,
                        size: 16,
                        color: AppTheme.textDimDark,
                      ),
                      splashRadius: 16,
                      tooltip: isEn ? 'Close' : 'Đóng',
                      onPressed: onClose,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
