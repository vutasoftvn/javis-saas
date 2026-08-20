# Harness Ownership Consumer Report

This report is evidence for migration ordering. It does not authorize deletion.

## backend/agent_runtime/runtime

### Consumers

- non-production consumer: backend/agent_runtime/runtime/__init__.py imports agent_runtime.runtime.base
- test-only consumer: backend/app/tests/e2e/test_phase9_e2e_integration.py imports agent_runtime.runtime.base
- test-only consumer: backend/app/tests/unit/test_phase1_core_contracts.py imports agent_runtime.runtime.base
- test-only consumer: backend/app/tests/unit/test_phase6_agent_profiles.py imports agent_runtime.runtime.base

## backend/agent_runtime/models

### Consumers

- non-production consumer: backend/agent_runtime/models/__init__.py imports agent_runtime.models.base
- non-production consumer: backend/agent_runtime/models/__init__.py imports agent_runtime.models.gateway
- non-production consumer: backend/agent_runtime/models/__init__.py imports agent_runtime.models.providers
- non-production consumer: backend/agent_runtime/models/gateway.py imports agent_runtime.models.base
- non-production consumer: backend/agent_runtime/models/gateway.py imports agent_runtime.models.providers
- non-production consumer: backend/agent_runtime/models/providers/__init__.py imports agent_runtime.models.providers.anthropic_provider
- non-production consumer: backend/agent_runtime/models/providers/__init__.py imports agent_runtime.models.providers.deepseek_provider
- non-production consumer: backend/agent_runtime/models/providers/__init__.py imports agent_runtime.models.providers.openai_provider
- non-production consumer: backend/agent_runtime/models/providers/anthropic_provider.py imports agent_runtime.models.base
- non-production consumer: backend/agent_runtime/models/providers/deepseek_provider.py imports agent_runtime.models.base
- non-production consumer: backend/agent_runtime/models/providers/openai_provider.py imports agent_runtime.models.base
- test-only consumer: backend/app/tests/e2e/test_phase9_e2e_integration.py imports agent_runtime.models.base
- test-only consumer: backend/app/tests/e2e/test_phase9_e2e_integration.py imports agent_runtime.models.gateway
- test-only consumer: backend/app/tests/unit/test_phase1_core_contracts.py imports agent_runtime.models.base
- test-only consumer: backend/app/tests/unit/test_phase7_adapters_executors.py imports agent_runtime.models.base
- test-only consumer: backend/app/tests/unit/test_phase7_adapters_executors.py imports agent_runtime.models.gateway

## backend/agent_runtime/context

### Consumers

- non-production consumer: backend/agent_runtime/context/__init__.py imports agent_runtime.context.base
- non-production consumer: backend/agent_runtime/context/__init__.py imports agent_runtime.context.context_engine
- non-production consumer: backend/agent_runtime/context/__init__.py imports agent_runtime.context.resolvers
- non-production consumer: backend/agent_runtime/context/context_engine.py imports agent_runtime.context.base
- non-production consumer: backend/agent_runtime/context/context_engine.py imports agent_runtime.context.resolvers.company_resolver
- non-production consumer: backend/agent_runtime/context/context_engine.py imports agent_runtime.context.resolvers.knowledge_resolver
- non-production consumer: backend/agent_runtime/context/context_engine.py imports agent_runtime.context.resolvers.project_resolver
- non-production consumer: backend/agent_runtime/context/context_engine.py imports agent_runtime.context.resolvers.startup_stage_resolver
- non-production consumer: backend/agent_runtime/context/resolvers/__init__.py imports agent_runtime.context.resolvers.company_resolver
- non-production consumer: backend/agent_runtime/context/resolvers/__init__.py imports agent_runtime.context.resolvers.knowledge_resolver
- non-production consumer: backend/agent_runtime/context/resolvers/__init__.py imports agent_runtime.context.resolvers.project_resolver
- non-production consumer: backend/agent_runtime/context/resolvers/__init__.py imports agent_runtime.context.resolvers.startup_stage_resolver
- test-only consumer: backend/app/tests/e2e/test_phase9_e2e_integration.py imports agent_runtime.context.base
- test-only consumer: backend/app/tests/e2e/test_phase9_e2e_integration.py imports agent_runtime.context.context_engine
- test-only consumer: backend/app/tests/unit/test_phase1_core_contracts.py imports agent_runtime.context.base
- test-only consumer: backend/app/tests/unit/test_phase3_intent_context.py imports agent_runtime.context.base
- test-only consumer: backend/app/tests/unit/test_phase3_intent_context.py imports agent_runtime.context.context_engine

## backend/agent_runtime/routing

### Consumers

