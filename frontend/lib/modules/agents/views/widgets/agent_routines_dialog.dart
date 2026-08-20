import 'package:flutter/material.dart';
import '../../../../modules/agents/services/agent_platform_service.dart';

class AgentRoutinesDialog extends StatefulWidget {
  const AgentRoutinesDialog({super.key});

  @override
  State<AgentRoutinesDialog> createState() => _AgentRoutinesDialogState();
}

class _AgentRoutinesDialogState extends State<AgentRoutinesDialog> {
  final AgentPlatformService _service = AgentPlatformService();
  bool _isLoading = true;
  List<Map<String, dynamic>> _routines = [];
  List<Map<String, dynamic>> _heartbeats = [];
  String? _triggeringKey;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    final rList = await _service.listRoutines();
    final hList = await _service.listHeartbeats();
    setState(() {
      _routines = rList;
      _heartbeats = hList;
      _isLoading = false;
    });
  }

  Future<void> _triggerRoutine(String key) async {
    setState(() => _triggeringKey = key);
    final res = await _service.triggerRoutine(key);
    setState(() => _triggeringKey = null);

    if (mounted) {
      if (res != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Kích hoạt quy trình "$key" thành công!'),
            backgroundColor: const Color(0xFF10B981),
          ),
        );
        _loadData();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Lỗi khi kích hoạt quy trình "$key"'),
            backgroundColor: const Color(0xFFEF4444),
          ),
        );
      }
    }
  }

  Future<void> _runStalledWatchdog() async {
    final res = await _service.checkStalledRuns(timeoutMinutes: 10);
    if (mounted && res != null) {
      final count = res['recovered_count'] ?? 0;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Watchdog: Đã kiểm tra và xử lý $count phiên chạy bị treo.'),
          backgroundColor: Colors.blueAccent,
        ),
      );
      _loadData();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: const Color(0xFF0F172A),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        width: 840,
        height: 640,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.tealAccent.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.alarm_on_rounded, color: Colors.tealAccent, size: 22),
                ),
                const SizedBox(width: 14),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'COSA Autonomous Routines & Heartbeat Monitor',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Colors.white),
                      ),
                      Text(
                        'Quy trình tự động theo lịch 12-Week Year và giám sát nhịp tim Agent',
                        style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: 'Chạy Stalled Run Watchdog',
                  onPressed: _runStalledWatchdog,
                  icon: const Icon(Icons.shield_outlined, color: Colors.amber),
                ),
                const SizedBox(width: 6),
                IconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.close_rounded, color: Colors.grey),
                ),
              ],
            ),

            const SizedBox(height: 18),

            // Content
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator(color: Colors.tealAccent))
                  : DefaultTabController(
                      length: 2,
                      child: Column(
                        children: [
                          const TabBar(
                            tabs: [
                              Tab(text: 'Danh mục Routines'),
                              Tab(text: 'Trạng thái Heartbeats'),
                            ],
                            labelColor: Colors.tealAccent,
                            unselectedLabelColor: Colors.grey,
                            indicatorColor: Colors.tealAccent,
                          ),
                          const SizedBox(height: 14),
                          Expanded(
                            child: TabBarView(
                              children: [
                                // Tab 1: Routines
                                _buildRoutinesTab(),
                                // Tab 2: Heartbeats
                                _buildHeartbeatsTab(),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRoutinesTab() {
    if (_routines.isEmpty) {
      return Center(
        child: Text('Không có routine nào được đăng ký.', style: TextStyle(color: Colors.grey.shade500)),
      );
    }

    return ListView.separated(
      itemCount: _routines.length,
      separatorBuilder: (context, index) => const SizedBox(height: 10),
      itemBuilder: (ctx, i) {
        final r = _routines[i];
        final key = r['key'] ?? '';
        final name = r['name'] ?? key;
        final cron = r['cron_expression'] ?? 'Schedule';
        final agent = r['target_agent_key'] ?? 'Agent';
        final isRunning = _triggeringKey == key;

        return Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: const Color(0xFF334155)),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.tealAccent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.schedule_rounded, color: Colors.tealAccent, size: 20),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      name,
                      style: const TextStyle(color: Colors.white, fontSize: 13.5, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Cron: $cron | Phụ trách: $agent',
                      style: TextStyle(color: Colors.grey.shade400, fontSize: 11.5),
                    ),
                  ],
                ),
              ),
              ElevatedButton.icon(
                onPressed: isRunning ? null : () => _triggerRoutine(key),
                icon: isRunning
                    ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.bolt_rounded, size: 16, color: Colors.white),
                label: Text(isRunning ? 'Đang chạy...' : 'Chạy ngay', style: const TextStyle(color: Colors.white, fontSize: 12)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0D9488),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildHeartbeatsTab() {
    if (_heartbeats.isEmpty) {
      return Center(
        child: Text('Chưa có dữ liệu nhịp tim của Agent.', style: TextStyle(color: Colors.grey.shade500)),
      );
    }

    return ListView.separated(
      itemCount: _heartbeats.length,
      separatorBuilder: (context, index) => const SizedBox(height: 10),
      itemBuilder: (ctx, i) {
        final hb = _heartbeats[i];
        final agent = hb['agent_key'] ?? 'Agent';
        final status = hb['status'] ?? 'HEALTHY';
        final activeRuns = hb['active_runs_count'] ?? 0;
        final isHealthy = status == 'HEALTHY';

        return Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: const Color(0xFF334155)),
          ),
          child: Row(
            children: [
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  color: isHealthy ? const Color(0xFF10B981) : Colors.amber,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  agent,
                  style: const TextStyle(color: Colors.white, fontSize: 13.5, fontWeight: FontWeight.w700),
                ),
              ),
              Text(
                'Active Runs: $activeRuns',
                style: TextStyle(color: Colors.grey.shade400, fontSize: 12),
              ),
              const SizedBox(width: 14),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: (isHealthy ? const Color(0xFF10B981) : Colors.amber).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  status,
                  style: TextStyle(
                    color: isHealthy ? const Color(0xFF10B981) : Colors.amber,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
