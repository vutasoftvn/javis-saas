from __future__ import annotations

from typing import Any

__all__ = ["ArtifactSynthesis"]


class ArtifactSynthesis:
    """Primitive tổng hợp kết quả từ nhiều specialist thành 1 báo cáo / response hoàn chỉnh."""

    def synthesize(
        self,
        mission_goal: str,
        specialist_outputs: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sections = []
        for domain, output in specialist_outputs.items():
            content = output if isinstance(output, str) else str(output.get("output") or output)
            sections.append(f"### Domain [{domain.upper()}]:\n{content}")

        synthesis_text = f"## Mission Synthesis for: {mission_goal}\n\n" + "\n\n".join(sections)
        return {
            "mission_goal": mission_goal,
            "synthesized_response": synthesis_text,
            "domain_results": specialist_outputs,
            "contributing_domains": list(specialist_outputs.keys()),
        }
