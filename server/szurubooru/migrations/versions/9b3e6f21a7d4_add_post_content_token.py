"""
Add post content token and old content table

Revision ID: 9b3e6f21a7d4
Created at: 2026-11-21 12:00:00.000000
"""

import hmac

import sqlalchemy as sa
from alembic import op

from szurubooru import config

revision = "9b3e6f21a7d4"
down_revision = "7c1d4a9e2b35"
branch_labels = None
depends_on = None


def _get_legacy_hash(post_id):
    return hmac.new(
        config.config["secret"].encode("utf8"),
        msg=str(post_id).encode("utf-8"),
        digestmod="md5",
    ).hexdigest()[0:16]


def upgrade():
    op.add_column(
        "post",
        sa.Column("content-token", sa.Unicode(16), nullable=True),
    )

    # existing files are already named after this hash
    conn = op.get_bind()
    post = sa.table(
        "post", sa.column("id", sa.Integer), sa.column("content-token")
    )
    for (post_id,) in conn.execute(sa.select(post.c.id)).fetchall():
        conn.execute(
            post.update()
            .where(post.c.id == post_id)
            .values({"content-token": _get_legacy_hash(post_id)})
        )

    op.alter_column(
        "post", "content-token", existing_type=sa.Unicode(16), nullable=False
    )

    op.create_table(
        "post_old_content",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.Unicode(16), nullable=False),
        sa.Column("mime-type", sa.Unicode(32), nullable=False),
        sa.Column("replaced_time", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_post_old_content_post_id"), "post_old_content", ["post_id"]
    )
    op.create_index(
        op.f("ix_post_old_content_replaced_time"),
        "post_old_content",
        ["replaced_time"],
    )


def downgrade():
    op.drop_index(
        op.f("ix_post_old_content_replaced_time"), table_name="post_old_content"
    )
    op.drop_index(
        op.f("ix_post_old_content_post_id"), table_name="post_old_content"
    )
    op.drop_table("post_old_content")
    op.drop_column("post", "content-token")
