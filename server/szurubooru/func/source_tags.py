import html as html_module
import re
import urllib.error
import urllib.request
from typing import Any, Optional

from szurubooru import config, errors

_timeout = 10
_bot_user_agent = "Mozilla/5.0 (compatible; Discordbot/2.0)"
_default_phixiv_host = "phixiv.net"
_default_vxreddit_host = "vxreddit.com"
_max_response_size = 2 ** 21

_reddit_pattern = re.compile(
    r"^https?://(?:[\w-]+\.)?reddit\.com/(?:r/\w+/)?comments/(\w+)",
    re.IGNORECASE,
)
_pixiv_pattern = re.compile(
    r"^https?://(?:www\.)?pixiv\.net/(?:\w+/)?artworks/(\d+)",
    re.IGNORECASE,
)

_reddit_author_pattern = re.compile(
    r'og:site_name"\s+content="u/([^"\s]+) on ', re.IGNORECASE
)
_pixiv_author_pattern = re.compile(r"/e\?i=(\d+)&")


class SourceLookupError(errors.ProcessingError):
    pass


def _fetch_html(url: str) -> str:
    # The proxy services only serve embed markup to link-preview bots
    request = urllib.request.Request(url)
    request.add_header("User-Agent", _bot_user_agent)
    try:
        with urllib.request.urlopen(request, timeout=_timeout) as handle:
            content = handle.read(_max_response_size)
        return content.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as ex:
        raise SourceLookupError(
            "Source proxy returned HTTP %d. (%s)" % (ex.code, ex.reason),
            extra_fields={"URL": url},
        ) from ex
    except (urllib.error.URLError, OSError) as ex:
        raise SourceLookupError(
            "Could not query source proxy.", extra_fields={"URL": url}
        ) from ex


def _resolve_reddit(post_id: str) -> Optional[str]:
    host = config.config.get("vxreddit_host") or _default_vxreddit_host
    html = _fetch_html("https://%s/comments/%s" % (host, post_id.lower()))
    # vxReddit only exposes the author in og:site_name: "u/<name> on r/<sub>"
    match = _reddit_author_pattern.search(html)
    if not match:
        raise SourceLookupError("Could not find author in vxReddit response.")
    author = html_module.unescape(match.group(1))
    return None if author == "[deleted]" else author + ".reddit"


def _resolve_pixiv(artwork_id: str) -> Optional[str]:
    host = config.config.get("phixiv_host") or _default_phixiv_host
    html = _fetch_html("https://%s/artworks/%s" % (host, artwork_id))
    # phixiv exposes the author ID in its oEmbed link: /e?i=<id>&n=<name>
    match = _pixiv_author_pattern.search(html)
    if not match:
        raise SourceLookupError("Could not find author in phixiv response.")
    return match.group(1) + ".pixiv_id"


def resolve_source_tag(url: str) -> Optional[str]:
    """Return the tag name for a source URL that needs a remote lookup, or
    None if the URL isn't supported or no author could be determined."""
    match = _reddit_pattern.match(url)
    if match:
        return _resolve_reddit(match.group(1))
    match = _pixiv_pattern.match(url)
    if match:
        return _resolve_pixiv(match.group(1))
    return None
