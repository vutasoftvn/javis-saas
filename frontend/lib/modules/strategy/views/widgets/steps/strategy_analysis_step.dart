import 'package:flutter/material.dart';
import 'package:frontend/core/theme/app_theme.dart';
import 'package:frontend/modules/strategy/models/strategy_workflow_models.dart';

class StrategyAnalysisStep extends StatefulWidget {
  final StrategicObjectiveModel selectedObjective;
  final List<BscFocusScopeModel> bscFocusScopes;
  final List<PestelSignalModel> pestelSignals;
  final List<ResourceCapabilityAssessmentModel> resourceAssessments;
  final List<SwotItemModel> swotItems;
  final Future<void> Function({
    required PestelDimension dimension,
    required String statement,
    required String impact,
    required String certainty,
    List<String>? evidenceRefs,
    List<BscPerspective>? bscPerspectives,
  }) onCreatePestelSignal;
  final Future<void> Function({
    required ResourceCapabilityCategory category,
    required String statement,
    required String strengthLevel,
    List<String>? evidenceRefs,
    List<BscPerspective>? bscPerspectives,
  }) onCreateResourceAssessment;
  final Future<void> Function({
    required SwotItemType itemType,
    required String content,
    required String sourceType,
    String? sourceId,
    List<String>? evidenceRefs,
    List<BscPerspective>? bscPerspectives,
  }) onCreateSwotItem;
  final Future<void> Function() onDeriveSwotDrafts;
  final VoidCallback onNext;
  final VoidCallback onBack;

  const StrategyAnalysisStep({
    super.key,
    required this.selectedObjective,
    required this.bscFocusScopes,
    required this.pestelSignals,
    required this.resourceAssessments,
    required this.swotItems,
    required this.onCreatePestelSignal,
    required this.onCreateResourceAssessment,
    required this.onCreateSwotItem,
    required this.onDeriveSwotDrafts,
    required this.onNext,
    required this.onBack,
  });

  @override
  State<StrategyAnalysisStep> createState() => _StrategyAnalysisStepState();
}

