import pytest

from szurubooru import api, errors, model
from szurubooru.func import source_tags


@pytest.fixture(autouse=True)
def inject_config(config_injector):
    config_injector(
        {"privileges": {"tags:resolve_source": model.User.RANK_REGULAR}}
    )


def test_resolving(user_factory, context_factory, monkeypatch):
    monkeypatch.setattr(source_tags, "resolve_source_tag", lambda url: "a.b")
    result = api.source_tag_api.get_source_tag(
        context_factory(
            params={"url": "https://x"},
            user=user_factory(rank=model.User.RANK_REGULAR),
        )
    )
    assert result == {"tag": "a.b"}


def test_missing_url(user_factory, context_factory):
    with pytest.raises(errors.MissingRequiredParameterError):
        api.source_tag_api.get_source_tag(
            context_factory(user=user_factory(rank=model.User.RANK_REGULAR))
        )


def test_without_privileges(user_factory, context_factory):
    with pytest.raises(errors.AuthError):
        api.source_tag_api.get_source_tag(
            context_factory(
                params={"url": "https://x"},
                user=user_factory(rank=model.User.RANK_ANONYMOUS),
            )
        )
