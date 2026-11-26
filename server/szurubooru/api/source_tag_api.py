from typing import Dict

from szurubooru import rest
from szurubooru.func import auth, source_tags


@rest.routes.get("/source-tag/?")
def get_source_tag(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "tags:resolve_source")
    url = ctx.get_param_as_string("url")
    return {"tag": source_tags.resolve_source_tag(url)}
