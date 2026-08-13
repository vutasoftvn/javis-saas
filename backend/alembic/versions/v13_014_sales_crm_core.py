"""sales crm core tables and lead extension

Revision ID: v13_014_sales_crm_core
Revises: v13_013_flag_defaults
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "v13_014_sales_crm_core"
down_revision: Union[str, Sequence[str], None] = "v13_013_flag_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. create accounts
    op.create_table(
        "accounts",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("size_segment", sa.String(length=50), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("lifecycle_status", sa.String(length=30), nullable=False, server_default="TARGET"),
        sa.Column("owner_id", sa.BigInteger(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_accounts_workspace_id"), "accounts", ["workspace_id"], unique=False)
    op.create_index(
        "uq_accounts_workspace_domain",
        "accounts",
        ["workspace_id", "domain"],
        unique=True,
        postgresql_where=sa.text("domain IS NOT NULL"),
    )

    # 2. create contacts
    op.create_table(
        "contacts",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("consent_status", sa.String(length=30), nullable=True),
        sa.Column("do_not_contact", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("owner_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_contacts_account_id"), "contacts", ["account_id"], unique=False)
    op.create_index(op.f("ix_contacts_workspace_id"), "contacts", ["workspace_id"], unique=False)
    op.create_index(
        "uq_contacts_workspace_email",
        "contacts",
        ["workspace_id", "email"],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL"),
    )

    # 3. extend sales_leads
    op.add_column("sales_leads", sa.Column("account_id", sa.BigInteger(), nullable=True))
    op.add_column("sales_leads", sa.Column("contact_id", sa.BigInteger(), nullable=True))
    op.add_column("sales_leads", sa.Column("source", sa.String(length=100), nullable=True))
    op.add_column("sales_leads", sa.Column("source_campaign_id", sa.BigInteger(), nullable=True))
    op.add_column("sales_leads", sa.Column("fit_score", sa.Float(), nullable=True))
    op.add_column("sales_leads", sa.Column("intent_score", sa.Float(), nullable=True))
    op.add_column("sales_leads", sa.Column("engagement_score", sa.Float(), nullable=True))
    op.add_column("sales_leads", sa.Column("qualification_status", sa.String(length=30), nullable=True))
    op.add_column("sales_leads", sa.Column("disqualification_reason", sa.Text(), nullable=True))
    op.add_column("sales_leads", sa.Column("next_action_at", sa.DateTime(), nullable=True))
    op.add_column("sales_leads", sa.Column("next_action_type", sa.String(length=50), nullable=True))
    op.add_column("sales_leads", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))

    op.create_foreign_key("fk_sales_leads_account_id", "sales_leads", "accounts", ["account_id"], ["id"])
    op.create_foreign_key("fk_sales_leads_contact_id", "sales_leads", "contacts", ["contact_id"], ["id"])
    op.create_foreign_key("fk_sales_leads_source_campaign_id", "sales_leads", "marketing_campaigns", ["source_campaign_id"], ["id"])
    op.create_index(op.f("ix_sales_leads_account_id"), "sales_leads", ["account_id"], unique=False)
    op.create_index(op.f("ix_sales_leads_contact_id"), "sales_leads", ["contact_id"], unique=False)

    # 4. create sales_opportunities
    op.create_table(
        "sales_opportunities",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("primary_contact_id", sa.BigInteger(), nullable=True),
        sa.Column("owner_id", sa.BigInteger(), nullable=True),
        sa.Column("source_lead_id", sa.BigInteger(), nullable=True),
        sa.Column("product", sa.String(length=255), nullable=True),
        sa.Column("stage", sa.String(length=30), nullable=False, server_default="DISCOVERY"),
        sa.Column("estimated_value", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="VND"),
        sa.Column("probability", sa.Float(), nullable=True),
        sa.Column("expected_close_date", sa.Date(), nullable=True),
        sa.Column("pain_points", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("needs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("objections", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("competitors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("next_action", sa.String(length=255), nullable=True),
        sa.Column("next_action_due_at", sa.DateTime(), nullable=True),
        sa.Column("won_reason", sa.String(length=30), nullable=True),
        sa.Column("lost_reason", sa.String(length=30), nullable=True),
        sa.Column("lost_reason_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["primary_contact_id"], ["contacts.id"]),
        sa.ForeignKeyConstraint(["source_lead_id"], ["sales_leads.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sales_opportunities_account_id"), "sales_opportunities", ["account_id"], unique=False)
    op.create_index(op.f("ix_sales_opportunities_workspace_id"), "sales_opportunities", ["workspace_id"], unique=False)

    # 5. create sales_activities
    op.create_table(
        "sales_activities",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("activity_type", sa.String(length=30), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=True),
        sa.Column("direction", sa.String(length=20), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sales_activities_entity_id"), "sales_activities", ["entity_id"], unique=False)
    op.create_index(op.f("ix_sales_activities_workspace_id"), "sales_activities", ["workspace_id"], unique=False)

    # 6. create customers
    op.create_table(
        "customers",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("acquired_from_opportunity_id", sa.BigInteger(), nullable=True),
        sa.Column("lifecycle_status", sa.String(length=30), nullable=False, server_default="ONBOARDING"),
        sa.Column("activation_status", sa.String(length=30), nullable=True),
        sa.Column("owner_id", sa.BigInteger(), nullable=True),
        sa.Column("first_purchase_at", sa.DateTime(), nullable=True),
        sa.Column("renewal_date", sa.Date(), nullable=True),
        sa.Column("health_status", sa.String(length=20), nullable=False, server_default="HEALTHY"),
        sa.Column("last_success_interaction_at", sa.DateTime(), nullable=True),
        sa.Column("next_success_action_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["acquired_from_opportunity_id"], ["sales_opportunities.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customers_workspace_id"), "customers", ["workspace_id"], unique=False)
    op.create_index("uq_customers_workspace_account", "customers", ["workspace_id", "account_id"], unique=True)


def downgrade() -> None:
    pass
