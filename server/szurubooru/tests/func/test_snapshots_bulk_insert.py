from unittest.mock import patch

import pytest
import sqlalchemy as sa
import sqlalchemy.orm as sa_orm

from szurubooru import db, model
from szurubooru.func import snapshots


@pytest.fixture(autouse=True)
def session(query_logger):
    """
    Commits db session and forces autoflush to False.
    Needed to reproduce batched Snapshot inserts as seen in production.
    """
    engine = sa.create_engine("sqlite://")
    session = sa_orm.Session(bind=engine, autoflush=False)
    db.session = session
    model.Base.metadata.create_all(engine, checkfirst=True)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_create_batches_post_and_new_tag_snapshots(
    post_factory, tag_factory, user_factory
):
    """
    tests a mix of both an int resource_name (post)
    and a str resource_name (tag) in a batched INSERT
    """
    post = post_factory(id=1)
    tag = tag_factory(names=["dummy-tag"])
    user = user_factory()
    db.session.add_all([post, tag, user])
    db.session.flush()

    with patch("szurubooru.func.snapshots.get_post_snapshot"), patch(
        "szurubooru.func.snapshots.get_tag_snapshot"
    ), patch("szurubooru.func.snapshots._post_to_webhooks"):
        snapshots.get_post_snapshot.return_value = "mocked-post"
        snapshots.get_tag_snapshot.return_value = "mocked-tag"
        snapshots.create(post, user)
        snapshots.create(tag, user)

    db.session.commit()

    results = db.session.query(model.Snapshot).all()
    assert len(results) == 2
    by_type = {result.resource_type: result for result in results}
    assert by_type["post"].resource_name == str(post.post_id)
    assert by_type["post"].resource_pkey == post.post_id
    assert by_type["tag"].resource_name == tag.first_name
    assert by_type["tag"].resource_pkey == tag.tag_id
