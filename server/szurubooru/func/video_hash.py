import logging
from typing import Tuple

import numpy as np

from szurubooru import errors
from szurubooru.func import images

logger = logging.getLogger(__name__)

# Perceptual video fingerprint: one 64-bit pHash per evenly spaced frame.
# Two videos match when their runtimes are close and the mean per-frame
# hamming distance is small, which survives re-encodes and rescaling.

FRAMES = 16
SIZE = 32
LOW = 8
MAX_DISTANCE = 8.0
DURATION_TOLERANCE = 0.1
HASH_BITS = 64


def _dct_matrix(n: int) -> np.ndarray:
    k = np.arange(n)[:, None]
    i = np.arange(n)[None, :]
    m = np.cos(np.pi * (2 * i + 1) * k / (2 * n)) * np.sqrt(2 / n)
    m[0] /= np.sqrt(2)
    return m


DCT = _dct_matrix(SIZE)


def _phash(frame: np.ndarray) -> int:
    coeffs = (DCT @ frame.astype(np.float64) @ DCT.T)[:LOW, :LOW].flatten()
    bits = coeffs > np.median(coeffs[1:])
    return int(np.packbits(bits).view(">u8")[0])


def generate_fingerprint(
    content: bytes, low_priority: bool = False
) -> Tuple[float, np.ndarray]:
    """Return the duration and FRAMES pHashes (uint64) of a video."""
    image = images.Image(content)
    duration = image.duration
    if duration <= 0:
        raise errors.ProcessingError("Unable to determine video duration.")
    raw = image.get_gray_frames(SIZE, FRAMES * 2 / duration, low_priority)
    if not raw:
        # e.g. single frame videos, which the fps filter drops entirely
        raw = image.get_gray_frames(SIZE, None, low_priority)
    decoded = np.frombuffer(raw, dtype=np.uint8).reshape(-1, SIZE, SIZE)
    if len(decoded) == 0:
        raise errors.ProcessingError("Unable to decode any video frames.")
    picks = np.linspace(0, len(decoded) - 1, FRAMES).round().astype(int)
    hashes = np.array([_phash(decoded[i]) for i in picks], dtype=np.uint64)
    return duration, hashes


def pack_fingerprint(hashes: np.ndarray) -> bytes:
    return hashes.astype(">u8").tobytes()


def unpack_fingerprint(packed: bytes) -> np.ndarray:
    return np.frombuffer(packed, dtype=">u8").astype(np.uint64)


def mean_distances(candidates: np.ndarray, query: np.ndarray) -> np.ndarray:
    """Mean per-frame hamming distance of each candidate row to the query."""
    return np.bitwise_count(candidates ^ query).mean(axis=1)
