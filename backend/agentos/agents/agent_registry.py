from __future__ import annotations

from dataclasses import dataclass, field

from agentos.core.agent import Agent


@dataclass
class AgentRecord:
    agent_key: str
    agent: Agent
    domain: str
    intents: list[str] = field(default_factory=list)


class AgentNotFoundError(Exception):
    def __init__(self, agent_key: str) -> None:
        super().__init__(f"Agent not registered: {agent_key}")
        self.agent_key = agent_key


class AgentRegistry:
    """In-process registry of live Agent instances available for
    delegation (blueprint §9/§10). Unlike SkillRegistry (Phase 4), there
    is no filesystem discovery — agents are code objects constructed and
    registered explicitly by whoever assembles the multi-agent topology.
    """

    def __init__(self) -> None:
        self._records: dict[str, AgentRecord] = {}

    def register(self, agent_key: str, agent: Agent, *, domain: str, intents: list[str]) -> None:
        self._records[agent_key] = AgentRecord(agent_key=agent_key, agent=agent, domain=domain, intents=intents)

    def get(self, agent_key: str) -> AgentRecord:
        try:
            return self._records[agent_key]
        except KeyError:
            raise AgentNotFoundError(agent_key) from None

    def list(self, *, domain: str | None = None) -> list[AgentRecord]:
        records = list(self._records.values())
        if domain is not None:
            records = [r for r in records if r.domain == domain]
        return records
