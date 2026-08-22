"""add workforce_members.agent_definition_id and workforce_relations table

Revision ID: c8e01c5a0008
Revises: c7e01c5a0007
Create Date: 2026-08-21 10:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c8e01c5a0008"
down_revision: Union[str, Sequence[str], None] = "c7e01c5a0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workforce_members",
        sa.Column("agent_definition_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "ix_workforce_members_agent_definition_id",
        "workforce_members",
        ["agent_definition_id"],
    )
    op.create_foreign_key(
        "fk_workforce_members_agent_definition_id",
        "workforce_members",
        "agent_definitions",
        ["agent_definition_id"],
        ["id"],
    )

    op.create_table(
        "workforce_relations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("member_id", sa.BigInteger(), nullable=False),
        sa.Column("related_member_id", sa.BigInteger(), nullable=False),
        sa.Column("relation", sa.String(length=50), nullable=False, server_default="reports_to"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_workforce_relations_org"),
        sa.ForeignKeyConstraint(["member_id"], ["workforce_members.id"], name="fk_workforce_relations_member"),
        sa.ForeignKeyConstraint(["related_member_id"], ["workforce_members.id"], name="fk_workforce_relations_related"),
        sa.UniqueConstraint("member_id", "related_member_id", "relation", name="uq_workforce_relation_edge"),
    )
    op.create_index("ix_workforce_relations_organization_id", "workforce_relations", ["organization_id"])
    op.create_index("ix_workforce_relations_member_id", "workforce_relations", ["member_id"])
    op.create_index("ix_workforce_relations_related_member_id", "workforce_relations", ["related_member_id"])


def downgrade() -> None:
    op.drop_table("workforce_relations")
    op.drop_constraint("fk_workforce_members_agent_definition_id", "workforce_members", type_="foreignkey")
    op.drop_index("ix_workforce_members_agent_definition_id", table_name="workforce_members")
    op.drop_column("workforce_members", "agent_definition_id")
