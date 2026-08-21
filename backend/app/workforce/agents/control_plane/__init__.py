"""Control Plane models (AgentGoal, AgentPlan, AgentPlanStep).

G3 §3/§9.6: the GoalDecomposer/ControlPlanePlanner/ControlPlaneExecutionManager/
DomainCapabilityRouter engine that used to live in this package (planner.py,
execution.py, router.py, router_api.py, context.py, evaluator.py) was a third,
disconnected Mission/Plan/execution engine — confirmed unreachable from any
mounted route (its own FastAPI router was only wired through the unmounted
`agents/gateway/router.py`) and exercised only by its own tests. Removed
outright rather than kept as dead weight; the canonical execution chain is
`app.workforce.agents.orchestration.service` (`AdkCofounderWorkflow`).

The models themselves are kept — they back real, still-used tables (consumed
by `app.workforce.agents.jobs.job_router.route_to_job`).

G3 Phase 1E: `AgentMemoryItem` (table `agent_business_memories`), formerly
also defined here, has been retired — zero production readers, one writer
(`app.workforce.agents.learning.verifier.LearningWriter`), now redirected to
`app.workforce.memory.AgentMemoryEntry` instead of a separate table.
"""
