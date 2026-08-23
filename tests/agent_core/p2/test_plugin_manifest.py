from __future__ import annotations

from agent_core.contracts.capability import CapabilitySpec
from agent_core.governance.contracts import CapabilityRisk
from agent_core.plugins import (
    PluginCapabilityGrant,
    PluginManifest,
    PluginRegistry,
)


def test_plugin_manifest_registry():
    """Kiểm thử Plugin Manifest & Registry."""
    registry = PluginRegistry()

    cap = CapabilitySpec(
        id="plugin.slack.notify",
        description="Send Slack webhook notification",
        risk=CapabilityRisk.LOW,
    )

    manifest = PluginManifest(
        plugin_id="plugin_slack_integrations",
        name="Slack Integration Plugin",
        version="1.0.0",
        publisher="cosa-community",
        capabilities=[cap],
        permissions=[
            PluginCapabilityGrant(
                capability_id="plugin.slack.notify",
                required_risk="LOW",
                allowed_domains=("api.slack.com",),
            )
        ],
    )

    registry.register_plugin(manifest)

    fetched = registry.get_plugin("plugin_slack_integrations")
    assert fetched is not None
    assert fetched.name == "Slack Integration Plugin"
    assert len(fetched.capabilities) == 1
    assert fetched.capabilities[0].id == "plugin.slack.notify"
