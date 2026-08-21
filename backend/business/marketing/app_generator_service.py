"""Company-Owned Marketing App Generator & Manifest Service (Phase 4).

Generates portable Next.js marketing applications with cosa.manifest.yaml, ensuring zero vendor lock-in.
Specification: COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md (Section 40-62)
"""
import logging
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field
import yaml

from platform_core.sync.entitlement_manager import EntitlementManager

logger = logging.getLogger(__name__)


class RouteModuleConfig(BaseModel):
    path: str = "/"
    title: str = "Home"
    modules: List[str] = Field(default_factory=lambda: ["HeroSection", "BentoFeatures", "LeadFormSection", "Footer"])
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None


class MarketingAppManifest(BaseModel):
    schema_version: int = 1
    app_id: str
    company_id: str
    name: str
    framework: str = "nextjs"
    deployment_mode: str = "cosa_managed" # cosa_managed, company_vps, fully_private
    custom_domain: Optional[str] = None
    default_subdomain: str
    routes: List[RouteModuleConfig] = Field(default_factory=list)
    features: Dict[str, bool] = Field(
        default_factory=lambda: {
            "lead_forms": True,
            "surveys": True,
            "analytics": True,
            "roi_calculator": False,
        }
    )
    public_intake_url: str = "/api/v1/public/intake/submit"

    def to_yaml(self) -> str:
        return yaml.dump(self.model_dump(mode="json"), sort_keys=False)


class AppGeneratorService:
    """Service to create, validate, and export Company-Owned Marketing Applications."""

    @classmethod
    def generate_app_manifest(
        cls,
        company_id: str,
        name: str,
        slug: str,
        deployment_mode: str = "cosa_managed",
        routes: Optional[List[RouteModuleConfig]] = None,
        custom_domain: Optional[str] = None,
        features: Optional[Dict[str, bool]] = None,
    ) -> MarketingAppManifest:
        """Generates and validates the portable marketing application manifest."""
        app_id = str(uuid.uuid4())
        default_subdomain = f"{slug}.cosa.vn"

        # Entitlement check for Custom Domain
        if custom_domain:
            has_custom_domain = EntitlementManager.is_feature_allowed(company_id, "custom_domain")
            if not has_custom_domain:
                logger.warning(
                    f"Company {company_id} requested custom_domain '{custom_domain}' without entitlement. Fallback to subdomain."
                )
                custom_domain = None

        default_routes = routes or [
            RouteModuleConfig(
                path="/",
                title="Home Landing",
                modules=["HeroSection", "SocialProofBar", "BentoFeatures", "PricingSection", "LeadFormSection", "FaqSection", "Footer"],
                seo_title=f"{name} - AI Solutions",
                seo_description=f"Welcome to {name}",
            ),
            RouteModuleConfig(
                path="/survey",
                title="Customer Discovery Survey",
                modules=["SurveyModule", "Footer"],
                seo_title=f"{name} - Discovery Survey",
                seo_description="Help us shape our upcoming product release.",
            ),
        ]

        manifest = MarketingAppManifest(
            app_id=app_id,
            company_id=company_id,
            name=name,
            framework="nextjs",
            deployment_mode=deployment_mode,
            custom_domain=custom_domain,
            default_subdomain=default_subdomain,
            routes=default_routes,
            features=features or {"lead_forms": True, "surveys": True, "analytics": True},
            public_intake_url="/api/v1/public/intake/submit",
        )

        logger.info(f"Generated manifest for Marketing App '{name}' ({app_id}) - Mode: {deployment_mode}")
        return manifest

    @classmethod
    def get_export_package_structure(cls, manifest: MarketingAppManifest) -> Dict[str, Any]:
        """Generates standalone portable repository directory structure for export/transfer."""
        return {
            "app_id": manifest.app_id,
            "company_id": manifest.company_id,
            "manifest_yaml": manifest.to_yaml(),
            "files": [
                "cosa.manifest.yaml",
                "package.json",
                "next.config.ts",
                "tsconfig.json",
                "tailwind.config.ts",
                ".env.example",
                "src/app/page.tsx",
                "src/app/survey/page.tsx",
                "src/components/sections/HeroSection.tsx",
                "src/components/sections/BentoFeatures.tsx",
                "src/components/sections/LeadFormSection.tsx",
                "src/components/sections/PricingSection.tsx",
                "src/components/sections/FaqSection.tsx",
                "src/lib/cosa-intake-client.ts",
                "README.md",
            ],
            "deployment_instructions": {
                "cosa_managed": "Deployed automatically to Hostinger VPS edge.",
                "company_vps": "Run 'npm install && npm run build && npm run start' on your VPS or Docker container.",
                "fully_private": "Connect public_intake_url to your local private COSA backend.",
            },
        }
