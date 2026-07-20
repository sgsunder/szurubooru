from unittest.mock import patch

import pytest

from szurubooru import api, db, errors, model
from szurubooru.func import tags


@pytest.fixture(autouse=True)
def inject_config(config_injector):
    config_injector(
        {"privileges": {"tags:recommendations": model.User.RANK_REGULAR}}
    )


def test_get_tag_recommendations(user_factory, tag_factory, context_factory):
    tag = tag_factory(names=["tag"])
    db.session.add(tag)
    db.session.flush()
    with (
        patch("szurubooru.func.tags.serialize_tag"),
        patch("szurubooru.func.tags.try_get_tag_by_name"),
        patch("szurubooru.func.tags.get_tag_recommendations"),
    ):
        tags.serialize_tag.side_effect = (
            lambda tag, *args, **kwargs: "serialized tag %s"
            % tag.names[0].name
        )
        tags.try_get_tag_by_name.return_value = tag
        tags.get_tag_recommendations.return_value = [
            (tag_factory(names=["rec1"]), 1.5),
            (tag_factory(names=["rec2"]), 0.5),
        ]
        result = api.tag_api.get_tag_recommendations(
            context_factory(
                params={"names": ["tag"]},
                user=user_factory(rank=model.User.RANK_REGULAR),
            ),
            {},
        )
        assert result == {
            "results": [
                {"tag": "serialized tag rec1", "score": 1.5},
                {"tag": "serialized tag rec2", "score": 0.5},
            ],
        }
        tags.try_get_tag_by_name.assert_called_once_with("tag")
        tags.get_tag_recommendations.assert_called_once_with([tag], 10)


def test_get_tag_recommendations_custom_limit(
    user_factory, tag_factory, context_factory
):
    tag = tag_factory(names=["tag"])
    db.session.add(tag)
    db.session.flush()
    with (
        patch("szurubooru.func.tags.try_get_tag_by_name"),
        patch("szurubooru.func.tags.get_tag_recommendations"),
    ):
        tags.try_get_tag_by_name.return_value = tag
        tags.get_tag_recommendations.return_value = []
        api.tag_api.get_tag_recommendations(
            context_factory(
                params={"names": ["tag"], "limit": 5},
                user=user_factory(rank=model.User.RANK_REGULAR),
            ),
            {},
        )
        tags.get_tag_recommendations.assert_called_once_with([tag], 5)


def test_get_tag_recommendations_limit_too_high(
    user_factory, tag_factory, context_factory
):
    with pytest.raises(errors.InvalidParameterError):
        api.tag_api.get_tag_recommendations(
            context_factory(
                params={"names": ["tag"], "limit": 999},
                user=user_factory(rank=model.User.RANK_REGULAR),
            ),
            {},
        )


def test_get_tag_recommendations_empty_names(user_factory, context_factory):
    with pytest.raises(errors.ValidationError):
        api.tag_api.get_tag_recommendations(
            context_factory(
                params={"names": []},
                user=user_factory(rank=model.User.RANK_REGULAR),
            ),
            {},
        )


def test_get_tag_recommendations_missing_names(user_factory, context_factory):
    with pytest.raises(errors.MissingRequiredParameterError):
        api.tag_api.get_tag_recommendations(
            context_factory(
                params={}, user=user_factory(rank=model.User.RANK_REGULAR)
            ),
            {},
        )


def test_get_tag_recommendations_unknown_tag_name(
    user_factory, context_factory
):
    """
    a name that doesn't resolve to an existing tag
    (e.g. a brand new tag being added alongside the post)
    is skipped rather than erroring out, so recommendations
    still work for whichever names do exist
    """
    result = api.tag_api.get_tag_recommendations(
        context_factory(
            params={"names": ["-"]},
            user=user_factory(rank=model.User.RANK_REGULAR),
        ),
        {},
    )
    assert result == {"results": []}


def test_get_tag_recommendations_mixed_known_and_unknown_tag_names(
    user_factory, tag_factory, context_factory
):
    tag = tag_factory(names=["tag"])
    db.session.add(tag)
    db.session.flush()
    with patch("szurubooru.func.tags.get_tag_recommendations"):
        tags.get_tag_recommendations.return_value = []
        api.tag_api.get_tag_recommendations(
            context_factory(
                params={"names": ["tag", "-"]},
                user=user_factory(rank=model.User.RANK_REGULAR),
            ),
            {},
        )
        tags.get_tag_recommendations.assert_called_once_with([tag], 10)


def test_get_tag_recommendations_without_privileges(
    user_factory, context_factory
):
    with pytest.raises(errors.AuthError):
        api.tag_api.get_tag_recommendations(
            context_factory(
                params={"names": ["-"]},
                user=user_factory(rank=model.User.RANK_ANONYMOUS),
            ),
            {},
        )
