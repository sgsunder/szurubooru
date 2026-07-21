import logging
import os
from typing import Dict

import yaml

from szurubooru import errors

logger = logging.getLogger(__name__)

base_config = {
    "name": "szurubooru",
    "domain": None,
    "secret": "change",
    "delete_source_files": "yes",
    "thumbnails": {
        "avatar_width": 300,
        "avatar_height": 300,
        "post_width": 300,
        "post_height": 300,
    },
    "user_agent": "Mozilla/5.0 (compatible; szurubooru/2.5)",
    "max_dl_filesize": 2000000000,
    "convert": {"gif": {"to_webm": False, "to_mp4": False}},
    "allow_broken_uploads": False,
    "smtp": {
        "host": None,
        "port": None,
        "user": None,
        "pass": None,
        "from": None,
    },
    "contact_email": None,
    "enable_safety": "yes",
    "tag_name_regex": "^\\S+$",
    "tag_category_name_regex": "^[^\\s%+#/]+$",
    "pool_name_regex": "^\\S+$",
    "pool_category_name_regex": "^[^\\s%+#/]+$",
    "password_regex": "^.{5,}$",
    "user_name_regex": "^[a-zA-Z0-9_-]{1,32}$",
    "webhooks": None,
    "default_rank": "regular",
    "privileges": {
        "users:create:self": "anonymous",
        "users:create:any": "administrator",
        "users:list": "regular",
        "users:view": "regular",
        "users:edit:any:name": "moderator",
        "users:edit:any:pass": "moderator",
        "users:edit:any:email": "moderator",
        "users:edit:any:avatar": "moderator",
        "users:edit:any:rank": "moderator",
        "users:edit:self:name": "regular",
        "users:edit:self:pass": "regular",
        "users:edit:self:email": "regular",
        "users:edit:self:avatar": "regular",
        "users:edit:self:rank": "moderator",
        "users:delete:any": "administrator",
        "users:delete:self": "regular",
        "user_tokens:list:any": "administrator",
        "user_tokens:list:self": "regular",
        "user_tokens:create:any": "administrator",
        "user_tokens:create:self": "regular",
        "user_tokens:edit:any": "administrator",
        "user_tokens:edit:self": "regular",
        "user_tokens:delete:any": "administrator",
        "user_tokens:delete:self": "regular",
        "posts:create:anonymous": "regular",
        "posts:create:identified": "regular",
        "posts:list": "anonymous",
        "posts:reverse_search": "regular",
        "posts:view": "anonymous",
        "posts:view:featured": "anonymous",
        "posts:edit:content": "power",
        "posts:edit:flags": "regular",
        "posts:edit:notes": "regular",
        "posts:edit:relations": "regular",
        "posts:edit:safety": "power",
        "posts:edit:source": "regular",
        "posts:edit:tags": "regular",
        "posts:edit:thumbnail": "power",
        "posts:feature": "moderator",
        "posts:delete": "moderator",
        "posts:score": "regular",
        "posts:merge": "moderator",
        "posts:favorite": "regular",
        "posts:bulk-edit:tags": "power",
        "posts:bulk-edit:safety": "power",
        "posts:bulk-edit:delete": "power",
        "tags:create": "regular",
        "tags:edit:names": "power",
        "tags:edit:category": "power",
        "tags:edit:description": "power",
        "tags:edit:implications": "power",
        "tags:edit:suggestions": "power",
        "tags:list": "regular",
        "tags:view": "anonymous",
        "tags:merge": "moderator",
        "tags:delete": "moderator",
        "tags:recommendations": "regular",
        "tag_categories:create": "moderator",
        "tag_categories:edit:name": "moderator",
        "tag_categories:edit:color": "moderator",
        "tag_categories:edit:order": "moderator",
        "tag_categories:edit:weights": "moderator",
        "tag_categories:list": "anonymous",
        "tag_categories:view": "anonymous",
        "tag_categories:delete": "moderator",
        "tag_categories:set_default": "moderator",
        "pools:create": "regular",
        "pools:edit:names": "power",
        "pools:edit:category": "power",
        "pools:edit:description": "power",
        "pools:edit:posts": "power",
        "pools:list": "regular",
        "pools:view": "anonymous",
        "pools:merge": "moderator",
        "pools:delete": "moderator",
        "pool_categories:create": "moderator",
        "pool_categories:edit:name": "moderator",
        "pool_categories:edit:color": "moderator",
        "pool_categories:list": "anonymous",
        "pool_categories:view": "anonymous",
        "pool_categories:delete": "moderator",
        "pool_categories:set_default": "moderator",
        "comments:create": "regular",
        "comments:delete:any": "moderator",
        "comments:delete:own": "regular",
        "comments:edit:any": "moderator",
        "comments:edit:own": "regular",
        "comments:list": "regular",
        "comments:view": "regular",
        "comments:score": "regular",
        "snapshots:list": "power",
        "uploads:create": "regular",
        "uploads:use_downloader": "power",
    },
}


def _merge(left: Dict, right: Dict) -> Dict:
    for key in right:
        if key in left:
            if isinstance(left[key], dict) and isinstance(right[key], dict):
                _merge(left[key], right[key])
            elif left[key] != right[key]:
                left[key] = right[key]
        else:
            left[key] = right[key]
    return left


def _container_config() -> Dict:
    if "TEST_ENVIRONMENT" not in os.environ:
        for key in ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST"]:
            if key not in os.environ:
                raise errors.ConfigError(
                    f'Environment variable "{key}" not set'
                )
    val = {
        "debug": True,
        "show_sql": int(os.getenv("LOG_SQL", 0)),
        "data_url": os.getenv("DATA_URL", "data/"),
        "data_dir": "/data/",
        "database": "postgresql://%(user)s:%(pass)s@%(host)s:%(port)d/%(db)s"
        % {
            "user": os.getenv("POSTGRES_USER"),
            "pass": os.getenv("POSTGRES_PASSWORD"),
            "host": os.getenv("POSTGRES_HOST"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "db": os.getenv("POSTGRES_DB", os.getenv("POSTGRES_USER")),
        },
    }
    if "SZURUBOORU_NAME" in os.environ:
        val["name"] = os.getenv("SZURUBOORU_NAME")
    if "SZURUBOORU_SECRET" in os.environ:
        val["secret"] = os.getenv("SZURUBOORU_SECRET")
    return val


def _file_config(filename: str) -> Dict:
    with open(filename, "rt") as handle:
        return yaml.load(handle.read(), Loader=yaml.SafeLoader) or {}


def _running_inside_container() -> bool:
    env = os.environ.keys()
    return (
        os.path.exists("/.dockerenv")
        or "KUBERNETES_SERVICE_HOST" in env
        or "container" in env  # set by lxc/podman
    )


def _read_config() -> Dict:
    ret = base_config
    if os.path.isfile("/config.yaml"):
        ret = _merge(ret, _file_config("/config.yaml"))
    elif os.path.isdir("/config.yaml"):
        logger.warning(
            "'config.yaml' should be a file, not a directory, skipping"
        )
    if _running_inside_container():
        ret = _merge(ret, _container_config())
    return ret


config = _read_config()
