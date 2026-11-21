"""
Create post video fingerprint table

Revision ID: 7c1d4a9e2b35
Created at: 2026-11-21 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "7c1d4a9e2b35"
down_revision = "030b2516b9f8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "post_video_fingerprint",
        sa.Column("post_id", sa.Integer(), nullable=False, index=True),
        sa.Column("duration", sa.Float(), nullable=False, index=True),
        sa.Column("hashes", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["post.id"]),
        sa.PrimaryKeyConstraint("post_id"),
    )


def downgrade():
    op.drop_table("post_video_fingerprint")
