import logging
import os
from typing import Dict

import yaml

from szurubooru import errors

logger = logging.getLogger(__name__)


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


def _secret_present(var: str) -> bool:
    return var in os.environ or f"{var}_FILE" in os.environ


def _read_secret(var: str) -> str:
    # Read a secret from `<var>`, or from the file named by `<var>_FILE`
    file_var = f"{var}_FILE"
    if file_var in os.environ:
        path = os.environ[file_var]
        try:
            with open(path) as handle:
                return handle.read().strip()
        except OSError as ex:
            raise errors.ConfigError(f'Could not read "{file_var}" at "{path}": {ex}')
    return os.environ[var]


def _env_config() -> Dict:
    val: Dict = {}

    if "SZURUBOORU_NAME" in os.environ:
        val["name"] = os.environ["SZURUBOORU_NAME"]
    if _secret_present("SZURUBOORU_SECRET"):
        val["secret"] = _read_secret("SZURUBOORU_SECRET")
    if "QUIET" in os.environ:
        val["quiet"] = bool(int(os.environ["QUIET"]))
    if "LOG_SQL" in os.environ:
        val["show_sql"] = bool(int(os.environ["LOG_SQL"]))
    if "DATA_URL" in os.environ:
        val["data_url"] = os.environ["DATA_URL"]
    if "DATA_DIR" in os.environ:
        val["data_dir"] = os.environ["DATA_DIR"]

    postgres_present = {
        "POSTGRES_USER": "POSTGRES_USER" in os.environ,
        "POSTGRES_PASSWORD": _secret_present("POSTGRES_PASSWORD"),
        "POSTGRES_HOST": "POSTGRES_HOST" in os.environ,
    }
    if any(postgres_present.values()) or "TEST_ENVIRONMENT" in os.environ:
        missing = [key for key, present in postgres_present.items() if not present]
        if missing and "TEST_ENVIRONMENT" not in os.environ:
            raise errors.ConfigError(f'Environment variable "{missing[0]}" not set')
        val["database"] = "postgresql://%(user)s:%(pass)s@%(host)s:%(port)d/%(db)s" % {
            "user": os.getenv("POSTGRES_USER"),
            "pass": (
                _read_secret("POSTGRES_PASSWORD") if postgres_present["POSTGRES_PASSWORD"] else None
            ),
            "host": os.getenv("POSTGRES_HOST"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "db": os.getenv("POSTGRES_DB", os.getenv("POSTGRES_USER")),
        }

    return val


def _file_config(filename: str) -> Dict:
    with open(filename, "rt") as handle:
        return yaml.load(handle.read(), Loader=yaml.SafeLoader) or {}


def _dist_config_path() -> str:
    # Locate config.yaml.dist
    package_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for candidate in (
        "config.yaml.dist",
        os.path.join(package_root, "config.yaml.dist"),
    ):
        if os.path.isfile(candidate):
            return candidate
    raise errors.ConfigError("Unable to locate config.yaml.dist")


def _user_config_path() -> str:
    return os.getenv("SZURUBOORU_CONFIG_PATH", "config.yaml")


def _read_config() -> Dict:
    ret = _file_config(_dist_config_path())

    user_config_path = _user_config_path()
    if os.path.isfile(user_config_path):
        ret = _merge(ret, _file_config(user_config_path))
    elif os.path.isdir(user_config_path):
        logger.warning("'%s' should be a file, not a directory, skipping" % user_config_path)

    ret = _merge(ret, _env_config())
    return ret


config = _read_config()
