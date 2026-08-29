import 'package:flutter/material.dart';

class ActivationStepIndicators extends StatelessWidget {
  final int currentStep;
  final ValueChanged<int> onSelectStep;

  const ActivationStepIndicators({
    super.key,
    required this.currentStep,
    required this.onSelectStep,
  });

  @override
  Widget build(BuildContext context) {
    final stepTitles = [
      '1. Hồ sơ Doanh nghiệp',
      '2. Định vị Dự án',
      '3. Nạp Tri thức & JTBD',
      '4. AI Chẩn đoán',
    ];

    return Row(
      children: List.generate(4, (index) {
        final isCompleted = index < currentStep;
        final isActive = index == currentStep;
        final color = isCompleted
            ? const Color(0xFF10B981)
            : (isActive ? const Color(0xFF0EA5E9) : const Color(0xFF475569));

        return Expanded(
          child: InkWell(
            onTap: () => onSelectStep(index),
            borderRadius: BorderRadius.circular(8),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 8),
              margin: const EdgeInsets.symmetric(horizontal: 3),
              decoration: BoxDecoration(
                color: isActive ? color.withValues(alpha: 0.15) : Colors.transparent,
                borderRadius: BorderRadius.circular(8),
                border: Border(
                  bottom: BorderSide(
                    color: color,
                    width: isActive ? 2.5 : 1.5,
                  ),
                ),
              ),
              child: Row(
                children: [
                  Container(
                    width: 20,
                    height: 20,
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.2),
                      shape: BoxShape.circle,
                      border: Border.all(color: color),
                    ),
                    child: Center(
                      child: isCompleted
                          ? const Icon(Icons.check, size: 12, color: Color(0xFF10B981))
                          : Text(
                              '${index + 1}',
                              style: TextStyle(
                                color: color,
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      stepTitles[index],
                      style: TextStyle(
                        color: isActive ? Colors.white : const Color(0xFF94A3B8),
                        fontSize: 11,
                        fontWeight: isActive ? FontWeight.bold : FontWeight.w500,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      }),
    );
  }
}
