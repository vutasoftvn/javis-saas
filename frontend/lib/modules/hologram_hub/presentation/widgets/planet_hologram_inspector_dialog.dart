import 'dart:math' as math;
import 'package:flutter/material.dart';

/// Data specifications for 8 planets in the Solar System,
/// connecting sacred Trống Đồng astronomical orbits with COSA OS enterprise philosophy.
class PlanetHologramData {
  final String id;
  final String nameVi;
  final String nameEn;
  final String symbol;
  final String chineseStarName;
  final double orbitRatio;
  final double radius;
  final Color primaryColor;
  final Color darkColor;
  final Color glowColor;
  final int turns;
  final double startAngle;
  final bool hasMoon;
  final bool hasStripes;
  final bool hasRings;
  final bool hasPolarCap;
  final bool hasVerticalRing;

  // Astronomical & Physical specs
  final String solarDistance;
  final String orbitalPeriod;
  final String diameter;
  final String surfaceTemp;
  final String keyFeatures;

  // COSA OS System Role & Philosophy
  final String cosaRole;
  final String cosaBadge;
  final String cosaDescription;
  final String cosaMetric;
  final IconData cosaIcon;

  const PlanetHologramData({
    required this.id,
    required this.nameVi,
    required this.nameEn,
    required this.symbol,
    required this.chineseStarName,
    required this.orbitRatio,
    required this.radius,
    required this.primaryColor,
    required this.darkColor,
    required this.glowColor,
    required this.turns,
    required this.startAngle,
    this.hasMoon = false,
    this.hasStripes = false,
    this.hasRings = false,
    this.hasPolarCap = false,
    this.hasVerticalRing = false,
    required this.solarDistance,
    required this.orbitalPeriod,
    required this.diameter,
    required this.surfaceTemp,
    required this.keyFeatures,
    required this.cosaRole,
    required this.cosaBadge,
    required this.cosaDescription,
    required this.cosaMetric,
    required this.cosaIcon,
  });

  static const double alignmentAxis = -math.pi / 3.8;

