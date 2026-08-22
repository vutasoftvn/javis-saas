from __future__ import annotations

from agentos.core.agent import Agent
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext

DEFAULT_MAX_ROUNDS = 2


class DebateLoop:
    """Generator/Critic multi-agent flow (blueprint §9.2): the generator
    produces a draft, the critic reviews it, and — if the critic's
    verdict isn't a bare "approved" — the generator revises using the
    critique as its next goal. Stops after max_rounds even if the critic
    never approves, so this can't loop forever.
    """

    def __init__(self, generator: Agent, critic: Agent, *, max_rounds: int = DEFAULT_MAX_ROUNDS) -> None:
        self._generator = generator
        self._critic = critic
        self._max_rounds = max_rounds

    async def run(self, task: TaskContext) -> tuple[AgentResult, AgentResult]:
        draft_task = task
        generator_result = await self._generator.run(draft_task)
        critic_result = await self._critic.run(
            draft_task.model_copy(update={"goal": f"Critique this: {generator_result.output}"})
        )

        rounds = 1
        while (
            rounds < self._max_rounds
            and generator_result.status == AgentRunStatus.COMPLETED
            and critic_result.status == AgentRunStatus.COMPLETED
            and (critic_result.output or "").strip().lower() != "approved"
        ):
            revision_goal = (
                f"Revise this: {generator_result.output}\nBased on this feedback: {critic_result.output}"
            )
            generator_result = await self._generator.run(draft_task.model_copy(update={"goal": revision_goal}))
            critic_result = await self._critic.run(
                draft_task.model_copy(update={"goal": f"Critique this: {generator_result.output}"})
            )
            rounds += 1

        return generator_result, critic_result
