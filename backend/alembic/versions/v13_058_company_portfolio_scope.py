"""Add company portfolio scope tables and initiative offering link.

Revision ID: v13_058_company_portfolio_scope
Revises: v13_057_learning_memory
Create Date: 2026-08-20 13:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "v13_058_company_portfolio_scope"
down_revision: Union[str, Sequence[str], None] = "v13_057_learning_memory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operating_units",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column(
            "workspace_id",
            sa.BigInteger(),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "status", sa.String(length=24), nullable=False, server_default="active"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "workspace_id", "slug", name="uq_operating_unit_workspace_slug"
        ),
    )
    op.create_index(
        "ix_operating_units_workspace_status",
        "operating_units",
        ["workspace_id", "status"],
    )

    op.create_table(
        "offerings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column(
            "workspace_id",
            sa.BigInteger(),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "operating_unit_id",
            sa.BigInteger(),
            sa.ForeignKey("operating_units.id"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column(
            "status", sa.String(length=24), nullable=False, server_default="active"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("operating_unit_id", "slug", name="uq_offering_unit_slug"),
    )
    op.create_index(
        "ix_offerings_workspace_unit_status",
        "offerings",
        ["workspace_id", "operating_unit_id", "status"],
    )

    with op.batch_alter_table("initiatives") as batch_op:
        batch_op.add_column(
            sa.Column(
                "offering_id",
                sa.BigInteger(),
                sa.ForeignKey("offerings.id"),
                nullable=True,
            )
        )
        batch_op.create_index("ix_initiatives_offering_id", ["offering_id"])


def downgrade() -> None:
    with op.batch_alter_table("initiatives") as batch_op:
        batch_op.drop_index("ix_initiatives_offering_id")
        batch_op.drop_column("offering_id")

    op.drop_index("ix_offerings_workspace_unit_status", table_name="offerings")
    op.drop_table("offerings")
    op.drop_index("ix_operating_units_workspace_status", table_name="operating_units")
    op.drop_table("operating_units")