- non-production consumer: backend/agent_runtime/context/context_engine.py imports agent_runtime.routing.base
- non-production consumer: backend/agent_runtime/routing/__init__.py imports agent_runtime.routing.base
- non-production consumer: backend/agent_runtime/routing/__init__.py imports agent_runtime.routing.capability_resolver
- non-production consumer: backend/agent_runtime/routing/__init__.py imports agent_runtime.routing.intent_router
- non-production consumer: backend/agent_runtime/routing/capability_resolver.py imports agent_runtime.routing.base
- non-production consumer: backend/agent_runtime/routing/intent_router.py imports agent_runtime.routing.base
- test-only consumer: backend/app/tests/e2e/test_phase9_e2e_integration.py imports agent_runtime.routing.base
- test-only consumer: backend/app/tests/e2e/test_phase9_e2e_integration.py imports agent_runtime.routing.capability_resolver
- test-only consumer: backend/app/tests/e2e/test_phase9_e2e_integration.py imports agent_runtime.routing.intent_router
- test-only consumer: backend/app/tests/unit/test_phase1_core_contracts.py imports agent_runtime.routing.base
- test-only consumer: backend/app/tests/unit/test_phase3_intent_context.py imports agent_runtime.routing.base
- test-only consumer: backend/app/tests/unit/test_phase3_intent_context.py imports agent_runtime.routing.capability_resolver
- test-only consumer: backend/app/tests/unit/test_phase3_intent_context.py imports agent_runtime.routing.intent_router

## backend/agent_runtime/trajectory

### Consumers

- non-production consumer: backend/agent_runtime/trajectory/__init__.py imports agent_runtime.trajectory.models
- non-production consumer: backend/agent_runtime/trajectory/__init__.py imports agent_runtime.trajectory.trajectory_builder
- non-production consumer: backend/agent_runtime/trajectory/trajectory_builder.py imports agent_runtime.trajectory.models
- test-only consumer: backend/app/tests/e2e/test_phase9_e2e_integration.py imports agent_runtime.trajectory.trajectory_builder
- test-only consumer: backend/app/tests/unit/test_phase2_event_session.py imports agent_runtime.trajectory.models
- test-only consumer: backend/app/tests/unit/test_phase2_event_session.py imports agent_runtime.trajectory.trajectory_builder

## backend/tools

### Consumers

- non-production consumer: backend/agent_runtime/permissions/base.py imports tools.base
- test-only consumer: backend/app/tests/e2e/test_phase9_e2e_integration.py imports tools.dispatcher
- test-only consumer: backend/app/tests/e2e/test_phase9_e2e_integration.py imports tools.finance
- test-only consumer: backend/app/tests/e2e/test_phase9_e2e_integration.py imports tools.hostinger
- test-only consumer: backend/app/tests/e2e/test_phase9_e2e_integration.py imports tools.registry
- test-only consumer: backend/app/tests/unit/test_phase1_core_contracts.py imports tools.base
- test-only consumer: backend/app/tests/unit/test_phase4_tool_registry.py imports tools.base
- test-only consumer: backend/app/tests/unit/test_phase4_tool_registry.py imports tools.dispatcher
- test-only consumer: backend/app/tests/unit/test_phase4_tool_registry.py imports tools.registry
- test-only consumer: backend/app/tests/unit/test_phase5_skills_workflows.py imports tools.dispatcher
- test-only consumer: backend/app/tests/unit/test_phase5_skills_workflows.py imports tools.registry
- non-production consumer: backend/tools/__init__.py imports tools.base
- non-production consumer: backend/tools/__init__.py imports tools.crm
- non-production consumer: backend/tools/__init__.py imports tools.dispatcher
- non-production consumer: backend/tools/__init__.py imports tools.filesystem
- non-production consumer: backend/tools/__init__.py imports tools.finance
- non-production consumer: backend/tools/__init__.py imports tools.hostinger
- non-production consumer: backend/tools/__init__.py imports tools.knowledge
- non-production consumer: backend/tools/__init__.py imports tools.n8n
- non-production consumer: backend/tools/__init__.py imports tools.registry
- non-production consumer: backend/tools/__init__.py imports tools.shell
- non-production consumer: backend/tools/__init__.py imports tools.web
- non-production consumer: backend/tools/crm/__init__.py imports tools.crm.lead_tools
- non-production consumer: backend/tools/crm/lead_tools.py imports tools.base
- non-production consumer: backend/tools/dispatcher.py imports tools.base
- non-production consumer: backend/tools/dispatcher.py imports tools.registry
- non-production consumer: backend/tools/filesystem/__init__.py imports tools.filesystem.file_ops
- non-production consumer: backend/tools/filesystem/file_ops.py imports tools.base
- non-production consumer: backend/tools/finance/__init__.py imports tools.finance.financial_tools
- non-production consumer: backend/tools/finance/financial_tools.py imports tools.base
- non-production consumer: backend/tools/hostinger/__init__.py imports tools.hostinger.deploy_tools
- non-production consumer: backend/tools/hostinger/deploy_tools.py imports tools.base
- non-production consumer: backend/tools/knowledge/__init__.py imports tools.knowledge.search_tools
- non-production consumer: backend/tools/knowledge/search_tools.py imports tools.base
- non-production consumer: backend/tools/n8n/__init__.py imports tools.n8n.trigger
- non-production consumer: backend/tools/n8n/trigger.py imports tools.base
- non-production consumer: backend/tools/registry.py imports tools.base
- non-production consumer: backend/tools/shell/__init__.py imports tools.shell.sandboxed_shell
- non-production consumer: backend/tools/shell/sandboxed_shell.py imports tools.base
- non-production consumer: backend/tools/web/__init__.py imports tools.web.search
- non-production consumer: backend/tools/web/search.py imports tools.base
- non-production consumer: backend/workflows/engine.py imports tools.dispatcher
- non-production consumer: services/realtime_agent/agent.py imports tools
- non-production consumer: services/realtime_agent/tests/test_tools.py imports tools
- non-production consumer: services/realtime_agent/tests/test_tools.py imports tools
- non-production consumer: services/realtime_agent/tests/test_tools.py imports tools
- non-production consumer: services/realtime_agent/tests/test_tools.py imports tools
- non-production consumer: services/realtime_agent/tests/test_tools.py imports tools
- non-production consumer: services/realtime_agent/tests/test_tools.py imports tools
- non-production consumer: services/realtime_agent/tests/test_tools.py imports tools

