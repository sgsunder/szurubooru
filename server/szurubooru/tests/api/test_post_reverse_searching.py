from unittest.mock import patch

import pytest

from szurubooru import api, db, model
from szurubooru.func import posts


@pytest.fixture(autouse=True)
def inject_config(config_injector):
    config_injector(
        {
            "privileges": {"posts:reverse_search": model.User.RANK_REGULAR},
            "allow_broken_uploads": False,
        }
    )


def test_reverse_searching_video(
    user_factory, post_factory, context_factory, read_asset
):
    content = read_asset("mp4.mp4")
    post = post_factory(id=1)
    db.session.add(post)
    db.session.flush()
    posts.generate_post_video_fingerprint(post, content)
    db.session.flush()
    with patch("szurubooru.func.posts.serialize_post"):
        posts.serialize_post.side_effect = lambda post, *_, **__: (
            post and post.post_id
        )
        result = api.post_api.get_posts_by_image(
            context_factory(
                files={"content": content},
                user=user_factory(rank=model.User.RANK_REGULAR),
            )
        )
    assert result["exactPost"] is None
    assert result["similarPosts"] == [{"distance": 0, "post": 1}]
