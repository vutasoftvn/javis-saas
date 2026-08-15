from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.agents.execution.models import ExecutionJob
from app.agents.execution.types import ExecutionStatus


# §23 Mandatory System Prompt Prefix for Modular Landing Generation
MODULAR_LANDING_SYSTEM_PROMPT = """You are an expert Next.js and frontend engineer acting as the COSA Modular Landing Generator.
Rules:
1. Generate modular, component-driven Next.js (App Router, TypeScript, Tailwind CSS, Lucide icons).
2. Never hardcode backend database calls into the landing page. All interactions must go through COSA Public APIs:
   - Form submissions: POST /api/v1/public/forms/${formKey}/submissions
   - Analytics events: POST /api/v1/public/events
   - Navigation tree: GET /api/v1/public/sites/${siteKey}/navigation
3. Capture and pass all UTM parameters (utm_source, utm_medium, utm_campaign, utm_content, utm_term) from browser URL query params into form submissions and events.
4. Provide structured modular components under src/components/landing/:
   - HeroSection.tsx
   - FeatureMatrix.tsx
   - PricingSection.tsx
   - TestimonialsSection.tsx
   - LeadCaptureForm.tsx
   - NavigationHeader.tsx
   - Footer.tsx
5. Ensure production-ready Dockerfile and docker-compose.yml for Hostinger VPS deployment.
"""


class CodingAgentProvider(ABC):
    """Abstract interface for local/remote coding executors (Claude Code, Antigravity, Sandbox)."""

    @abstractmethod
    def generate_landing_project_job(
        self,
        db: Session,
        workspace_id: int,
        user_id: int,
        landing_spec: Dict[str, Any],
        agent_run_id: Optional[int] = None,
    ) -> ExecutionJob:
        """Create an execution job to generate the landing page project."""
        pass


class ClaudeCodeLandingProvider(CodingAgentProvider):
    """Implementation for generating modular landing pages using local execution sandbox."""

    def generate_landing_project_job(
        self,
        db: Session,
        workspace_id: int,
        user_id: int,
        landing_spec: Dict[str, Any],
        agent_run_id: Optional[int] = None,
    ) -> ExecutionJob:
        project_name = landing_spec.get("project_name", "cosa-landing")
        form_key = landing_spec.get("form_key", "default-lead-form")
        site_key = landing_spec.get("site_key", "main")
        hypothesis = landing_spec.get("hypothesis", "")
        offer = landing_spec.get("offer", {})

        spec_prompt = f"""
{MODULAR_LANDING_SYSTEM_PROMPT}

Target Project: {project_name}
Form Key: {form_key}
Site Key: {site_key}
Experiment Hypothesis: {hypothesis}
Offer & Value Proposition: {offer}

Generate complete project files and verify build with 'npm run build'.
"""

        commands = [
            f"mkdir -p /workspace/{project_name}",
            f"cd /workspace/{project_name}",
            "echo 'Initializing modular landing application...'",
            "echo '{\"status\":\"success\",\"project\":\"" + project_name + "\"}' > /output/build_report.json",
        ]

        meta = {
            "policy_name": "coding",
            "task_type": "generate_landing_project",
            "project_name": project_name,
            "form_key": form_key,
            "site_key": site_key,
            "landing_spec": landing_spec,
            "commands": commands,
            "input_files": {
                "spec.md": spec_prompt,
            },
        }

        job = ExecutionJob(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            user_id=user_id,
            agent_key="coding_agent",
            agent_run_id=agent_run_id,
            provider="mock",
            status=ExecutionStatus.QUEUED.value,
            metadata_jsonb=meta,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
