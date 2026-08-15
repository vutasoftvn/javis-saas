import os
import yaml
import pytest


K8S_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "deploy", "k8s", "opensandbox"
)


def _load_yaml(filename: str):
    path = os.path.join(K8S_DIR, filename)
    assert os.path.exists(path), f"Manifest file missing: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_opensandbox_deployment_spec():
    doc = _load_yaml("opensandbox-deployment.yaml")
    assert doc["kind"] == "Deployment"
    assert doc["metadata"]["name"] == "opensandbox-server"
    assert doc["metadata"]["namespace"] == "cosa-sandbox"

    spec = doc["spec"]["template"]["spec"]
    containers = spec["containers"]
    assert len(containers) == 1
    c = containers[0]
    assert c["name"] == "opensandbox-server"
    assert c["ports"][0]["containerPort"] == 8080

    # Verify probes
    assert c["readinessProbe"]["httpGet"]["path"] == "/health"
    assert c["livenessProbe"]["httpGet"]["path"] == "/health"


def test_opensandbox_service_spec():
    doc = _load_yaml("opensandbox-service.yaml")
    assert doc["kind"] == "Service"
    assert doc["metadata"]["name"] == "opensandbox-server"
    assert doc["metadata"]["namespace"] == "cosa-sandbox"
    assert doc["spec"]["type"] == "ClusterIP"
    assert doc["spec"]["ports"][0]["port"] == 8080


def test_opensandbox_networkpolicy_spec():
    doc = _load_yaml("opensandbox-networkpolicy.yaml")
    assert doc["kind"] == "NetworkPolicy"
    assert doc["metadata"]["name"] == "opensandbox-isolation-policy"
    assert doc["metadata"]["namespace"] == "cosa-sandbox"

    spec = doc["spec"]
    assert "Ingress" in spec["policyTypes"]
    assert "Egress" in spec["policyTypes"]

    # Ingress allows only cosa-core
    ingress_rules = spec["ingress"]
    assert len(ingress_rules) > 0
    ns_selector = ingress_rules[0]["from"][0]["namespaceSelector"]["matchLabels"]
    assert ns_selector["kubernetes.io/metadata.name"] == "cosa-core"

    # Egress explicitly blocks private CIDRs & metadata
    egress_rules = spec["egress"]
    ip_block = None
    for rule in egress_rules:
        to_list = rule.get("to", [])
        for to_item in to_list:
            if "ipBlock" in to_item:
                ip_block = to_item["ipBlock"]
                break

    assert ip_block is not None
    except_cidrs = ip_block.get("except", [])
    assert "169.254.169.254/32" in except_cidrs
    assert "10.0.0.0/8" in except_cidrs
    assert "192.168.0.0/16" in except_cidrs


def test_opensandbox_kustomization():
    doc = _load_yaml("kustomization.yaml")
    assert doc["kind"] == "Kustomization"
    assert doc["namespace"] == "cosa-sandbox"
    assert "opensandbox-deployment.yaml" in doc["resources"]
    assert "opensandbox-service.yaml" in doc["resources"]
    assert "opensandbox-networkpolicy.yaml" in doc["resources"]