class _StrategyAnalysisStepState extends State<StrategyAnalysisStep>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isDeriving = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _handleDeriveSwot() async {
    setState(() => _isDeriving = true);
    try {
      await widget.onDeriveSwotDrafts();
    } finally {
      if (mounted) setState(() => _isDeriving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildObjectiveAndBscContext(),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Bước 3: Phân tích chiến lược (PESTEL, Nguồn lực & SWOT)',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Thu thập tín hiệu vĩ mô và năng lực nội tại, trích xuất dữ liệu cho ma trận TOWS',
                    style: TextStyle(color: Colors.white70, fontSize: 13),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            TabBar(
              controller: _tabController,
              isScrollable: true,
              tabs: const [
                Tab(icon: Icon(Icons.radar, size: 16), text: 'PESTEL vĩ mô'),
                Tab(icon: Icon(Icons.inventory_2_outlined, size: 16), text: 'Nguồn lực & Năng lực'),
                Tab(icon: Icon(Icons.grid_view, size: 16), text: 'Ma trận SWOT'),
              ],
            ),
          ],
        ),
        const SizedBox(height: 16),
        SizedBox(
          height: 480,
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildPestelTab(),
              _buildResourcesTab(),
              _buildSwotTab(),
            ],
          ),
        ),
        const SizedBox(height: 24),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            OutlinedButton.icon(
              key: const Key('btn_back_step'),
              onPressed: widget.onBack,
              icon: const Icon(Icons.arrow_back, size: 18),
              label: const Text('Quay lại: Trọng tâm BSC'),
            ),
            ElevatedButton.icon(
              key: const Key('btn_next_step'),
              onPressed: widget.onNext,
              icon: const Icon(Icons.arrow_forward, size: 18),
              label: const Text('Tiếp tục: Ưu tiên TOWS'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryColor,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildObjectiveAndBscContext() {
    return Container(
      key: const Key('analysis_context_header'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.blueAccent.withValues(alpha: 0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.flag, color: Colors.blueAccent, size: 18),
              const SizedBox(width: 8),
              Text(
                'Mục tiêu chiến lược: ${widget.selectedObjective.title}',
                style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13),
              ),
            ],
          ),
          if (widget.bscFocusScopes.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                const Text('Trọng tâm BSC định hướng:', style: TextStyle(color: Colors.white60, fontSize: 12)),
                ...widget.bscFocusScopes.map((scope) {
                  return Chip(
                    label: Text(
                      '${scope.perspective.displayNameVi}: ${scope.focusDescription}',
                      style: const TextStyle(fontSize: 11, color: Colors.white),
                    ),
                    backgroundColor: const Color(0xFF334155),
                    padding: EdgeInsets.zero,
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  );
                }),
              ],
            ),
          ],
        ],
      ),
    );
  }

  // --------------------------------------------------------------------------
  // PESTEL TAB
  // --------------------------------------------------------------------------

  Widget _buildPestelTab() {
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Tín hiệu PESTEL (${widget.pestelSignals.length})',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
            ),
            ElevatedButton.icon(
              key: const Key('btn_add_pestel_signal'),
              onPressed: _showAddPestelDialog,
              icon: const Icon(Icons.add, size: 16),
              label: const Text('Thêm tín hiệu PESTEL'),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Expanded(
          child: widget.pestelSignals.isEmpty
              ? _buildEmptyTabState(
                  icon: Icons.radar,
                  title: 'Chưa có tín hiệu PESTEL',
                  desc: 'Bổ sung các yếu tố Chính trị, Kinh tế, Xã hội, Công nghệ, Môi trường, Pháp lý tác động đến mục tiêu.',
                )
              : ListView.builder(
                  itemCount: widget.pestelSignals.length,
                  itemBuilder: (context, index) {
                    final signal = widget.pestelSignals[index];
                    return Card(
                      key: Key('card_pestel_${signal.id}'),
                      color: const Color(0xFF1E293B),
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        leading: Chip(
                          label: Text(
                            signal.dimension.displayNameVi,
                            style: const TextStyle(fontSize: 11, color: Colors.white),
                          ),
                          backgroundColor: const Color(0xFF0F766E),
                        ),
                        title: Text(signal.statement, style: const TextStyle(color: Colors.white, fontSize: 14)),
                        subtitle: Wrap(
                          spacing: 4,
                          runSpacing: 2,
                          children: [
                            Text(
                              'Tác động: ${signal.impact} | Độ chắc chắn: ${signal.certainty}',
                              style: const TextStyle(color: Colors.white54, fontSize: 12),
                            ),
                            ...signal.evidenceRefs.map(
                              (ref) => Chip(
                                label: Text(ref, style: const TextStyle(fontSize: 10, color: Colors.white70)),
                                avatar: const Icon(Icons.link, size: 12, color: Colors.white70),
                                backgroundColor: const Color(0xFF334155),
                                padding: EdgeInsets.zero,
                                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              ),
                            ),
                            ...signal.bscPerspectives.map(
                              (p) => Chip(
                                label: Text(p.displayNameVi, style: const TextStyle(fontSize: 10, color: Colors.white)),
                                backgroundColor: const Color(0xFF475569),
                                padding: EdgeInsets.zero,
                                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  void _showAddPestelDialog() {
    final statementCtrl = TextEditingController();
    PestelDimension dimension = PestelDimension.economic;
    String impact = 'HIGH';
    String certainty = 'MEDIUM';
    final List<BscPerspective> selectedPerspectives = [];

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDState) => AlertDialog(
          backgroundColor: const Color(0xFF1E293B),
          title: const Text('Thêm tín hiệu PESTEL', style: TextStyle(color: Colors.white)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<PestelDimension>(
                  initialValue: dimension,
                  dropdownColor: const Color(0xFF1E293B),
                  decoration: const InputDecoration(labelText: 'Khía cạnh PESTEL'),
                  items: PestelDimension.values
                      .where((d) => d != PestelDimension.unknown)
                      .map((d) => DropdownMenuItem(value: d, child: Text(d.displayNameVi)))
                      .toList(),
                  onChanged: (val) {
                    if (val != null) setDState(() => dimension = val);
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: statementCtrl,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: 'Nội dung tín hiệu / xu hướng (*)',
                    hintText: 'Ví dụ: Lãi suất vay ưu đãi cho DN công nghệ giảm 2%',
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        initialValue: impact,
                        dropdownColor: const Color(0xFF1E293B),
                        decoration: const InputDecoration(labelText: 'Mức độ tác động'),
                        items: const [
                          DropdownMenuItem(value: 'HIGH', child: Text('Cao (High)')),
                          DropdownMenuItem(value: 'MEDIUM', child: Text('Vừa (Medium)')),
                          DropdownMenuItem(value: 'LOW', child: Text('Thấp (Low)')),
                        ],
                        onChanged: (val) {
                          if (val != null) setDState(() => impact = val);
                        },
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        initialValue: certainty,
                        dropdownColor: const Color(0xFF1E293B),
                        decoration: const InputDecoration(labelText: 'Độ chắc chắn'),
                        items: const [
                          DropdownMenuItem(value: 'HIGH', child: Text('Cao')),
                          DropdownMenuItem(value: 'MEDIUM', child: Text('Trung bình')),
                          DropdownMenuItem(value: 'LOW', child: Text('Thấp')),
                        ],
                        onChanged: (val) {
                          if (val != null) setDState(() => certainty = val);
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text('Liên kết trọng tâm BSC:', style: TextStyle(color: Colors.white70, fontSize: 12)),
                ),
                Wrap(
                  spacing: 6,
                  children: [
                    BscPerspective.financial,
                    BscPerspective.customer,
                    BscPerspective.internalProcess,
                    BscPerspective.learningAndGrowth,
                  ].map((p) {
                    final isChecked = selectedPerspectives.contains(p);
                    return FilterChip(
                      label: Text(p.displayNameVi, style: const TextStyle(fontSize: 11)),
                      selected: isChecked,
                      onSelected: (checked) {
                        setDState(() {
                          if (checked) {
                            selectedPerspectives.add(p);
                          } else {
                            selectedPerspectives.remove(p);
                          }
                        });
                      },
                    );
                  }).toList(),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Hủy')),
            ElevatedButton(
              onPressed: () {
                if (statementCtrl.text.trim().isNotEmpty) {
                  widget.onCreatePestelSignal(
                    dimension: dimension,
                    statement: statementCtrl.text.trim(),
                    impact: impact,
                    certainty: certainty,
                    bscPerspectives: selectedPerspectives,
                  );
                  Navigator.pop(ctx);
                }
              },
              child: const Text('Lưu tín hiệu'),
            ),
          ],
        ),
      ),
    );
  }

  // --------------------------------------------------------------------------
  // RESOURCE & CAPABILITY TAB
  // --------------------------------------------------------------------------

  Widget _buildResourcesTab() {
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Đánh giá Nguồn lực & Năng lực (${widget.resourceAssessments.length})',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
            ),
            ElevatedButton.icon(
              key: const Key('btn_add_resource_assessment'),
              onPressed: _showAddResourceDialog,
              icon: const Icon(Icons.add, size: 16),
              label: const Text('Thêm nguồn lực / năng lực'),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Expanded(
          child: widget.resourceAssessments.isEmpty
              ? _buildEmptyTabState(
                  icon: Icons.inventory_2_outlined,
                  title: 'Chưa có đánh giá Nguồn lực & Năng lực',
                  desc: 'Đánh giá 6 nhóm nguồn lực nội tại theo đúng danh pháp chuẩn: Tài sản hữu hình, Tài sản vô hình, Nguồn lực tài chính, Kỹ năng con người, Quy trình vận hành, Khả năng đổi mới.',
                )
              : ListView.builder(
                  itemCount: widget.resourceAssessments.length,
                  itemBuilder: (context, index) {
                    final item = widget.resourceAssessments[index];
                    return Card(
                      key: Key('card_resource_${item.id}'),
                      color: const Color(0xFF1E293B),
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        leading: Chip(
                          label: Text(
                            item.category.displayNameVi,
                            style: const TextStyle(fontSize: 11, color: Colors.white),
                          ),
                          backgroundColor: const Color(0xFF1D4ED8),
                        ),
                        title: Text(item.statement, style: const TextStyle(color: Colors.white, fontSize: 14)),
                        subtitle: Wrap(
                          spacing: 4,
                          runSpacing: 2,
                          children: [
                            Text(
                              'Độ mạnh: ${item.maturityLevel}',
                              style: const TextStyle(color: Colors.white54, fontSize: 12),
                            ),
                            ...item.evidenceRefs.map(
                              (ref) => Chip(
                                label: Text(ref, style: const TextStyle(fontSize: 10, color: Colors.white70)),
                                avatar: const Icon(Icons.link, size: 12, color: Colors.white70),
                                backgroundColor: const Color(0xFF334155),
                                padding: EdgeInsets.zero,
                                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              ),
                            ),
                            ...item.bscPerspectives.map(
                              (p) => Chip(
                                label: Text(p.displayNameVi, style: const TextStyle(fontSize: 10, color: Colors.white)),
                                backgroundColor: const Color(0xFF475569),
                                padding: EdgeInsets.zero,
                                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  void _showAddResourceDialog() {
    final statementCtrl = TextEditingController();
    ResourceCapabilityCategory category = ResourceCapabilityCategory.humanOrganizationalCapability;
    String strengthLevel = 'HIGH';
    final List<BscPerspective> selectedPerspectives = [];

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDState) => AlertDialog(
          backgroundColor: const Color(0xFF1E293B),
          title: const Text('Thêm Đánh giá Nguồn lực / Năng lực', style: TextStyle(color: Colors.white)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<ResourceCapabilityCategory>(
                  initialValue: category,
                  dropdownColor: const Color(0xFF1E293B),
                  decoration: const InputDecoration(labelText: 'Nhóm Nguồn lực & Năng lực chuẩn'),
                  items: ResourceCapabilityCategory.values
                      .where((c) => c != ResourceCapabilityCategory.unknown)
                      .map((c) => DropdownMenuItem(
                            value: c,
                            child: Text(c.displayNameVi, style: const TextStyle(fontSize: 12)),
                          ))
                      .toList(),
                  onChanged: (val) {
                    if (val != null) setDState(() => category = val);
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: statementCtrl,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: 'Mô tả hiện trạng năng lực (*)',
                    hintText: 'Ví dụ: Đội ngũ kỹ sư nòng cốt có 5+ năm kinh nghiệm trong Generative AI',
                  ),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: strengthLevel,
                  dropdownColor: const Color(0xFF1E293B),
                  decoration: const InputDecoration(labelText: 'Mức độ mạnh / trưởng thành'),
                  items: const [
                    DropdownMenuItem(value: 'HIGH', child: Text('Mạnh / Lợi thế cốt lõi (High)')),
                    DropdownMenuItem(value: 'MEDIUM', child: Text('Trung bình (Medium)')),
                    DropdownMenuItem(value: 'LOW', child: Text('Yếu / Cần khắc phục (Low)')),
                  ],
                  onChanged: (val) {
                    if (val != null) setDState(() => strengthLevel = val);
                  },
                ),
                const SizedBox(height: 12),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text('Liên kết trọng tâm BSC:', style: TextStyle(color: Colors.white70, fontSize: 12)),
                ),
                Wrap(
                  spacing: 6,
                  children: [
                    BscPerspective.financial,
                    BscPerspective.customer,
                    BscPerspective.internalProcess,
                    BscPerspective.learningAndGrowth,
                  ].map((p) {
                    final isChecked = selectedPerspectives.contains(p);
                    return FilterChip(
                      label: Text(p.displayNameVi, style: const TextStyle(fontSize: 11)),
                      selected: isChecked,
                      onSelected: (checked) {
                        setDState(() {
                          if (checked) {
                            selectedPerspectives.add(p);
                          } else {
                            selectedPerspectives.remove(p);
                          }
                        });
                      },
                    );
                  }).toList(),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Hủy')),
            ElevatedButton(
              onPressed: () {
                if (statementCtrl.text.trim().isNotEmpty) {
                  widget.onCreateResourceAssessment(
                    category: category,
                    statement: statementCtrl.text.trim(),
                    strengthLevel: strengthLevel,
                    bscPerspectives: selectedPerspectives,
                  );
                  Navigator.pop(ctx);
                }
              },
              child: const Text('Lưu năng lực'),
            ),
          ],
        ),
      ),
    );
  }

  // --------------------------------------------------------------------------
  // SWOT TAB (WITH PROVENANCE)
  // --------------------------------------------------------------------------

  Widget _buildSwotTab() {
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Yếu tố SWOT (${widget.swotItems.length})',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
            ),
            Row(
              children: [
                ElevatedButton.icon(
                  key: const Key('btn_derive_swot'),
                  onPressed: _isDeriving ? null : _handleDeriveSwot,
                  icon: _isDeriving
                      ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.auto_awesome, size: 16),
                  label: const Text('Trích xuất từ PESTEL & Nguồn lực'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF7C3AED),
                    foregroundColor: Colors.white,
                  ),
                ),
                const SizedBox(width: 8),
                ElevatedButton.icon(
                  key: const Key('btn_add_manual_swot'),
                  onPressed: _showAddManualSwotDialog,
                  icon: const Icon(Icons.add, size: 16),
                  label: const Text('Thêm thủ công'),
                ),
              ],
            ),
          ],
        ),
        const SizedBox(height: 8),
        Expanded(
          child: widget.swotItems.isEmpty
              ? _buildEmptyTabState(
                  icon: Icons.grid_view,
                  title: 'Chưa có dữ liệu SWOT',
                  desc: 'Bấm nút "Trích xuất từ PESTEL & Nguồn lực" để sinh tự động các cơ hội/thách thức và điểm mạnh/yếu có nguồn gốc, hoặc thêm thủ công.',
                )
              : GridView.count(
                  crossAxisCount: 2,
                  childAspectRatio: 1.6,
                  crossAxisSpacing: 8,
                  mainAxisSpacing: 8,
                  children: [
                    _buildSwotQuadrant(SwotItemType.strength, 'Điểm mạnh (Strengths)', Colors.green),
                    _buildSwotQuadrant(SwotItemType.weakness, 'Điểm yếu (Weaknesses)', Colors.redAccent),
                    _buildSwotQuadrant(SwotItemType.opportunity, 'Cơ hội (Opportunities)', Colors.blueAccent),
                    _buildSwotQuadrant(SwotItemType.threat, 'Thách thức (Threats)', Colors.amber),
                  ],
                ),
        ),
      ],
    );
  }

  Widget _buildSwotQuadrant(SwotItemType type, String title, Color color) {
    final items = widget.swotItems.where((s) => s.itemType == type).toList();

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                title,
                style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 13),
              ),
              Text('${items.length}', style: TextStyle(color: color, fontSize: 12)),
            ],
          ),
          const Divider(height: 12, color: Colors.white12),
          Expanded(
            child: items.isEmpty
                ? const Center(
                    child: Text('Trống', style: TextStyle(color: Colors.white30, fontSize: 12)),
                  )
                : ListView.builder(
                    itemCount: items.length,
                    itemBuilder: (context, idx) {
                      final item = items[idx];
                      final isManual = item.sourcePestelSignalId == null && item.sourceResourceCapabilityId == null;

                      return Container(
                        margin: const EdgeInsets.only(bottom: 6),
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0F172A),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(item.content, style: const TextStyle(color: Colors.white, fontSize: 13)),
                            const SizedBox(height: 4),
                            Wrap(
                              spacing: 4,
                              children: [
                                // Source provenance chip
                                if (isManual)
                                  const Chip(
                                    label: Text('Nguồn: Thủ công', style: TextStyle(fontSize: 9, color: Colors.amberAccent)),
                                    backgroundColor: Color(0xFF78350F),
                                    padding: EdgeInsets.zero,
                                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                  )
                                else
                                  Chip(
                                    label: Text(
                                      item.sourcePestelSignalId != null ? 'Nguồn: PESTEL' : 'Nguồn: Nguồn lực',
                                      style: const TextStyle(fontSize: 9, color: Colors.lightGreenAccent),
                                    ),
                                    backgroundColor: const Color(0xFF064E3B),
                                    padding: EdgeInsets.zero,
                                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                  ),
                                ...item.evidenceRefs.map(
                                  (ref) => Chip(
                                    label: Text(ref, style: const TextStyle(fontSize: 9, color: Colors.white70)),
                                    avatar: const Icon(Icons.link, size: 10, color: Colors.white70),
                                    backgroundColor: const Color(0xFF1E293B),
                                    padding: EdgeInsets.zero,
                                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                  ),
                                ),
                                ...item.bscPerspectives.map(
                                  (p) => Chip(
                                    label: Text(p.displayNameVi, style: const TextStyle(fontSize: 9, color: Colors.white70)),
                                    backgroundColor: const Color(0xFF334155),
                                    padding: EdgeInsets.zero,
                                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  void _showAddManualSwotDialog() {
    final contentCtrl = TextEditingController();
    final evidenceCtrl = TextEditingController();
    SwotItemType itemType = SwotItemType.strength;
    final List<BscPerspective> selectedPerspectives = [];

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDState) => AlertDialog(
          backgroundColor: const Color(0xFF1E293B),
          title: const Text('Thêm mục SWOT thủ công', style: TextStyle(color: Colors.white)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<SwotItemType>(
                  initialValue: itemType,
                  dropdownColor: const Color(0xFF1E293B),
                  decoration: const InputDecoration(labelText: 'Phân loại SWOT (*)'),
                  items: const [
                    DropdownMenuItem(value: SwotItemType.strength, child: Text('Điểm mạnh (Strength)')),
                    DropdownMenuItem(value: SwotItemType.weakness, child: Text('Điểm yếu (Weakness)')),
                    DropdownMenuItem(value: SwotItemType.opportunity, child: Text('Cơ hội (Opportunity)')),
                    DropdownMenuItem(value: SwotItemType.threat, child: Text('Thách thức (Threat)')),
                  ],
                  onChanged: (val) {
                    if (val != null) setDState(() => itemType = val);
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: contentCtrl,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: 'Nội dung nhận định (*)',
                    hintText: 'Nhập nội dung quan sát hoặc phân tích...',
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: evidenceCtrl,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: 'Nguồn dẫn chứng / Bằng chứng (Bắt buộc cho mục thủ công) (*)',
                    hintText: 'Ví dụ: Báo cáo thị trường Gartner 2026, Phỏng vấn 10 khách hàng...',
                  ),
                ),
                const SizedBox(height: 12),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text('Liên kết trọng tâm BSC:', style: TextStyle(color: Colors.white70, fontSize: 12)),
                ),
                Wrap(
                  spacing: 6,
                  children: [
                    BscPerspective.financial,
                    BscPerspective.customer,
                    BscPerspective.internalProcess,
                    BscPerspective.learningAndGrowth,
                  ].map((p) {
                    final isChecked = selectedPerspectives.contains(p);
                    return FilterChip(
                      label: Text(p.displayNameVi, style: const TextStyle(fontSize: 11)),
                      selected: isChecked,
                      onSelected: (checked) {
                        setDState(() {
                          if (checked) {
                            selectedPerspectives.add(p);
                          } else {
                            selectedPerspectives.remove(p);
                          }
                        });
                      },
                    );
                  }).toList(),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Hủy')),
            ElevatedButton(
              onPressed: () {
                final text = contentCtrl.text.trim();
                final evidence = evidenceCtrl.text.trim();
                if (text.isNotEmpty && evidence.isNotEmpty) {
                  widget.onCreateSwotItem(
                    itemType: itemType,
                    content: text,
                    sourceType: 'MANUAL',
                    evidenceRefs: [evidence],
                    bscPerspectives: selectedPerspectives,
                  );
                  Navigator.pop(ctx);
                }
              },
              child: const Text('Lưu mục SWOT'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyTabState({required IconData icon, required String title, required String desc}) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 40, color: Colors.white24),
            const SizedBox(height: 8),
            Text(title, style: const TextStyle(color: Colors.white70, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            Text(desc, style: const TextStyle(color: Colors.white38, fontSize: 12), textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}
