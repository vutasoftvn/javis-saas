import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../models/strategy_workflow_models.dart';
import '../services/strategy_workflow_service.dart';

class CycleReviewTimeline extends StatefulWidget {
  final String cycleId;
  final int? cycleDurationWeeks;
  final StrategyWorkflowService? workflowService;
  final void Function(CycleReviewModel review)? onReviewClosed;

  const CycleReviewTimeline({
    super.key,
    required this.cycleId,
    this.cycleDurationWeeks,
    this.workflowService,
    this.onReviewClosed,
  });

  @override
  State<CycleReviewTimeline> createState() => _CycleReviewTimelineState();
}

class _CycleReviewTimelineState extends State<CycleReviewTimeline> {
  late final StrategyWorkflowService _service;
  List<CycleReviewModel> _reviews = [];
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _service = widget.workflowService ?? StrategyWorkflowService();
    _loadReviews();
  }

  @override
  void didUpdateWidget(covariant CycleReviewTimeline oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.cycleId != widget.cycleId) {
      _loadReviews();
    }
  }

  Future<void> _loadReviews() async {
    if (widget.cycleId.isEmpty) return;
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final items = await _service.listCycleReviews(widget.cycleId);
      if (mounted) {
        setState(() {
          _reviews = items;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _startReview(CycleReviewModel review) async {
    setState(() => _isLoading = true);
    try {
      final updated = await _service.startCycleReview(review.id);
      setState(() {
        _reviews = _reviews.map((r) => r.id == review.id ? updated : r).toList();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _closeReview(CycleReviewModel review, String conclusion) async {
    setState(() => _isLoading = true);
    try {
      final closed = await _service.closeCycleReview(
        review.id,
        conclusion: conclusion,
      );
      setState(() {
        _reviews = _reviews.map((r) => r.id == review.id ? closed : r).toList();
        _isLoading = false;
      });
      widget.onReviewClosed?.call(closed);
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  void _showCloseDialog(CycleReviewModel review) {
    final conclusionCtrl = TextEditingController(text: review.conclusion ?? '');
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceDark,
        title: Text(
          'Đóng Đánh Giá ${review.kind.displayNameVi} (Tuần ${review.scheduledWeekNo})',
          style: const TextStyle(color: Colors.white, fontSize: 16),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Xác nhận hoàn thành phiên đánh giá và chốt quyết định quản trị chu kỳ:',
              style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
            ),
            const SizedBox(height: 12),
            TextField(
              key: const ValueKey('review_conclusion_input'),
              controller: conclusionCtrl,
              maxLines: 3,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: const InputDecoration(
                labelText: 'Kết luận đánh giá *',
                hintText: 'Nhập đánh giá tiến độ OKR, rủi ro PESTEL và quyết định tiếp theo',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Hủy'),
          ),
          ElevatedButton(
            key: const ValueKey('confirm_close_review_button'),
            onPressed: () {
              Navigator.of(ctx).pop();
              _closeReview(review, conclusionCtrl.text.trim());
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary, foregroundColor: Colors.black),
            child: const Text('Chốt & Đóng Review'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Sort reviews by scheduledWeekNo then kind
    final sortedReviews = List<CycleReviewModel>.from(_reviews)
      ..sort((a, b) {
        final weekComp = a.scheduledWeekNo.compareTo(b.scheduledWeekNo);
        if (weekComp != 0) return weekComp;
        return a.kind.index.compareTo(b.kind.index);
      });

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const Icon(Icons.timeline_rounded, color: AppTheme.primary, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Tiến Trình Đánh Giá Chu Kỳ (Cycle Review Timeline)',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
                    Text(
                      'Lịch đánh giá tự động: Tuần, Giữa chu kỳ (Mid-cycle) và Cuối chu kỳ (End-cycle)${widget.cycleDurationWeeks != null ? " · Chu kỳ ${widget.cycleDurationWeeks} tuần" : ""}',
                      style: const TextStyle(fontSize: 12, color: AppTheme.textMutedDark),
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.refresh, size: 18, color: Colors.white70),
                onPressed: _loadReviews,
                tooltip: 'Tải lại tiến trình',
              ),
            ],
          ),

          if (_errorMessage != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.red.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.red.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline, color: Colors.red, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(_errorMessage!, style: const TextStyle(color: Colors.red, fontSize: 12)),
                  ),
                ],
              ),
            ),
          ],

          const SizedBox(height: 16),

          if (_isLoading && _reviews.isEmpty)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: CircularProgressIndicator(color: AppTheme.primary),
              ),
            )
          else if (sortedReviews.isEmpty)
            Container(
              padding: const EdgeInsets.all(20),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.02),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.borderDark.withValues(alpha: 0.5)),
              ),
              child: const Text(
                'Chưa có phiên đánh giá nào được lập lịch cho chu kỳ này.',
                style: TextStyle(color: AppTheme.textMutedDark, fontSize: 13),
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: sortedReviews.length,
              separatorBuilder: (_, _) => const SizedBox(height: 10),
              itemBuilder: (ctx, idx) => _buildReviewCard(sortedReviews[idx]),
            ),
        ],
      ),
    );
  }

  Widget _buildReviewCard(CycleReviewModel review) {
    final isMidCycle = review.kind == CycleReviewKind.midCycle;
    final isEndCycle = review.kind == CycleReviewKind.endCycle;

    Color kindColor;
    IconData kindIcon;
    if (isEndCycle) {
      kindColor = const Color(0xFFA855F7); // Purple
      kindIcon = Icons.flag_rounded;
    } else if (isMidCycle) {
      kindColor = const Color(0xFFF59E0B); // Amber
      kindIcon = Icons.wb_twilight_rounded;
    } else {
      kindColor = const Color(0xFF38BDF8); // Sky blue
      kindIcon = Icons.calendar_view_week_rounded;
    }

    Color statusColor;
    String statusText;
    switch (review.status) {
      case CycleReviewStatus.scheduled:
        statusColor = Colors.blueGrey;
        statusText = 'ĐÃ LÊN LỊCH';
        break;
      case CycleReviewStatus.inProgress:
        statusColor = const Color(0xFFF59E0B);
        statusText = 'ĐANG TIẾN HÀNH';
        break;
      case CycleReviewStatus.completed:
        statusColor = const Color(0xFF10B981);
        statusText = 'HOÀN THÀNH';
        break;
      case CycleReviewStatus.superseded:
        statusColor = Colors.grey;
        statusText = 'THAY THẾ';
        break;
      case CycleReviewStatus.skipped:
        statusColor = Colors.redAccent;
        statusText = 'BỎ QUA';
        break;
      case CycleReviewStatus.unknown:
        statusColor = Colors.grey;
        statusText = 'KHÔNG RÕ';
        break;
    }

    return Container(
      key: ValueKey('review_card_${review.id}'),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDarkLighter,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isMidCycle || isEndCycle
              ? kindColor.withValues(alpha: 0.5)
              : AppTheme.borderDark,
          width: isMidCycle || isEndCycle ? 1.5 : 1.0,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              // Kind Icon & Chip
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: kindColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: kindColor),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(kindIcon, size: 14, color: kindColor),
                    const SizedBox(width: 6),
                    Text(
                      review.kind.displayNameVi,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: kindColor,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              // Scheduled Week
              Text(
                'Tuần ${review.scheduledWeekNo}',
                key: ValueKey('review_week_${review.id}'),
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
              const Spacer(),
              // Status Badge
              Container(
                key: ValueKey('review_status_${review.id}'),
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: statusColor),
                ),
                child: Text(
                  statusText,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: statusColor,
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 8),

          // Policy Revision & Decision Record Link
          Wrap(
            spacing: 12,
            runSpacing: 6,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.policy_outlined, size: 13, color: AppTheme.textMutedDark),
                  const SizedBox(width: 4),
                  Text(
                    'Chính sách rev: ${review.settingsRevision ?? review.revision}',
                    key: ValueKey('review_policy_revision_${review.id}'),
                    style: const TextStyle(fontSize: 11, color: AppTheme.textMutedDark),
                  ),
                ],
              ),
              if (review.decisionId != null)
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.link_rounded, size: 13, color: AppTheme.primary),
                    const SizedBox(width: 4),
                    Text(
                      'Biên bản quyết định #${review.decisionId}',
                      key: ValueKey('review_decision_link_${review.id}'),
                      style: const TextStyle(fontSize: 11, color: AppTheme.primary),
                    ),
                  ],
                ),
              if (review.conductedAt != null)
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.check_rounded, size: 13, color: Colors.green),
                    const SizedBox(width: 4),
                    Text(
                      'Thực hiện: ${review.conductedAt}',
                      style: const TextStyle(fontSize: 11, color: Colors.green),
                    ),
                  ],
                ),
            ],
          ),

          if (review.conclusion != null && review.conclusion!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.03),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.notes_rounded, size: 14, color: Colors.white60),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Kết luận: ${review.conclusion}',
                      style: const TextStyle(fontSize: 12, color: Colors.white70),
                    ),
                  ),
                ],
              ),
            ),
          ],

          // Action Buttons: Gated STRICTLY by review.can* flags, NEVER role == 'founder'
          if (review.status != CycleReviewStatus.completed &&
              review.status != CycleReviewStatus.superseded) ...[
            const SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                if (review.status == CycleReviewStatus.scheduled && review.canStart)
                  ElevatedButton.icon(
                    key: ValueKey('start_review_button_${review.id}'),
                    onPressed: () => _startReview(review),
                    icon: const Icon(Icons.play_arrow_rounded, size: 15),
                    label: const Text('Bắt đầu review'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: kindColor,
                      foregroundColor: Colors.black,
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                  ),
                if (review.status == CycleReviewStatus.inProgress && review.canClose) ...[
                  const SizedBox(width: 8),
                  ElevatedButton.icon(
                    key: ValueKey('close_review_button_${review.id}'),
                    onPressed: () => _showCloseDialog(review),
                    icon: const Icon(Icons.check_circle_outline, size: 15),
                    label: const Text('Đóng & Duyệt review'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF10B981),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ],
            ),
          ],
        ],
      ),
    );
  }
}