  static const List<PlanetHologramData> allPlanets = [
    PlanetHologramData(
      id: 'mercury',
      nameVi: 'Thủy Tinh',
      nameEn: 'Mercury',
      symbol: '☿',
      chineseStarName: 'Thần Tinh (Thủy Đức)',
      orbitRatio: 0.28,
      radius: 4.8,
      primaryColor: Color(0xFFE2E8F0),
      darkColor: Color(0xFF475569),
      glowColor: Color(0xFF94A3B8),
      turns: 16,
      startAngle: alignmentAxis,
      solarDistance: '57.9 triệu km (0.39 AU)',
      orbitalPeriod: '88 ngày Trái Đất',
      diameter: '4,879 km',
      surfaceTemp: '-180°C đến 430°C',
      keyFeatures: 'Hành tinh nhỏ nhất, bề mặt nhiều hố va chạm và chuyển động nhanh nhất quanh Mặt Trời.',
      cosaRole: 'Tốc độ phản hồi & Tác chiến tức thời',
      cosaBadge: 'TỐC ĐỘ PHẢN HỒI',
      cosaDescription: 'Đại diện cho nhịp độ xung thần kinh thời gian thực, độ trễ xử lý < 250ms và sự thích ứng siêu linh hoạt của hệ thống trước mọi biến động thị trường.',
      cosaMetric: 'Độ trễ API: < 120ms | Tần số xử lý: 16 Hz',
      cosaIcon: Icons.bolt_rounded,
    ),
    PlanetHologramData(
      id: 'venus',
      nameVi: 'Kim Tinh',
      nameEn: 'Venus',
      symbol: '♀',
      chineseStarName: 'Thái Bạch (Kim Đức)',
      orbitRatio: 0.39,
      radius: 6.8,
      primaryColor: Color(0xFFFEF08A),
      darkColor: Color(0xFFD97706),
      glowColor: Color(0xFFF59E0B),
      turns: 11,
      startAngle: alignmentAxis,
      solarDistance: '108.2 triệu km (0.72 AU)',
      orbitalPeriod: '225 ngày Trái Đất',
      diameter: '12,104 km',
      surfaceTemp: '465°C (Nhiệt độ cao nhất hệ)',
      keyFeatures: 'Hành tinh sáng nhất bầu trời đêm với bầu khí quyển dày đặc phản chiếu 75% ánh sáng.',
      cosaRole: 'Giá trị cốt lõi & Trải nghiệm khách hàng',
      cosaBadge: 'TRẢI NGHIỆM KHÁCH HÀNG',
      cosaDescription: 'Biểu trưng cho sức hút thương hiệu mãnh liệt, thiết kế tinh xảo vị nhân sinh và giá trị cốt lõi không thể thay thế khiến khách hàng gắn bó lâu dài.',
      cosaMetric: 'NPS Trải nghiệm: 94.8% | Retention: 89.2%',
      cosaIcon: Icons.auto_awesome_rounded,
    ),
    PlanetHologramData(
      id: 'earth',
      nameVi: 'Trái Đất',
      nameEn: 'Earth',
      symbol: '♁',
      chineseStarName: 'Địa Cầu (Nhân Hòa)',
      orbitRatio: 0.51,
      radius: 7.6,
      primaryColor: Color(0xFF38BDF8),
      darkColor: Color(0xFF1D4ED8),
      glowColor: Color(0xFF00F0FF),
      turns: 8,
      startAngle: alignmentAxis,
      hasMoon: true,
      solarDistance: '149.6 triệu km (1.00 AU)',
      orbitalPeriod: '365.25 ngày (1 năm)',
      diameter: '12,742 km',
      surfaceTemp: '15°C (Vùng sinh thái vàng)',
      keyFeatures: 'Cái nôi của sự sống, 71% bề mặt là đại dương lấp lánh, có bầu khí quyển bảo vệ và Mặt Trăng đồng hành.',
      cosaRole: 'Khách hàng, Thị trường & Product-Market Fit',
      cosaBadge: 'THỊ TRƯỜNG & PMF',
      cosaDescription: 'Trung tâm sinh quyển của doanh nghiệp — nơi sản phẩm giải quyết nỗi đau thực tế của khách hàng, nuôi dưỡng hệ sinh thái cộng đồng và đạt PMF bền vững.',
      cosaMetric: 'PMF Score: 92/100 | Active Users: 100K+',
      cosaIcon: Icons.public_rounded,
    ),
    PlanetHologramData(
      id: 'mars',
      nameVi: 'Hỏa Tinh',
      nameEn: 'Mars',
      symbol: '♂',
      chineseStarName: 'Huỳnh Hoặc (Hỏa Đức)',
      orbitRatio: 0.63,
      radius: 5.8,
      primaryColor: Color(0xFFF87171),
      darkColor: Color(0xFF991B1B),
      glowColor: Color(0xFFEF4444),
      turns: 6,
      startAngle: alignmentAxis,
      hasPolarCap: true,
      solarDistance: '227.9 triệu km (1.52 AU)',
      orbitalPeriod: '687 ngày Trái Đất',
      diameter: '6,779 km',
      surfaceTemp: '-63°C (Khô lạnh & bão cát)',
      keyFeatures: 'Hành tinh Đỏ giàu oxit sắt, sở hữu chỏm băng cực Bắc vĩnh cửu và hẻm vực Valles Marineris kỳ vĩ.',
      cosaRole: 'Đột phá tiên phong & Thử nghiệm táo bạo',
      cosaBadge: 'TIÊN PHONG ĐỘT PHÁ',
      cosaDescription: 'Tinh thần dấn thân khai phá lãnh địa mới, chiến lược R&D quyết đoán, văn hóa thử nghiệm A/B liên tục và vượt qua mọi rào cản giới hạn.',
      cosaMetric: 'Tốc độ thử nghiệm: 48 chu kỳ/quý | R&D Score: Top 1%',
      cosaIcon: Icons.rocket_launch_rounded,
    ),
    PlanetHologramData(
      id: 'jupiter',
      nameVi: 'Mộc Tinh',
      nameEn: 'Jupiter',
      symbol: '♃',
      chineseStarName: 'Tuế Tinh (Mộc Đức)',
      orbitRatio: 0.76,
      radius: 12.8,
      primaryColor: Color(0xFFFDE68A),
      darkColor: Color(0xFF92400E),
      glowColor: Color(0xFFD97706),
      turns: 4,
      startAngle: alignmentAxis,
      hasStripes: true,
      solarDistance: '778.5 triệu km (5.20 AU)',
      orbitalPeriod: '11.86 năm Trái Đất',
      diameter: '139,820 km',
      surfaceTemp: '-110°C (Áp suất khổng lồ)',
      keyFeatures: 'Đại hành tinh khí lớn nhất Hệ Mặt Trời với các dải mây xoáy caramel và cơn bão Đốm Đỏ Lớn tồn tại hàng thế kỷ.',
      cosaRole: 'Tăng trưởng quy mô & Động lực dòng vốn',
      cosaBadge: 'TĂNG TRƯỞNG & VỐN',
      cosaDescription: 'Trọng lực hấp dẫn khổng lồ biểu trưng cho cỗ máy mở rộng quy mô cấp số nhân, hiệu ứng mạng lưới bao trùm và năng lực tập trung dòng vốn mạnh mẽ.',
      cosaMetric: 'Tốc độ mở rộng ARR: +240%/năm | Hiệu ứng mạng lưới',
      cosaIcon: Icons.trending_up_rounded,
    ),
    PlanetHologramData(
      id: 'saturn',
      nameVi: 'Thổ Tinh',
      nameEn: 'Saturn',
      symbol: '♄',
      chineseStarName: 'Trấn Tinh (Thổ Đức)',
      orbitRatio: 0.89,
      radius: 10.2,
      primaryColor: Color(0xFFFEF08A),
      darkColor: Color(0xFFB45309),
      glowColor: Color(0xFFE5A93C),
      turns: 3,
      startAngle: alignmentAxis,
      hasRings: true,
      solarDistance: '1.43 tỷ km (9.58 AU)',
      orbitalPeriod: '29.45 năm Trái Đất',
      diameter: '116,460 km',
      surfaceTemp: '-140°C (Hệ vành đai băng đá)',
      keyFeatures: 'Tuyệt tác thiên văn với hệ vành đai nghiêng Cassini lấp lánh trải rộng hàng trăm ngàn kilomet từ băng đá và bụi vũ trụ.',
      cosaRole: 'Quản trị hệ thống, Kỷ luật & Pháp trị',
      cosaBadge: 'QUẢN TRỊ & PHÁP TRỊ',
      cosaDescription: 'Hệ vành đai bảo vệ trứ danh tượng trưng cho khuôn khổ pháp lý vững như bàn thạch, chuẩn mực quản trị rủi ro, bảo mật nghiêm ngặt và tính kỷ luật vận hành.',
      cosaMetric: 'Tuân thủ SLA: 99.98% | Kiểm toán & Rào chắn: 100%',
      cosaIcon: Icons.shield_rounded,
    ),
    PlanetHologramData(
      id: 'uranus',
      nameVi: 'Thiên Vương',
      nameEn: 'Uranus',
      symbol: '♅',
      chineseStarName: 'Thiên Vương Tinh',
      orbitRatio: 1.02,
      radius: 8.4,
      primaryColor: Color(0xFFA5F3FC),
      darkColor: Color(0xFF0E7490),
      glowColor: Color(0xFF06B6D4),
      turns: 2,
      startAngle: alignmentAxis,
      hasVerticalRing: true,
      solarDistance: '2.87 tỷ km (19.2 AU)',
      orbitalPeriod: '84 năm Trái Đất',
      diameter: '50,724 km',
      surfaceTemp: '-195°C (Hành tinh băng khổng lồ)',
      keyFeatures: 'Trục tự quay nghiêng 98 độ gần như nằm ngang với hệ vành đai dựng đứng độc nhất trong Hệ Mặt Trời.',
      cosaRole: 'Công nghệ lõi sâu (Deep-Tech) & AI Đột phá',
      cosaBadge: 'DEEP-TECH MOAT',
      cosaDescription: 'Tư duy phản biện khác biệt hoàn toàn với số đông — tượng trưng cho con hào công nghệ trí tuệ nhân tạo độc quyền và kiến trúc nền tảng không thể sao chép.',
      cosaMetric: 'Hệ thống 16 AI Agents tự hành | Deep-Tech Moat',
      cosaIcon: Icons.psychology_rounded,
    ),
    PlanetHologramData(
      id: 'neptune',
      nameVi: 'Hải Vương',
      nameEn: 'Neptune',
      symbol: '♆',
      chineseStarName: 'Hải Vương Tinh',
      orbitRatio: 1.16,
      radius: 8.0,
      primaryColor: Color(0xFF60A5FA),
      darkColor: Color(0xFF1E3A8A),
      glowColor: Color(0xFF3B82F6),
      turns: 1,
      startAngle: alignmentAxis,
      solarDistance: '4.50 tỷ km (30.1 AU)',
      orbitalPeriod: '164.8 năm Trái Đất',
      diameter: '49,244 km',
      surfaceTemp: '-200°C (Gió bão siêu thanh 2,100 km/h)',
      keyFeatures: 'Quả cầu xanh thẳm của đại dương vũ trụ với những cơn gió bão dữ dội nhất Hệ Mặt Trời và đốm đen Great Dark Spot.',
      cosaRole: 'Tầm nhìn dài hạn & Chiến lược đại dương xanh',
      cosaBadge: 'TẦM NHÌN DÀI HẠN',
      cosaDescription: 'Quỹ đạo xa nhất hướng về chiều sâu vô cực — tượng trưng cho định hướng chiến lược 10 năm, khám phá những thị trường ngách đại dương xanh chưa từng ai chạm tới.',
      cosaMetric: 'Tầm nhìn chiến lược: 10 năm | Blue Ocean Strategy',
      cosaIcon: Icons.explore_rounded,
    ),
  ];

