"""
Add recommendation weight to tag categories

Revision ID: 5436e77141a8
Created at: 2026-07-20 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "5436e77141a8"
down_revision = "5b5c940b4e78"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "tag_category",
        sa.Column("recommendation_weight", sa.Float(), nullable=True),
    )
    op.execute(
        sa.table("tag_category", sa.column("recommendation_weight"))
        .update()
        .values(recommendation_weight=1.0)
    )
    op.alter_column(
        "tag_category", "recommendation_weight", nullable=False
    )


def downgrade():
    op.drop_column("tag_category", "recommendation_weight")
