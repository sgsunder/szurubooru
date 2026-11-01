from datetime import datetime
from unittest.mock import patch

import pytest

from szurubooru import api, db, errors, model
from szurubooru.func import posts


@pytest.fixture(autouse=True)
def inject_config(config_injector):
    config_injector(
        {
            "privileges": {
                "posts:inspire": model.User.RANK_REGULAR,
            },
            "inspirations": {"cooldown_seconds": 3600},
        }
    )


def test_converting_comment(
    user_factory, post_factory, comment_factory, context_factory
):
    user = user_factory()
    post = post_factory()
    comment = comment_factory(
        user=user, post=post, time=datetime(2019, 5, 6, 7, 8, 9)
    )
    db.session.add_all([user, post, comment])
    db.session.commit()
    with patch("szurubooru.func.posts.serialize_post"):
        posts.serialize_post.return_value = "serialized post"
        result = api.comment_api.convert_comment_to_inspiration(
            context_factory(params={"version": 1}, user=user),
            {"comment_id": comment.comment_id},
        )
    assert result == "serialized post"
    assert db.session.query(model.Comment).count() == 0
    inspiration = db.session.query(model.PostInspiration).one()
    assert inspiration.time == datetime(2019, 5, 6, 7, 8, 9)
    assert inspiration.user_id == user.user_id
    assert inspiration.post_id == post.post_id


def test_converting_bypasses_cooldown(
    user_factory, post_factory, comment_factory, context_factory, fake_datetime
):
    user = user_factory()
    post = post_factory()
    comment = comment_factory(user=user, post=post)
    db.session.add_all([user, post, comment])
    db.session.commit()
    with patch("szurubooru.func.posts.serialize_post"):
        with fake_datetime(datetime(2020, 1, 1, 12, 0, 0)):
            api.post_api.inspire_post(
                context_factory(user=user), {"post_id": post.post_id}
            )
            api.comment_api.convert_comment_to_inspiration(
                context_factory(params={"version": 1}, user=user),
                {"comment_id": comment.comment_id},
            )
    assert db.session.query(model.PostInspiration).count() == 2
    assert db.session.query(model.Comment).count() == 0


def test_converting_someone_elses_comment(
    user_factory, post_factory, comment_factory, context_factory
):
    user1 = user_factory(rank=model.User.RANK_REGULAR)
    user2 = user_factory(rank=model.User.RANK_ADMINISTRATOR)
    post = post_factory()
    comment = comment_factory(user=user1, post=post)
    db.session.add_all([user1, user2, post, comment])
    db.session.commit()
    with pytest.raises(errors.AuthError):
        api.comment_api.convert_comment_to_inspiration(
            context_factory(params={"version": 1}, user=user2),
            {"comment_id": comment.comment_id},
        )
    assert db.session.query(model.Comment).count() == 1
    assert db.session.query(model.PostInspiration).count() == 0


def test_converting_without_privileges(
    user_factory,
    post_factory,
    comment_factory,
    context_factory,
    config_injector,
):
    config_injector(
        {
            "privileges": {"posts:inspire": model.User.RANK_MODERATOR},
            "inspirations": {"cooldown_seconds": 3600},
        }
    )
    user = user_factory(rank=model.User.RANK_REGULAR)
    post = post_factory()
    comment = comment_factory(user=user, post=post)
    db.session.add_all([user, post, comment])
    db.session.commit()
    with pytest.raises(errors.AuthError):
        api.comment_api.convert_comment_to_inspiration(
            context_factory(params={"version": 1}, user=user),
            {"comment_id": comment.comment_id},
        )
    assert db.session.query(model.Comment).count() == 1


def test_converting_with_wrong_version(
    user_factory, post_factory, comment_factory, context_factory
):
    user = user_factory()
    post = post_factory()
    comment = comment_factory(user=user, post=post)
    db.session.add_all([user, post, comment])
    db.session.commit()
    with pytest.raises(errors.IntegrityError):
        api.comment_api.convert_comment_to_inspiration(
            context_factory(params={"version": 2}, user=user),
            {"comment_id": comment.comment_id},
        )
    assert db.session.query(model.Comment).count() == 1


def test_converting_non_existing_comment(user_factory, context_factory):
    user = user_factory()
    db.session.add(user)
    db.session.commit()
    with pytest.raises(Exception):
        api.comment_api.convert_comment_to_inspiration(
            context_factory(params={"version": 1}, user=user),
            {"comment_id": 5},
        )
