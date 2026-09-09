"""
Create post inspiration table

Revision ID: 030b2516b9f8
Created at: 2026-09-09 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "030b2516b9f8"
down_revision = "5436e77141a8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "post_inspiration",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), nullable=True, index=True),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["post.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("post_inspiration")