  static PlanetHologramData? findById(String id) {
    for (final p in allPlanets) {
      if (p.id.toLowerCase() == id.toLowerCase()) return p;
    }
    return null;
  }
}

/// Modal inspector dialog with smooth holographic zoom animation,
/// 3D rotating planet preview, astronomical specs, and COSA OS strategic symbolism.
class PlanetHologramInspectorDialog extends StatefulWidget {
  final PlanetHologramData planet;

  const PlanetHologramInspectorDialog({
    super.key,
    required this.planet,
  });

  /// Opens the inspector with a smooth holographic scale & fade transition
  static Future<void> show(BuildContext context, PlanetHologramData planet) {
    return showGeneralDialog(
      context: context,
      barrierDismissible: true,
      barrierLabel: 'DismissPlanetHologram',
      barrierColor: Colors.black.withValues(alpha: 0.78),
      transitionDuration: const Duration(milliseconds: 320),
      pageBuilder: (context, anim1, anim2) {
        return PlanetHologramInspectorDialog(planet: planet);
      },
      transitionBuilder: (context, anim1, anim2, child) {
        final curved = CurvedAnimation(
          parent: anim1,
          curve: Curves.easeOutBack,
          reverseCurve: Curves.easeInCubic,
        );
        return ScaleTransition(
          scale: Tween<double>(begin: 0.85, end: 1.0).animate(curved),
          child: FadeTransition(
            opacity: anim1,
            child: child,
          ),
        );
      },
    );
  }

  @override
  State<PlanetHologramInspectorDialog> createState() => _PlanetHologramInspectorDialogState();
}

