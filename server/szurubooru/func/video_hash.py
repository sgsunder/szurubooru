import logging
import os
import tempfile

from PIL import Image as _PILImage

if not hasattr(_PILImage, "ANTIALIAS"):
    # videohash 3.0.1 (last released 2022) references the `Image.ANTIALIAS`
    # constant, which Pillow removed in 9.1/10.0 in favor of `Image.LANCZOS`
    _PILImage.ANTIALIAS = _PILImage.LANCZOS

import videohash  # noqa: E402

from szurubooru import errors
from szurubooru.func import images, mime, util

logger = logging.getLogger(__name__)


HASH_BITS = 64
DISTANCE_CUTOFF_BITS = 10
"""Untuned starting point. Adjust based on real-world testing."""

_MIN_FRAME_INTERVAL = 0.1
_DEFAULT_FRAME_INTERVAL = 1.0
_TARGET_SAMPLE_FRAMES = 60
"""
Scale long videos down to keep hashing time roughly bounded for long videos,
by ensuring that all videos sample this many frames.
"""

DISTANCE_CUTOFF = DISTANCE_CUTOFF_BITS / HASH_BITS


def _get_frame_interval(content: bytes) -> float:
    try:
        duration = float(images.Image(content).info["format"]["duration"])
    except (errors.ProcessingError, KeyError, ValueError, TypeError):
        return _DEFAULT_FRAME_INTERVAL
    if duration <= 0:
        return _DEFAULT_FRAME_INTERVAL
    return max(
        _MIN_FRAME_INTERVAL,
        min(_DEFAULT_FRAME_INTERVAL, _TARGET_SAMPLE_FRAMES / duration),
    )


def generate_hash(content: bytes) -> bytes:
    extension = mime.get_extension(mime.get_mime_type(content))
    if not extension:
        raise errors.ProcessingError(
            "Unable to generate a video hash for this file."
        )

    frame_interval = _get_frame_interval(content)

    try:
        with util.create_temp_file(suffix="." + extension) as handle:
            handle.write(content)
            handle.flush()
            with tempfile.TemporaryDirectory() as storage_path:
                result = videohash.VideoHash(
                    path=handle.name,
                    # videohash's own does_path_exists() only recognizes a
                    # directory if the path ends with a separator, else it
                    # checks os.path.isfile() and rejects a perfectly valid
                    # directory -- trailing sep is required here.
                    storage_path=storage_path + os.sep,
                    frame_interval=frame_interval,
                )
                hash_int = int(result.hash, 2)
                return hash_int.to_bytes(HASH_BITS // 8, "big")
    except errors.ProcessingError:
        raise
    except Exception as ex:
        logger.warning("Unable to generate video hash (%r)", ex)
        raise errors.ProcessingError(
            "Unable to generate a video hash for this video."
        )


def hamming_distance(hash_a: bytes, hash_b: bytes) -> int:
    return bin(
        int.from_bytes(hash_a, "big") ^ int.from_bytes(hash_b, "big")
    ).count("1")


def normalized_distance(hash_a: bytes, hash_b: bytes) -> float:
    return hamming_distance(hash_a, hash_b) / HASH_BITS
