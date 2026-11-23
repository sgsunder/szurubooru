import logging
from typing import Tuple

import numpy as np

from szurubooru import errors
from szurubooru.func import images

logger = logging.getLogger(__name__)

# Perceptual video fingerprint: one 64-bit pHash per evenly spaced frame.
# Two videos match when their runtimes are close and the mean per-frame
# hamming distance along a time-aligned (DTW) path is small, which survives
# re-encodes, rescaling and differing intros/outros (e.g. a held first frame).

FRAMES = 16
SIZE = 32
LOW = 8
MAX_DISTANCE = 8.0
DURATION_TOLERANCE = 0.1
DURATION_SLACK = 3.0  # seconds, added on top of the relative tolerance
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
    """Mean per-frame hamming distance of each candidate row to the query,
    along the cheapest monotonic alignment of the two frame sequences."""
    # pairwise[c, i, j]: distance of candidate c's frame i to query frame j
    pairwise = np.bitwise_count(
        candidates[:, :, None] ^ query[None, None, :]
    ).astype(np.float64)
    count, rows, cols = pairwise.shape
    # DTW with the symmetric step pattern: diagonal steps count twice, so the
    # total divided by rows + cols is a path-length independent mean.
    cost = np.full((count, rows, cols), np.inf)
    cost[:, 0, 0] = 2 * pairwise[:, 0, 0]
    for i in range(rows):
        for j in range(cols):
            if i == 0 and j == 0:
                continue
            best = np.full(count, np.inf)
            if i and j:
                best = cost[:, i - 1, j - 1] + 2 * pairwise[:, i, j]
            if i:
                best = np.minimum(best, cost[:, i - 1, j] + pairwise[:, i, j])
            if j:
                best = np.minimum(best, cost[:, i, j - 1] + pairwise[:, i, j])
            cost[:, i, j] = best
    return cost[:, -1, -1] / (rows + cols)
