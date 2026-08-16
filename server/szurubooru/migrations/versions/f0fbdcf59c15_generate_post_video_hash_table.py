"""
Generate post video hash table

Revision ID: f0fbdcf59c15
Created at: 2026-08-15 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "f0fbdcf59c15"
down_revision = "5436e77141a8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "post_video_hash",
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("hash", sa.LargeBinary(length=8), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["post.id"]),
        sa.PrimaryKeyConstraint("post_id"),
    )


def downgrade():
    op.drop_table("post_video_hash")