## backend/skills

### Consumers

- test-only consumer: backend/app/tests/unit/test_phase1_core_contracts.py imports skills.base
- test-only consumer: backend/app/tests/unit/test_phase5_skills_workflows.py imports skills.repository
- non-production consumer: backend/skills/__init__.py imports skills.base
- non-production consumer: backend/skills/__init__.py imports skills.definitions
- non-production consumer: backend/skills/__init__.py imports skills.repository
- non-production consumer: backend/skills/definitions/__init__.py imports skills.definitions.coding_refactor
- non-production consumer: backend/skills/definitions/__init__.py imports skills.definitions.lead_generation
- non-production consumer: backend/skills/definitions/__init__.py imports skills.definitions.market_research
- non-production consumer: backend/skills/definitions/__init__.py imports skills.definitions.okr_setting
- non-production consumer: backend/skills/definitions/__init__.py imports skills.definitions.pmf_discovery
- non-production consumer: backend/skills/definitions/__init__.py imports skills.definitions.tt58_audit
- non-production consumer: backend/skills/definitions/coding_refactor.py imports skills.base
- non-production consumer: backend/skills/definitions/lead_generation.py imports skills.base
- non-production consumer: backend/skills/definitions/market_research.py imports skills.base
- non-production consumer: backend/skills/definitions/okr_setting.py imports skills.base
- non-production consumer: backend/skills/definitions/pmf_discovery.py imports skills.base
- non-production consumer: backend/skills/definitions/tt58_audit.py imports skills.base
- non-production consumer: backend/skills/repository.py imports skills.base
- non-production consumer: backend/skills/repository.py imports skills.definitions
- non-production consumer: backend/workflows/engine.py imports skills.repository

## backend/workflows

### Consumers

- test-only consumer: backend/app/tests/unit/test_phase1_core_contracts.py imports workflows.base
- test-only consumer: backend/app/tests/unit/test_phase5_skills_workflows.py imports workflows.definitions
- test-only consumer: backend/app/tests/unit/test_phase5_skills_workflows.py imports workflows.engine
- non-production consumer: backend/workflows/__init__.py imports workflows.base
- non-production consumer: backend/workflows/__init__.py imports workflows.definitions
- non-production consumer: backend/workflows/__init__.py imports workflows.engine
- non-production consumer: backend/workflows/definitions/__init__.py imports workflows.definitions.financial_health
- non-production consumer: backend/workflows/definitions/__init__.py imports workflows.definitions.lead_outreach
- non-production consumer: backend/workflows/definitions/__init__.py imports workflows.definitions.market_analysis
- non-production consumer: backend/workflows/definitions/financial_health.py imports workflows.base
- non-production consumer: backend/workflows/definitions/lead_outreach.py imports workflows.base
- non-production consumer: backend/workflows/definitions/market_analysis.py imports workflows.base
- non-production consumer: backend/workflows/engine.py imports workflows.base

## backend/executors

### Consumers

- test-only consumer: backend/app/tests/unit/test_phase1_core_contracts.py imports executors.base
- test-only consumer: backend/app/tests/unit/test_phase7_adapters_executors.py imports executors.base
- test-only consumer: backend/app/tests/unit/test_phase7_adapters_executors.py imports executors.registry
- non-production consumer: backend/executors/__init__.py imports executors.base
- non-production consumer: backend/executors/__init__.py imports executors.claude_code_executor
- non-production consumer: backend/executors/__init__.py imports executors.registry
- non-production consumer: backend/executors/__init__.py imports executors.sandboxed_shell_executor
- non-production consumer: backend/executors/claude_code_executor.py imports executors.base
- non-production consumer: backend/executors/n8n_executor.py imports executors.claude_code_executor
- non-production consumer: backend/executors/registry.py imports executors.base
- non-production consumer: backend/executors/registry.py imports executors.claude_code_executor
- non-production consumer: backend/executors/registry.py imports executors.sandboxed_shell_executor
- non-production consumer: backend/executors/sandboxed_shell_executor.py imports executors.base
