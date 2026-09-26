from __future__ import annotations

from pydantic import BaseModel, Field

from agent.prompts.locale import DEFAULT_LOCALE, render_locale_policy

__all__ = ["PLATFORM_POLICY", "PromptBundle"]

# Blueprint V2 §68.2 — platform_policy.en.md: phần bất biến, áp dụng cho MỌI agent,
# không phải nội dung riêng của từng AgentSpec.
PLATFORM_POLICY = (
    "You are an AI agent operating inside COSA, a Founder/Company Operating System. "
    "Every mutating or financial action must go through the platform's capability "
    "gateway and may require human approval — never claim an action succeeded unless "
    "the tool result confirms it. Do not fabricate data; if information is unavailable, "
    "say so explicitly."
)


class PromptBundle(BaseModel):
    """Compose prompt từ các section có kiểu (Blueprint V2 §68.2), thay vì 1 giant
    prompt string. Không lưu private chain-of-thought — chỉ compose instruction/
    policy, không phải nơi lưu reasoning trung gian của model."""

    platform_policy: str = PLATFORM_POLICY
    agent_instructions: str = ""
    skill_instructions: list[str] = Field(default_factory=list)
    # Ngữ cảnh phiên đã được nền tảng verify (workspace/project) để model không phải hỏi lại.
    session_context: dict[str, str] = Field(default_factory=dict)
    locale: str = DEFAULT_LOCALE

    def render(self) -> str:
        sections = [self.platform_policy]
        if self.agent_instructions:
            sections.append(self.agent_instructions)
        for skill_text in self.skill_instructions:
            sections.append(skill_text)
        # Bỏ giá trị rỗng; gộp xuống dòng thành khoảng trắng để giá trị không
        # chèn được dòng chỉ thị mới vào prompt. Không còn dòng nào -> bỏ section.
        lines = [
            f"- {k}: {' '.join(str(v).split())}"
            for k, v in self.session_context.items()
            if v and str(v).strip()
        ]
        if lines:
            sections.append(
                "Session context (verified by the platform):\n"
                + "\n".join(lines)
                + "\nDo not ask the user for these values; use them when calling tools."
            )
        sections.append(render_locale_policy(self.locale))
        return "\n\n".join(sections)
