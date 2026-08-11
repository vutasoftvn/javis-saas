import 'package:flutter/material.dart';
import '../../../../../core/theme/app_theme.dart';

class AnalysisBadge extends StatelessWidget {
  final String text;
  final Color color;

  const AnalysisBadge({
    super.key,
    required this.text,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    final translatedLabel = getBadgeLabel(text);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Text(
        translatedLabel,
        style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold),
      ),
    );
  }

  static String getBadgeLabel(String? text) {
    if (text == null || text.isEmpty) return '';
    switch (text.toUpperCase()) {
      case 'POSITIVE':
      case 'TÍCH CỰC':
        return 'Tích cực';
      case 'NEUTRAL':
      case 'TRUNG TÍNH':
        return 'Trung tính';
      case 'NEGATIVE':
      case 'TIÊU CỰC':
        return 'Tiêu cực';
      case 'HIGH':
      case 'CAO':
        return 'Cao';
      case 'MEDIUM':
      case 'TRUNG BÌNH':
        return 'Trung bình';
      case 'LOW':
      case 'THẤP':
        return 'Thấp';
      case 'HYPOTHESIZED':
      case 'GIẢ ĐỊNH':
        return 'Giả định';
      case 'VERIFIED':
      case 'ĐÃ XÁC THỰC':
        return 'Đã xác thực';
      case 'VALIDATED':
      case 'ĐÃ KIỂM CHỨNG':
        return 'Đã kiểm chứng';
      default:
        return text;
    }
  }
}

String getPestelFactorLabel(String? factor) {
  if (factor == null || factor.isEmpty) return 'Chính trị';
  switch (factor.toUpperCase()) {
    case 'POLITICAL':
    case 'CHÍNH TRỊ':
      return 'Chính trị';
    case 'ECONOMIC':
    case 'KINH TẾ':
      return 'Kinh tế';
    case 'SOCIAL':
    case 'XÃ HỘI':
      return 'Xã hội';
    case 'TECHNOLOGICAL':
    case 'CÔNG NGHỆ':
      return 'Công nghệ';
    case 'ENVIRONMENTAL':
    case 'MÔI TRƯỜNG':
      return 'Môi trường';
    case 'LEGAL':
    case 'PHÁP LÝ':
      return 'Pháp lý';
    default:
      return factor;
  }
}

Color getFactorColor(String factor) {
  switch (factor.toUpperCase()) {
    case 'POLITICAL':
    case 'CHÍNH TRỊ':
      return const Color(0xFF3B82F6);
    case 'ECONOMIC':
    case 'KINH TẾ':
      return const Color(0xFF10B981);
    case 'SOCIAL':
    case 'XÃ HỘI':
      return const Color(0xFFF59E0B);
    case 'TECHNOLOGICAL':
    case 'CÔNG NGHỆ':
      return const Color(0xFF8B5CF6);
    case 'ENVIRONMENTAL':
    case 'MÔI TRƯỜNG':
      return const Color(0xFF06B6D4);
    case 'LEGAL':
    case 'PHÁP LÝ':
      return const Color(0xFFEC4899);
    default:
      return AppTheme.primary;
  }
}

String getSwotCategoryLabel(String? category) {
  if (category == null || category.isEmpty) return 'Điểm mạnh (Strengths)';
  switch (category.toUpperCase()) {
    case 'STRENGTH':
    case 'STRENGTHS':
    case 'ĐIỂM MẠNH':
      return 'Điểm mạnh (Strengths)';
    case 'WEAKNESS':
    case 'WEAKNESSES':
    case 'ĐIỂM YẾU':
      return 'Điểm yếu (Weaknesses)';
    case 'OPPORTUNITY':
    case 'OPPORTUNITIES':
    case 'CƠ HỘI':
      return 'Cơ hội (Opportunities)';
    case 'THREAT':
    case 'THREATS':
    case 'THÁCH THỨC':
      return 'Thách thức (Threats)';
    default:
      return category;
  }
}

Color getSwotCategoryColor(String category) {
  switch (category.toUpperCase()) {
    case 'STRENGTH':
    case 'STRENGTHS':
    case 'ĐIỂM MẠNH':
      return const Color(0xFF10B981);
    case 'WEAKNESS':
    case 'WEAKNESSES':
    case 'ĐIỂM YẾU':
      return const Color(0xFFEF4444);
    case 'OPPORTUNITY':
    case 'OPPORTUNITIES':
    case 'CƠ HỘI':
      return const Color(0xFF3B82F6);
    case 'THREAT':
    case 'THREATS':
    case 'THÁCH THỨC':
      return const Color(0xFFF59E0B);
    default:
      return AppTheme.primary;
  }
}

String getTowsQuadrantLabel(String? quadrant) {
  if (quadrant == null || quadrant.isEmpty) return 'Chiến lược SO (Tận dụng cơ hội)';
  switch (quadrant.toUpperCase()) {
    case 'SO':
      return 'Chiến lược SO (Tận dụng cơ hội)';
    case 'ST':
      return 'Chiến lược ST (Vượt qua thách thức)';
    case 'WO':
      return 'Chiến lược WO (Khắc phục điểm yếu)';
    case 'WT':
      return 'Chiến lược WT (Tối thiểu hóa rủi ro)';
    default:
      return quadrant;
  }
}

Color getTowsQuadrantColor(String quadrant) {
  switch (quadrant.toUpperCase()) {
    case 'SO':
      return const Color(0xFF10B981);
    case 'ST':
      return const Color(0xFF3B82F6);
    case 'WO':
      return const Color(0xFFF59E0B);
    case 'WT':
      return const Color(0xFFEF4444);
    default:
      return AppTheme.primary;
  }
}
