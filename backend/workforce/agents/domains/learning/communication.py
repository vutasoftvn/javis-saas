from typing import Any, Dict, List, Optional


class LearningCommunicationCapability:
    """Communication capability for formatting operating playbook recommendations and team retrospectives."""

    @classmethod
    def format_playbook_update(
        cls,
        lesson_title: str,
        recommendations: List[str],
    ) -> Dict[str, Any]:
        return {
            "status": "success",
            "playbook_section": lesson_title,
            "formatted_playbook": "\n".join(f"- {r}" for r in recommendations),
            "summary": f"Formatted playbook update for '{lesson_title}'.",
        }
