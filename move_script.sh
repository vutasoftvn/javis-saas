# vault
mv backend/app/api/vault.py backend/app/modules/vault/router.py
mv backend/app/api/sync.py backend/app/modules/vault/sync_router.py
mv backend/app/api/brains.py backend/app/modules/vault/brains_router.py
mv backend/app/services/chunking_service.py backend/app/modules/vault/
mv backend/app/services/embedding_service.py backend/app/modules/vault/
mv backend/app/services/retrieval_service.py backend/app/modules/vault/
mv backend/app/services/graph_service.py backend/app/modules/vault/

# chat
mv backend/app/api/chat.py backend/app/modules/chat/router.py
mv backend/app/api/ai.py backend/app/modules/chat/ai_router.py
mv backend/app/services/chat_execution_service.py backend/app/modules/chat/
mv backend/app/services/chat_stream_bus.py backend/app/modules/chat/
mv backend/app/services/ai_router.py backend/app/modules/chat/
mv backend/app/services/model_registry.py backend/app/modules/chat/
mv backend/app/services/providers.py backend/app/modules/chat/

# tasks
mv backend/app/api/tasks.py backend/app/modules/tasks/router.py
mv backend/app/api/agents.py backend/app/modules/tasks/agents_router.py
mv backend/app/services/scheduler_service.py backend/app/modules/tasks/
mv backend/app/services/task_dispatcher.py backend/app/modules/tasks/

# workflows
mv backend/app/api/workflows.py backend/app/modules/workflows/router.py
mv backend/app/services/workflow_compiler.py backend/app/modules/workflows/
mv backend/app/services/workflow_graph.py backend/app/modules/workflows/
mv backend/app/services/workflow_runtime.py backend/app/modules/workflows/

# strategy
mv backend/app/api/strategy.py backend/app/modules/strategy/router.py
mv backend/app/api/okrs.py backend/app/modules/strategy/okrs_router.py
mv backend/app/api/execution.py backend/app/modules/strategy/execution_router.py
mv backend/app/services/strategy_canvas_service.py backend/app/modules/strategy/

# integrations
mv backend/app/api/connectors.py backend/app/modules/integrations/router.py
mv backend/app/api/channels.py backend/app/modules/integrations/channels_router.py
mv backend/app/api/plugins.py backend/app/modules/integrations/plugins_router.py
mv backend/app/services/mcp backend/app/modules/integrations/
mv backend/app/services/channels backend/app/modules/integrations/
mv backend/app/services/secrets_service.py backend/app/modules/integrations/
mv backend/app/services/plugin_host.py backend/app/modules/integrations/
mv backend/app/services/connector_health.py backend/app/modules/integrations/
mv backend/app/services/chatbot_grounding.py backend/app/modules/integrations/

# platform
mv backend/app/api/admin.py backend/app/modules/platform/router.py
mv backend/app/api/domain.py backend/app/modules/platform/domain_router.py
mv backend/app/services/backup_service.py backend/app/modules/platform/
mv backend/app/services/branding_service.py backend/app/modules/platform/
mv backend/app/services/usage_service.py backend/app/modules/platform/
