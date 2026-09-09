from datetime import datetime
from unittest.mock import patch

import pytest

from szurubooru import api, db, errors, model
from szurubooru.func import inspirations, posts


@pytest.fixture(autouse=True)
def inject_config(config_injector):
    config_injector(
        {
            "privileges": {
                "posts:inspire": model.User.RANK_REGULAR,
                "posts:inspire:reset": model.User.RANK_MODERATOR,
            },
            "inspirations": {"cooldown_seconds": 3600},
        }
    )


def test_inspiring(user_factory, post_factory, context_factory, fake_datetime):
    user = user_factory()
    post = post_factory()
    db.session.add_all([user, post])
    db.session.commit()
    with patch("szurubooru.func.posts.serialize_post"), fake_datetime(
        datetime(2020, 1, 1, 12, 0, 0)
    ):
        posts.serialize_post.return_value = "serialized post"
        result = api.post_api.inspire_post(
            context_factory(user=user), {"post_id": post.post_id}
        )
        assert result == "serialized post"
        post = db.session.query(model.Post).one()
        assert db.session.query(model.PostInspiration).count() == 1
        assert post.inspiration_count == 1
        assert post.last_inspiration_time == datetime(2020, 1, 1, 12, 0, 0)


def test_inspiring_twice_within_cooldown(
    user_factory, post_factory, context_factory, fake_datetime
):
    user = user_factory()
    post = post_factory()
    db.session.add_all([user, post])
    db.session.commit()
    with patch("szurubooru.func.posts.serialize_post"):
        with fake_datetime(datetime(2020, 1, 1, 12, 0, 0)):
            api.post_api.inspire_post(
                context_factory(user=user), {"post_id": post.post_id}
            )
        with fake_datetime(datetime(2020, 1, 1, 12, 30, 0)):
            with pytest.raises(inspirations.InspirationCooldownError):
                api.post_api.inspire_post(
                    context_factory(user=user), {"post_id": post.post_id}
                )
        post = db.session.query(model.Post).one()
        assert post.inspiration_count == 1


def test_inspiring_after_cooldown_expires(
    user_factory, post_factory, context_factory, fake_datetime
):
    user = user_factory()
    post = post_factory()
    db.session.add_all([user, post])
    db.session.commit()
    with patch("szurubooru.func.posts.serialize_post"):
        with fake_datetime(datetime(2020, 1, 1, 12, 0, 0)):
            api.post_api.inspire_post(
                context_factory(user=user), {"post_id": post.post_id}
            )
        with fake_datetime(datetime(2020, 1, 1, 13, 0, 1)):
            api.post_api.inspire_post(
                context_factory(user=user), {"post_id": post.post_id}
            )
        post = db.session.query(model.Post).one()
        assert post.inspiration_count == 2


def test_inspiration_cooldown_is_per_user(
    user_factory, post_factory, context_factory, fake_datetime
):
    user1 = user_factory()
    user2 = user_factory()
    post = post_factory()
    db.session.add_all([user1, user2, post])
    db.session.commit()
    with patch("szurubooru.func.posts.serialize_post"):
        with fake_datetime(datetime(2020, 1, 1, 12, 0, 0)):
            api.post_api.inspire_post(
                context_factory(user=user1), {"post_id": post.post_id}
            )
            api.post_api.inspire_post(
                context_factory(user=user2), {"post_id": post.post_id}
            )
        post = db.session.query(model.Post).one()
        assert post.inspiration_count == 2


def test_inspiration_cooldown_is_global_across_posts(
    user_factory, post_factory, context_factory, fake_datetime
):
    user = user_factory()
    post1 = post_factory(id=1)
    post2 = post_factory(id=2)
    db.session.add_all([user, post1, post2])
    db.session.commit()
    with patch("szurubooru.func.posts.serialize_post"):
        with fake_datetime(datetime(2020, 1, 1, 12, 0, 0)):
            api.post_api.inspire_post(
                context_factory(user=user), {"post_id": post1.post_id}
            )
            with pytest.raises(inspirations.InspirationCooldownError):
                api.post_api.inspire_post(
                    context_factory(user=user), {"post_id": post2.post_id}
                )
        post1 = db.session.query(model.Post).filter(
            model.Post.post_id == 1
        ).one()
        post2 = db.session.query(model.Post).filter(
            model.Post.post_id == 2
        ).one()
        assert post1.inspiration_count == 1
        assert post2.inspiration_count == 0


def test_resetting_inspiration_count(
    user_factory, post_factory, context_factory, fake_datetime
):
    user = user_factory()
    admin = user_factory(rank=model.User.RANK_MODERATOR)
    post = post_factory()
    db.session.add_all([user, admin, post])
    db.session.commit()
    with patch("szurubooru.func.posts.serialize_post"):
        with fake_datetime(datetime(2020, 1, 1, 12, 0, 0)):
            api.post_api.inspire_post(
                context_factory(user=user), {"post_id": post.post_id}
            )
        post = db.session.query(model.Post).one()
        assert post.inspiration_count == 1
        api.post_api.reset_post_inspiration(
            context_factory(user=admin), {"post_id": post.post_id}
        )
        post = db.session.query(model.Post).one()
        assert post.inspiration_count == 0
        assert db.session.query(model.PostInspiration).count() == 0


def test_trying_to_reset_without_privileges(
    user_factory, post_factory, context_factory
):
    post = post_factory()
    db.session.add(post)
    db.session.commit()
    with pytest.raises(errors.AuthError):
        api.post_api.reset_post_inspiration(
            context_factory(user=user_factory(rank=model.User.RANK_REGULAR)),
            {"post_id": post.post_id},
        )


def test_trying_to_inspire_without_privileges(
    user_factory, post_factory, context_factory
):
    post = post_factory()
    db.session.add(post)
    db.session.commit()
    with pytest.raises(errors.AuthError):
        api.post_api.inspire_post(
            context_factory(user=user_factory(rank=model.User.RANK_ANONYMOUS)),
            {"post_id": post.post_id},
        )


def test_trying_to_inspire_non_existing(user_factory, context_factory):
    with pytest.raises(posts.PostNotFoundError):
        api.post_api.inspire_post(
            context_factory(user=user_factory()), {"post_id": 5}
        )


def test_trying_to_reset_non_existing(user_factory, context_factory):
    with pytest.raises(posts.PostNotFoundError):
        api.post_api.reset_post_inspiration(
            context_factory(user=user_factory(rank=model.User.RANK_MODERATOR)),
            {"post_id": 5},
        )


def test_add_inspiration_requires_persisted_user(post_factory, user_factory):
    # A transient (never added/flushed) user has no user_id, mirroring an
    # anonymous request. This is a defense-in-depth check independent of the
    # privilege system, in case posts:inspire is ever misconfigured to allow
    # the anonymous rank.
    post = post_factory()
    db.session.add(post)
    db.session.commit()
    transient_user = user_factory()
    with pytest.raises(errors.AuthError):
        inspirations.add_inspiration(post, transient_user)
