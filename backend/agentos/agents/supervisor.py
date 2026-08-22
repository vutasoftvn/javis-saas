from __future__ import annotations

import re
import uuid

from agentos.agents.agent_registry import AgentRegistry
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(text.lower()))


def score_agent(goal: str, intents: list[str]) -> float:
    """Naive term-overlap relevance score in [0, 1] — same MVP approach as
    agentos.memory.retrieval.score_relevance (Phase 3) and
    agentos.skills.router.score_skill (Phase 4), applied here to agent
    capability matching (blueprint §9 Supervisor pattern).
    """
    goal_tokens = _tokenize(goal)
    intent_tokens: set[str] = set()
    for intent in intents:
        intent_tokens |= _tokenize(intent)
    if not goal_tokens or not intent_tokens:
        return 0.0
    return len(goal_tokens & intent_tokens) / len(goal_tokens)


class SupervisorAgent:
    """Supervisor pattern (blueprint §9.2): picks the best-scoring
    specialist from an AgentRegistry and delegates the entire task to it.
    Implements the Agent protocol itself, so a SupervisorAgent can be
    nested as a specialist under another SupervisorAgent if a topology
    ever needs that.
    """

    def __init__(self, registry: AgentRegistry, *, domain: str | None = None) -> None:
        self._registry = registry
        self._domain = domain

    async def run(self, task: TaskContext) -> AgentResult:
        candidates = self._registry.list(domain=self._domain)
        scored = [(score_agent(task.goal, record.intents), record) for record in candidates]
        relevant = [(score, record) for score, record in scored if score > 0]
        if not relevant:
            return AgentResult(
                run_id=str(uuid.uuid4()),
                status=AgentRunStatus.FAILED,
                error=f"No registered specialist scored above zero for goal: {task.goal!r}",
            )
        relevant.sort(key=lambda pair: pair[0], reverse=True)
        _, chosen = relevant[0]
        return await chosen.agent.run(task)
