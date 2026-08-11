import os
import glob

# Mapping of old import segments to new import segments
replacements = {
    "app.api.vault": "app.modules.vault.router",
    "app.api.sync": "app.modules.vault.sync_router",
    "app.api.brains": "app.modules.vault.brains_router",
    "app.services.chunking_service": "app.modules.vault.chunking_service",
    "app.services.embedding_service": "app.modules.vault.embedding_service",
    "app.services.retrieval_service": "app.modules.vault.retrieval_service",
    "app.services.graph_service": "app.modules.vault.graph_service",

    "app.api.chat": "app.modules.chat.router",
    "app.api.ai": "app.modules.chat.ai_router",
    "app.services.chat_execution_service": "app.modules.chat.chat_execution_service",
    "app.services.chat_stream_bus": "app.modules.chat.chat_stream_bus",
    "app.services.ai_router": "app.modules.chat.ai_router",
    "app.services.model_registry": "app.modules.chat.model_registry",
    "app.services.providers": "app.modules.chat.providers",

    "app.api.tasks": "app.modules.tasks.router",
    "app.api.agents": "app.modules.tasks.agents_router",
    "app.services.scheduler_service": "app.modules.tasks.scheduler_service",
    "app.services.task_dispatcher": "app.modules.tasks.task_dispatcher",

    "app.api.workflows": "app.modules.workflows.router",
    "app.services.workflow_compiler": "app.modules.workflows.workflow_compiler",
    "app.services.workflow_graph": "app.modules.workflows.workflow_graph",
    "app.services.workflow_runtime": "app.modules.workflows.workflow_runtime",

    "app.api.strategy": "app.modules.strategy.router",
    "app.api.okrs": "app.modules.strategy.okrs_router",
    "app.api.execution": "app.modules.strategy.execution_router",
    "app.services.strategy_canvas_service": "app.modules.strategy.strategy_canvas_service",

    "app.api.connectors": "app.modules.integrations.router",
    "app.api.channels": "app.modules.integrations.channels_router",
    "app.api.plugins": "app.modules.integrations.plugins_router",
    "app.services.mcp": "app.modules.integrations.mcp",
    "app.services.channels": "app.modules.integrations.channels",
    "app.services.secrets_service": "app.modules.integrations.secrets_service",
    "app.services.plugin_host": "app.modules.integrations.plugin_host",
    "app.services.connector_health": "app.modules.integrations.connector_health",
    "app.services.chatbot_grounding": "app.modules.integrations.chatbot_grounding",

    "app.api.admin": "app.modules.platform.router",
    "app.api.domain": "app.modules.platform.domain_router",
    "app.services.backup_service": "app.modules.platform.backup_service",
    "app.services.branding_service": "app.modules.platform.branding_service",
    "app.services.usage_service": "app.modules.platform.usage_service",

    "app.api.auth": "app.modules.iam.router"
}

python_files = glob.glob('backend/app/**/*.py', recursive=True) + glob.glob('backend/tests/**/*.py', recursive=True) + ['backend/app/main.py', 'backend/app/worker_main.py']

for filepath in python_files:
    if not os.path.isfile(filepath):
        continue
    with open(filepath, 'r') as f:
        content = f.read()
    
    new_content = content
    for old, new in replacements.items():
        new_content = new_content.replace(old, new)
        
    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

print("Import replacement complete.")
