from typing import Any, Dict, Optional


class LearningEvaluationCapability:
    """Evaluation capability for measuring learning loop velocity and organizational adoption."""

    @classmethod
    def evaluate_learning_velocity(
        cls,
        total_lessons: int = 5,
        confirmed_lessons: int = 4,
        applied_lessons: int = 3,
    ) -> Dict[str, Any]:
        adoption_rate = (applied_lessons / total_lessons) if total_lessons > 0 else 0.0
        return {
            "status": "success",
            "total_lessons": total_lessons,
            "confirmed_lessons": confirmed_lessons,
            "applied_lessons": applied_lessons,
            "adoption_rate": round(adoption_rate, 2),
            "summary": f"Learning adoption rate is {int(adoption_rate * 100)}% across active cycles.",
        }