class _PlanetHologramInspectorDialogState extends State<PlanetHologramInspectorDialog>
    with SingleTickerProviderStateMixin {
  late final AnimationController _rotationCtrl;

  @override
  void initState() {
    super.initState();
    _rotationCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 14),
    )..repeat();
  }

  @override
  void dispose() {
    _rotationCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final planet = widget.planet;
    final screenWidth = MediaQuery.of(context).size.width;
    final isCompact = screenWidth < 680;

    return Center(
      child: Material(
        color: Colors.transparent,
        child: Container(
          width: isCompact ? (screenWidth - 32) : 740,
          constraints: BoxConstraints(
            maxHeight: MediaQuery.of(context).size.height * 0.88,
          ),
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
          decoration: BoxDecoration(
            color: const Color(0xFF070B19).withValues(alpha: 0.95),
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: planet.glowColor.withValues(alpha: 0.35),
              width: 1.5,
            ),
            boxShadow: [
              BoxShadow(
                color: planet.glowColor.withValues(alpha: 0.18),
                blurRadius: 36,
                spreadRadius: 2,
              ),
              const BoxShadow(
                color: Colors.black,
                blurRadius: 24,
                spreadRadius: 8,
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // ── Cyber Top Bar ────────────────────────────────────
                _buildTopBar(context, planet),

                // ── Main Content Area ────────────────────────────────
                Flexible(
                  child: SingleChildScrollView(
                    physics: const BouncingScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(24, 12, 24, 24),
                    child: isCompact
                        ? Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Center(child: _buildPlanet3DPreview(planet)),
                              const SizedBox(height: 20),
                              _buildCosaOsCard(planet),
                              const SizedBox(height: 16),
                              _buildAstronomicalSpecsCard(planet),
                            ],
                          )
                        : Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Left column: 3D Hologram rotating sphere
                              SizedBox(
                                width: 280,
                                child: Column(
                                  children: [
                                    _buildPlanet3DPreview(planet),
                                    const SizedBox(height: 16),
                                    _buildAstronomicalSpecsCard(planet),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 24),
                              // Right column: COSA OS strategic meaning & specs
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    _buildCosaOsCard(planet),
                                    const SizedBox(height: 16),
                                    _buildOrbitalMechanicsCard(planet),
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
        ),
      ),
    );
  }

  Widget _buildTopBar(BuildContext context, PlanetHologramData planet) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withValues(alpha: 0.70),
        border: Border(
          bottom: BorderSide(
            color: planet.glowColor.withValues(alpha: 0.20),
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          // Cyber HUD Radar Dot
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: planet.glowColor,
              boxShadow: [
                BoxShadow(
                  color: planet.glowColor.withValues(alpha: 0.8),
                  blurRadius: 8,
                  spreadRadius: 2,
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          // Planet symbol & title
          Text(
            planet.symbol,
            style: TextStyle(
              fontSize: 20,
              color: planet.primaryColor,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Row(
              children: [
                Text(
                  planet.nameVi.toUpperCase(),
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.2,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  '// ${planet.nameEn.toUpperCase()}',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 1.0,
                    color: planet.glowColor.withValues(alpha: 0.85),
                  ),
                ),
              ],
            ),
          ),
          // Close button ✕
          Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: () => Navigator.of(context).pop(),
              borderRadius: BorderRadius.circular(20),
              hoverColor: Colors.white.withValues(alpha: 0.1),
              child: Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.2),
                    width: 1,
                  ),
                ),
                child: const Icon(
                  Icons.close_rounded,
                  size: 18,
                  color: Colors.white70,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPlanet3DPreview(PlanetHologramData planet) {
    return Container(
      width: 250,
      height: 250,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: const Color(0xFF030611).withValues(alpha: 0.6),
        shape: BoxShape.circle,
        border: Border.all(
          color: planet.glowColor.withValues(alpha: 0.25),
          width: 1.2,
        ),
      ),
      child: AnimatedBuilder(
        animation: _rotationCtrl,
        builder: (context, _) {
          return CustomPaint(
            size: const Size(240, 240),
            painter: _PlanetHologram3DPainter(
              planet: planet,
              rotationProgress: _rotationCtrl.value,
            ),
          );
        },
      ),
    );
  }

  Widget _buildCosaOsCard(PlanetHologramData planet) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            planet.darkColor.withValues(alpha: 0.28),
            const Color(0xFF0B132B).withValues(alpha: 0.65),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: planet.glowColor.withValues(alpha: 0.35),
          width: 1.2,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: planet.glowColor.withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: planet.glowColor.withValues(alpha: 0.4),
                    width: 1,
                  ),
                ),
                child: Icon(planet.cosaIcon, size: 20, color: planet.primaryColor),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'BIỂU TƯỢNG COSA OS',
                      style: TextStyle(
                        fontSize: 10.5,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.4,
                        color: planet.glowColor,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      planet.cosaBadge,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.5,
                        color: Colors.white,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            planet.cosaDescription,
            style: const TextStyle(
              fontSize: 13,
              height: 1.55,
              color: Color(0xFFCBD5E1),
            ),
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFF030712).withValues(alpha: 0.6),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: planet.glowColor.withValues(alpha: 0.25),
                width: 1,
              ),
            ),
            child: Row(
              children: [
                Icon(Icons.query_stats_rounded, size: 16, color: planet.glowColor),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    planet.cosaMetric,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: planet.primaryColor,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAstronomicalSpecsCard(PlanetHologramData planet) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0B1329).withValues(alpha: 0.45),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.12),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.public, size: 16, color: planet.glowColor),
              const SizedBox(width: 8),
              const Text(
                'THÔNG SỐ THIÊN VĂN',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.2,
                  color: Colors.white70,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildSpecRow('Cổ danh Thất Tinh', planet.chineseStarName),
          _buildSpecRow('Khoảng cách', planet.solarDistance),
          _buildSpecRow('Chu kỳ quỹ đạo', planet.orbitalPeriod),
          _buildSpecRow('Đường kính xích đạo', planet.diameter),
          _buildSpecRow('Nhiệt độ bề mặt', planet.surfaceTemp),
        ],
      ),
    );
  }

  Widget _buildOrbitalMechanicsCard(PlanetHologramData planet) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0B1329).withValues(alpha: 0.45),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.12),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.track_changes_rounded, size: 16, color: planet.glowColor),
              const SizedBox(width: 8),
              const Text(
                'CƠ HỌC QUỸ ĐẠO TRỐNG ĐỒNG',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.2,
                  color: Colors.white70,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildSpecRow(
            'Tỷ lệ bán kính Trống Đồng',
            '${(planet.orbitRatio * 100).toStringAsFixed(0)}% (${planet.orbitRatio}x R)',
          ),
          _buildSpecRow(
            'Tần số quay chu kỳ 120s',
            '${planet.turns} vòng toàn phần',
          ),
          _buildSpecRow(
            'Đặc trưng hình thái',
            planet.keyFeatures,
          ),
        ],
      ),
    );
  }

  Widget _buildSpecRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(
              label,
              style: TextStyle(
                fontSize: 11.5,
                color: Colors.white.withValues(alpha: 0.55),
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: Colors.white,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// CustomPainter rendering a highly-detailed 3D rotating hologram sphere
/// with specific celestial features:
/// - Saturn: Tilted Cassini rings with division and planetary shadows.
/// - Earth: Swirling oceans, cloud patterns, and an orbiting 3D Moon.
/// - Jupiter: Caramel atmospheric bands and moving Great Red Spot.
/// - Mars: Northern polar ice cap and terracotta crust.
/// - Other planets: Craters, sulfuric clouds, vertical ice ring, deep dark storm.
class _PlanetHologram3DPainter extends CustomPainter {
  final PlanetHologramData planet;
  final double rotationProgress;

  _PlanetHologram3DPainter({
    required this.planet,
    required this.rotationProgress,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    // Diameter ~120–160px: radius = 56px (diameter 112-140px with rings/moons)
    final sphereRadius = planet.hasRings ? 48.0 : (planet.hasStripes ? 62.0 : 54.0);

    // 1. Draw outer cyber radar HUD frame (azimuth ring, tick marks, rotating scanline)
    _drawCyberRadarHud(canvas, center, size.width / 2 - 8);

    // 2. Draw 3D planet celestial body
    if (planet.hasRings) {
      _drawSaturnWithCassiniRings(canvas, center, sphereRadius);
    } else if (planet.hasMoon) {
      _drawEarthWithOrbitingMoon(canvas, center, sphereRadius);
    } else if (planet.hasStripes) {
      _drawJupiterWithGreatRedSpot(canvas, center, sphereRadius);
    } else if (planet.hasPolarCap) {
      _drawMarsWithPolarCap(canvas, center, sphereRadius);
    } else if (planet.hasVerticalRing) {
      _drawUranusWithVerticalRing(canvas, center, sphereRadius);
    } else {
      _drawStandard3DSphere(canvas, center, sphereRadius);
    }

    // 3. Holographic Scanline & Glitch Light Beam Sweep
    _drawHolographicScanSweep(canvas, center, size);
  }

  void _drawCyberRadarHud(Canvas canvas, Offset center, double radius) {
    final hudPaint = Paint()
      ..color = planet.glowColor.withValues(alpha: 0.18)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;

    // Outer guide circle
    canvas.drawCircle(center, radius, hudPaint);

    // Radial tick marks every 30 degrees
    final tickPaint = Paint()
      ..color = planet.glowColor.withValues(alpha: 0.35)
      ..strokeWidth = 1.2;

    for (int deg = 0; deg < 360; deg += 30) {
      final rad = deg * math.pi / 180.0;
      final p1 = center + Offset(math.cos(rad), math.sin(rad)) * (radius - 5);
      final p2 = center + Offset(math.cos(rad), math.sin(rad)) * radius;
      canvas.drawLine(p1, p2, tickPaint);
    }

    // Concentric coordinate rings
    canvas.drawCircle(
      center,
      radius * 0.76,
      Paint()
        ..color = planet.glowColor.withValues(alpha: 0.08)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.8,
    );
  }

  void _drawStandard3DSphere(Canvas canvas, Offset center, double r) {
    _drawAmbientGlow(canvas, center, r);
    _drawSphereBase(canvas, center, r);

    // Surface details for Mercury / Venus / Neptune
    final rotAngle = rotationProgress * 2 * math.pi;

    if (planet.id == 'mercury') {
      // Craters drifting
      for (int i = 0; i < 5; i++) {
        final cx = center.dx + math.cos(rotAngle + i * 1.3) * (r * 0.55);
        final cy = center.dy + math.sin((i * 1.7)) * (r * 0.45);
        if ((Offset(cx, cy) - center).distance < r * 0.8) {
          canvas.drawCircle(
            Offset(cx, cy),
            4.0 + (i % 3),
            Paint()
              ..color = const Color(0xFF1E293B).withValues(alpha: 0.6)
              ..style = PaintingStyle.fill,
          );
        }
      }
    } else if (planet.id == 'venus') {
      // Swirling golden cloud bands
      canvas.save();
      final clipPath = Path()..addOval(Rect.fromCircle(center: center, radius: r));
      canvas.clipPath(clipPath);

      final cloudPaint = Paint()
        ..color = const Color(0xFFFEF3C7).withValues(alpha: 0.22)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 6.0;

      for (int y = -2; y <= 2; y++) {
        final waveOffset = math.sin(rotAngle + y) * 12;
        canvas.drawLine(
          Offset(center.dx - r, center.dy + y * 14 + waveOffset),
          Offset(center.dx + r, center.dy + y * 14 - waveOffset),
          cloudPaint,
        );
      }
      canvas.restore();
    } else if (planet.id == 'neptune') {
      // Great Dark Spot & white cirrus clouds
      canvas.save();
      final clipPath = Path()..addOval(Rect.fromCircle(center: center, radius: r));
      canvas.clipPath(clipPath);

      final spotX = center.dx + math.cos(rotAngle) * (r * 0.5);
      final spotY = center.dy + 8.0;
      canvas.drawOval(
        Rect.fromCenter(center: Offset(spotX, spotY), width: 18, height: 10),
        Paint()..color = const Color(0xFF0C1947).withValues(alpha: 0.85),
      );

      // White cirrus streak
      canvas.drawLine(
        Offset(center.dx - r * 0.6, center.dy - 12),
        Offset(center.dx + r * 0.7, center.dy - 8),
        Paint()
          ..color = Colors.white.withValues(alpha: 0.5)
          ..strokeWidth = 1.6,
      );
      canvas.restore();
    }

    _drawSpecularHighlight(canvas, center, r);
  }

  /// SAO THỔ (SATURN): Vành đai nghiêng Cassini lấp lánh xoay quanh quả cầu màu cát vàng
  void _drawSaturnWithCassiniRings(Canvas canvas, Offset center, double r) {
    const ringTiltAngle = -0.42; // Nghiêng ~24 độ
    final ringRadiusX = r * 2.3;
    final ringRadiusY = r * 0.70;

    _drawAmbientGlow(canvas, center, r);

    // A. Vẽ nửa sau của vành đai Cassini (phía sau hành tinh)
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(ringTiltAngle);

    // Clip nửa sau (y <= 0)
    canvas.save();
    canvas.clipRect(Rect.fromLTRB(-ringRadiusX * 1.5, -ringRadiusY * 1.5, ringRadiusX * 1.5, 0));
    _paintCassiniRingsGeometry(canvas, Offset.zero, ringRadiusX, ringRadiusY);
    canvas.restore();

    canvas.restore();

    // B. Quả cầu Sao Thổ (Màu vàng cát & dải mây mờ)
    _drawSphereBase(canvas, center, r);

    // Dải mây khí quyển ngang trên bề mặt Sao Thổ
    canvas.save();
    canvas.clipPath(Path()..addOval(Rect.fromCircle(center: center, radius: r)));
    for (int i = -3; i <= 3; i++) {
      final yPos = center.dy + (i * 9.0);
      canvas.drawLine(
        Offset(center.dx - r, yPos),
        Offset(center.dx + r, yPos),
        Paint()
          ..color = (i.isEven ? const Color(0xFFD97706) : const Color(0xFFFEF3C7))
              .withValues(alpha: 0.18)
          ..strokeWidth = 4.0,
      );
    }
    // Bóng đổ của vành đai lên bề mặt hành tinh
    canvas.drawLine(
      Offset(center.dx - r, center.dy + 4),
      Offset(center.dx + r, center.dy - 6),
      Paint()
        ..color = Colors.black.withValues(alpha: 0.38)
        ..strokeWidth = 5.0,
    );
    canvas.restore();

    _drawSpecularHighlight(canvas, center, r);

    // C. Vẽ nửa trước của vành đai Cassini (phía trước hành tinh)
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(ringTiltAngle);

    // Clip nửa trước (y >= 0)
    canvas.save();
    canvas.clipRect(Rect.fromLTRB(-ringRadiusX * 1.5, 0, ringRadiusX * 1.5, ringRadiusY * 1.5));
    _paintCassiniRingsGeometry(canvas, Offset.zero, ringRadiusX, ringRadiusY);

    // Bóng đổ của quả cầu Sao Thổ lên nửa trước vành đai
    canvas.drawOval(
      Rect.fromCenter(center: Offset.zero, width: r * 1.8, height: r * 0.9),
      Paint()
        ..color = Colors.black.withValues(alpha: 0.32)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6),
    );
    canvas.restore();

    canvas.restore();
  }

  void _paintCassiniRingsGeometry(Canvas canvas, Offset center, double rx, double ry) {
    // Vành ngoài A
    canvas.drawOval(
      Rect.fromCenter(center: center, width: rx * 2, height: ry * 2),
      Paint()
        ..color = const Color(0xFFFDE68A).withValues(alpha: 0.65)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 9.0,
    );

    // Khe phân chia Cassini (khoảng trống tối mỏng)
    canvas.drawOval(
      Rect.fromCenter(center: center, width: rx * 1.76, height: ry * 1.76),
      Paint()
        ..color = const Color(0xFF030712).withValues(alpha: 0.90)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.6,
    );

    // Vành trong B (sáng nhất, hổ phách)
    canvas.drawOval(
      Rect.fromCenter(center: center, width: rx * 1.54, height: ry * 1.54),
      Paint()
        ..color = const Color(0xFFFBBF24).withValues(alpha: 0.85)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 14.0,
    );

    // Vành trong cùng C (Crepe ring mờ)
    canvas.drawOval(
      Rect.fromCenter(center: center, width: rx * 1.22, height: ry * 1.22),
      Paint()
        ..color = const Color(0xFFD97706).withValues(alpha: 0.30)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 6.0,
    );
  }

  /// TRÁI ĐẤT (EARTH): Quả cầu xanh đại dương có dải mây trắng xoáy nhẹ và Mặt Trăng bay quanh
  void _drawEarthWithOrbitingMoon(Canvas canvas, Offset center, double r) {
    _drawAmbientGlow(canvas, center, r);

    // 1. Quỹ đạo Mặt Trăng (3D tilted orbit)
    final moonOrbitRx = r * 1.85;
    final moonOrbitRy = r * 0.55;
    final moonAngle = rotationProgress * 2 * math.pi;
    final moonX = center.dx + math.cos(moonAngle) * moonOrbitRx;
    final moonY = center.dy + math.sin(moonAngle) * moonOrbitRy;
    final isMoonBehind = math.sin(moonAngle) < 0;

    // Vẽ Mặt Trăng nếu ở phía sau Trái Đất
    if (isMoonBehind) {
      _drawMoonBody(canvas, Offset(moonX, moonY), 5.5);
    }

    // 2. Quả cầu Trái Đất
    _drawSphereBase(canvas, center, r);

    // Lục địa & Mây xoáy
    canvas.save();
    canvas.clipPath(Path()..addOval(Rect.fromCircle(center: center, radius: r)));

    // Lục địa (màu xanh lục ngọc và đất nhạt trôi theo góc xoay)
    final continentAngle = rotationProgress * 2 * math.pi;
    final continentPaint = Paint()..color = const Color(0xFF10B981).withValues(alpha: 0.70);

    for (int i = 0; i < 3; i++) {
      final continentX = center.dx + math.cos(continentAngle + i * 2.1) * (r * 0.65);
      final continentY = center.dy + (i == 0 ? -10.0 : (i == 1 ? 12.0 : -4.0));
      canvas.drawOval(
        Rect.fromCenter(center: Offset(continentX, continentY), width: 34, height: 22),
        continentPaint,
      );
    }

    // Dải mây trắng xoáy nhẹ trôi theo chiều gió quyển
    final cloudAngle = continentAngle * 1.25;
    final cloudPaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.55)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 4.5
      ..strokeCap = StrokeCap.round;

    for (int y = -2; y <= 2; y++) {
      final offsetWave = math.sin(cloudAngle + y) * 14.0;
      final path = Path()
        ..moveTo(center.dx - r, center.dy + (y * 16) + offsetWave)
        ..quadraticBezierTo(
          center.dx,
          center.dy + (y * 16) - offsetWave,
          center.dx + r,
          center.dy + (y * 16) + offsetWave,
        );
      canvas.drawPath(path, cloudPaint);
    }

    canvas.restore();

    _drawSpecularHighlight(canvas, center, r);

    // 3. Vẽ Mặt Trăng nếu ở phía trước Trái Đất
    if (!isMoonBehind) {
      _drawMoonBody(canvas, Offset(moonX, moonY), 6.5);
    }
  }

  void _drawMoonBody(Canvas canvas, Offset pos, double radius) {
    // Hào quang Mặt Trăng
    canvas.drawCircle(
      pos,
      radius + 2,
      Paint()
        ..color = const Color(0xFFE2E8F0).withValues(alpha: 0.35)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3),
    );

    // Quả cầu Mặt Trăng 3D
    final moonPaint = Paint()
      ..shader = RadialGradient(
        center: const Alignment(-0.3, -0.3),
        colors: const [
          Color(0xFFFFFFFF),
          Color(0xFFCBD5E1),
          Color(0xFF475569),
        ],
      ).createShader(Rect.fromCircle(center: pos, radius: radius));
    canvas.drawCircle(pos, radius, moonPaint);
  }

  /// SAO MỘC (JUPITER): Dải mây khí quyển chuyển động kèm Đốm Đỏ Lớn sắc nét
  void _drawJupiterWithGreatRedSpot(Canvas canvas, Offset center, double r) {
    _drawAmbientGlow(canvas, center, r);
    _drawSphereBase(canvas, center, r);

    canvas.save();
    canvas.clipPath(Path()..addOval(Rect.fromCircle(center: center, radius: r)));

    final rot = rotationProgress * 2 * math.pi;

    // 1. Dải mây khí quyển chuyển động phân tầng (caramel, vàng kim, nâu đất)
    for (int i = -4; i <= 4; i++) {
      final yPos = center.dy + (i * 12.0);
      final isEvenBand = i.isEven;
      final speed = isEvenBand ? 1.0 : -0.8;
      final wave = math.sin(rot * speed + i) * 6.0;

      final color = isEvenBand ? const Color(0xFFB45309) : const Color(0xFFFEF3C7);
      final bandPaint = Paint()
        ..color = color.withValues(alpha: 0.40)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 7.5;

      final path = Path()
        ..moveTo(center.dx - r, yPos + wave)
        ..cubicTo(
          center.dx - r * 0.3,
          yPos - wave * 1.5,
          center.dx + r * 0.3,
          yPos + wave * 1.5,
          center.dx + r,
          yPos - wave,
        );
      canvas.drawPath(path, bandPaint);
    }

    // 2. ĐỐM ĐỎ LỚN (Great Red Spot) sắc nét trôi qua bề mặt
    final spotPhase = (rotationProgress * 1.3) % 1.0;
    final spotAngle = spotPhase * 2 * math.pi;
    final isSpotVisible = math.sin(spotAngle) >= -0.2;

    if (isSpotVisible) {
      final spotX = center.dx + math.cos(spotAngle) * (r * 0.62);
      final spotY = center.dy + (r * 0.32); // Bán cầu Nam
      final spotCenter = Offset(spotX, spotY);

      // Quầng xoáy ngoài
      canvas.drawOval(
        Rect.fromCenter(center: spotCenter, width: 26, height: 16),
        Paint()..color = const Color(0xFF991B1B).withValues(alpha: 0.95),
      );

      // Lõi đỏ cam rực rỡ
      canvas.drawOval(
        Rect.fromCenter(center: spotCenter, width: 18, height: 10),
        Paint()..color = const Color(0xFFEF4444).withValues(alpha: 0.95),
      );

      // Mắt bão xoáy sáng ở tâm
      canvas.drawCircle(
        spotCenter,
        2.5,
        Paint()..color = const Color(0xFFFEE2E2),
      );
    }

    canvas.restore();

    _drawSpecularHighlight(canvas, center, r);
  }

  /// SAO HỎA (MARS): Chỏm băng cực Bắc và bề mặt đỏ gạch nung
  void _drawMarsWithPolarCap(Canvas canvas, Offset center, double r) {
    _drawAmbientGlow(canvas, center, r);
    _drawSphereBase(canvas, center, r);

    canvas.save();
    canvas.clipPath(Path()..addOval(Rect.fromCircle(center: center, radius: r)));

    final rot = rotationProgress * 2 * math.pi;

    // Các mảng tối địa chất & hẻm vực Valles Marineris
    final canyonPaint = Paint()..color = const Color(0xFF7F1D1D).withValues(alpha: 0.65);
    for (int i = 0; i < 3; i++) {
      final cx = center.dx + math.cos(rot + i * 2.0) * (r * 0.5);
      final cy = center.dy + (i == 0 ? 0.0 : (i == 1 ? 16.0 : -12.0));
      canvas.drawOval(
        Rect.fromCenter(center: Offset(cx, cy), width: 28, height: 14),
        canyonPaint,
      );
    }

    // CHỎM BĂNG CỰC BẮC (North Polar Ice Cap)
    final polarCapCenter = Offset(center.dx, center.dy - r * 0.82);
    canvas.drawOval(
      Rect.fromCenter(center: polarCapCenter, width: 34, height: 14),
      Paint()
        ..color = Colors.white
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 1.5),
    );
    canvas.drawOval(
      Rect.fromCenter(center: polarCapCenter, width: 26, height: 9),
      Paint()..color = const Color(0xFFE0F2FE),
    );

    canvas.restore();

    _drawSpecularHighlight(canvas, center, r);
  }

  /// THIÊN VƯƠNG (URANUS): Vành đai dựng đứng góc 90 độ mỏng sáng cyan
  void _drawUranusWithVerticalRing(Canvas canvas, Offset center, double r) {
    _drawAmbientGlow(canvas, center, r);

    final ringRx = r * 0.35;
    final ringRy = r * 1.85;

    // Vành đai sau
    canvas.save();
    canvas.clipRect(Rect.fromLTRB(center.dx - ringRx * 2, center.dy - ringRy, center.dx, center.dy + ringRy));
    canvas.drawOval(
      Rect.fromCenter(center: center, width: ringRx * 2, height: ringRy * 2),
      Paint()
        ..color = const Color(0xFF06B6D4).withValues(alpha: 0.5)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3.5,
    );
    canvas.restore();

    // Quả cầu
    _drawSphereBase(canvas, center, r);
    _drawSpecularHighlight(canvas, center, r);

    // Vành đai trước
    canvas.save();
    canvas.clipRect(Rect.fromLTRB(center.dx, center.dy - ringRy, center.dx + ringRx * 2, center.dy + ringRy));
    canvas.drawOval(
      Rect.fromCenter(center: center, width: ringRx * 2, height: ringRy * 2),
      Paint()
        ..color = const Color(0xFF22D3EE).withValues(alpha: 0.85)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3.5,
    );
    canvas.restore();
  }

  void _drawAmbientGlow(Canvas canvas, Offset center, double r) {
    canvas.drawCircle(
      center,
      r + 16,
      Paint()
        ..color = planet.glowColor.withValues(alpha: 0.22)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 16),
    );
  }

  void _drawSphereBase(Canvas canvas, Offset center, double r) {
    final spherePaint = Paint()
      ..shader = RadialGradient(
        center: const Alignment(-0.35, -0.35),
        radius: 0.95,
        colors: [
          planet.primaryColor,
          planet.darkColor,
          const Color(0xFF030712),
        ],
        stops: const [0.0, 0.65, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: r));

    canvas.drawCircle(center, r, spherePaint);
  }

  void _drawSpecularHighlight(Canvas canvas, Offset center, double r) {
    // Top-left light reflection highlight
    final highlightPos = center + Offset(-r * 0.32, -r * 0.32);
    canvas.drawCircle(
      highlightPos,
      r * 0.38,
      Paint()
        ..color = Colors.white.withValues(alpha: 0.28)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8),
    );

    // Fresnel rim glow
    canvas.drawCircle(
      center,
      r,
      Paint()
        ..color = planet.glowColor.withValues(alpha: 0.35)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.8,
    );
  }

  void _drawHolographicScanSweep(Canvas canvas, Offset center, Size size) {
    final scanY = (rotationProgress * size.height) % size.height;
    final sweepPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          Colors.transparent,
          planet.glowColor.withValues(alpha: 0.15),
          Colors.transparent,
        ],
        stops: const [0.0, 0.5, 1.0],
      ).createShader(Rect.fromLTWH(0, scanY - 16, size.width, 32));

    canvas.drawRect(Rect.fromLTWH(0, scanY - 16, size.width, 32), sweepPaint);

    // Scanline laser edge
    canvas.drawLine(
      Offset(0, scanY),
      Offset(size.width, scanY),
      Paint()
        ..color = planet.glowColor.withValues(alpha: 0.35)
        ..strokeWidth = 1.0,
    );
  }

  @override
  bool shouldRepaint(covariant _PlanetHologram3DPainter oldDelegate) {
    return oldDelegate.rotationProgress != rotationProgress ||
        oldDelegate.planet.id != planet.id;
  }
}
