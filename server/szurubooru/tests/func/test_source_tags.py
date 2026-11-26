import urllib.error

import pytest

from szurubooru.func import source_tags


@pytest.fixture(autouse=True)
def inject_config(config_injector):
    config_injector({"user_agent": None})


def _fake_urlopen(monkeypatch, html="", error=None):
    requested = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _size=-1):
            return html.encode("utf-8")

    def urlopen(request, timeout=None):
        requested.append(request.full_url)
        if error:
            raise error
        return _Response()

    monkeypatch.setattr(source_tags.urllib.request, "urlopen", urlopen)
    return requested


def _reddit_html(author):
    return (
        '<meta property="og:site_name" content="u/%s on r/drakengard'
        ' - \u2b06 5 | \U0001f4ac 2" />' % author
    )


def test_reddit(monkeypatch):
    requested = _fake_urlopen(monkeypatch, _reddit_html("asyor_"))
    url = "https://www.reddit.com/r/drakengard/comments/1y5knfe"
    assert source_tags.resolve_source_tag(url) == "asyor_.reddit"
    assert requested == ["https://vxreddit.com/comments/1y5knfe"]


def test_reddit_custom_host(monkeypatch, config_injector):
    config_injector({"user_agent": None, "vxreddit_host": "vx.example.org"})
    requested = _fake_urlopen(monkeypatch, _reddit_html("asyor_"))
    source_tags.resolve_source_tag("https://reddit.com/comments/abc")
    assert requested == ["https://vx.example.org/comments/abc"]


def test_reddit_deleted_author(monkeypatch):
    _fake_urlopen(monkeypatch, _reddit_html("[deleted]"))
    url = "https://www.reddit.com/r/drakengard/comments/1y5knfe"
    assert source_tags.resolve_source_tag(url) is None


def test_reddit_unparseable_response(monkeypatch):
    _fake_urlopen(monkeypatch, "<html></html>")
    with pytest.raises(source_tags.SourceLookupError):
        source_tags.resolve_source_tag("https://reddit.com/comments/abc")


def test_pixiv(monkeypatch):
    html = (
        '<link rel="alternate" type="application/json+oembed" '
        'href="https://phixiv.net/e?i=91381925&n=Name">'
    )
    requested = _fake_urlopen(monkeypatch, html)
    url = "https://www.pixiv.net/en/artworks/147496533"
    assert source_tags.resolve_source_tag(url) == "91381925.pixiv_id"
    assert requested == ["https://phixiv.net/artworks/147496533"]


def test_pixiv_unparseable_response(monkeypatch):
    _fake_urlopen(monkeypatch, "<html></html>")
    with pytest.raises(source_tags.SourceLookupError):
        source_tags.resolve_source_tag("https://www.pixiv.net/artworks/1")


def test_http_error(monkeypatch):
    error = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
    _fake_urlopen(monkeypatch, error=error)
    with pytest.raises(source_tags.SourceLookupError):
        source_tags.resolve_source_tag("https://www.pixiv.net/artworks/1")


def test_unsupported_url_is_not_fetched(monkeypatch):
    requested = _fake_urlopen(monkeypatch)
    assert source_tags.resolve_source_tag("https://example.com/a/1") is None
    url = "https://evil.com/?reddit.com/comments/a"
    assert source_tags.resolve_source_tag(url) is None
    assert requested == []
