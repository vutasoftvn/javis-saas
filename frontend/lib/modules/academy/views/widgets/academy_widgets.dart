import 'package:flutter/material.dart';
import '../../models/academy_models.dart';

/// Displays a permanent synthetic disclaimer banner.
///
/// MUST be shown on every simulation result and template export.
/// Cannot be dismissed or hidden by user action.
class SyntheticDisclaimerBanner extends StatelessWidget {
  final String disclaimer;

  const SyntheticDisclaimerBanner({
    super.key,
    this.disclaimer =
        'Kết quả mô phỏng học tập – KHÔNG phải evidence thực. '
        'Cần con người thay thế nguồn tham chiếu bằng dữ liệu thực tế.',
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF78350F).withValues(alpha: 0.18),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFF59E0B), width: 1.2),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.school_rounded, size: 18, color: Color(0xFFF59E0B)),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Học tập / Mô phỏng',
                  style: TextStyle(
                    color: Color(0xFFF59E0B),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  disclaimer,
                  style: const TextStyle(
                    color: Color(0xFFFEF3C7),
                    fontSize: 12,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Lesson progress card — no lifecycle stage, no project reference.
class LessonProgressCard extends StatelessWidget {
  final AcademyLesson lesson;
  final bool isCompleted;
  final VoidCallback onTap;

  const LessonProgressCard({
    super.key,
    required this.lesson,
    required this.isCompleted,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: isCompleted
              ? const Color(0xFF052E16).withValues(alpha: 0.6)
              : const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isCompleted ? const Color(0xFF34D399) : const Color(0xFF334155),
          ),
        ),
        child: Row(
          children: [
            Icon(
              isCompleted ? Icons.check_circle_rounded : Icons.radio_button_unchecked,
              size: 20,
              color: isCompleted ? const Color(0xFF34D399) : Colors.grey,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    lesson.title,
                    style: TextStyle(
                      color: isCompleted ? const Color(0xFF34D399) : Colors.white,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    lesson.practiceType,
                    style: const TextStyle(color: Colors.grey, fontSize: 11.5),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Simulation workspace widget — shows synthetic result with mandatory disclaimer.
class SimulationWorkspace extends StatelessWidget {
  final AcademySimulationResult result;

  const SimulationWorkspace({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Mandatory disclaimer — cannot be dismissed
        SyntheticDisclaimerBanner(disclaimer: result.disclaimer),
        const SizedBox(height: 14),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xFF0F172A),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: const Color(0xFF334155)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.science_rounded, size: 16, color: Color(0xFF818CF8)),
                  const SizedBox(width: 8),
                  Text(
                    'Phiên mô phỏng: ${result.scenarioVersion}',
                    style: const TextStyle(
                      color: Color(0xFF818CF8),
                      fontSize: 12.5,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                'Attempt ID: ${result.attemptId}',
                style: const TextStyle(color: Colors.grey, fontSize: 11, fontFamily: 'monospace'),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
