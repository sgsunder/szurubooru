import subprocess

import numpy as np
import pytest

from szurubooru.func import video_hash


def test_fingerprint_shape(read_asset):
    duration, hashes = video_hash.generate_fingerprint(read_asset("mp4.mp4"))
    assert duration > 0
    assert hashes.shape == (video_hash.FRAMES,)
    assert hashes.dtype == np.uint64


def test_fingerprint_pack_round_trip(read_asset):
    _, hashes = video_hash.generate_fingerprint(read_asset("mp4.mp4"))
    packed = video_hash.pack_fingerprint(hashes)
    assert len(packed) == video_hash.FRAMES * 8
    assert np.array_equal(video_hash.unpack_fingerprint(packed), hashes)


def test_mean_distances():
    query = np.array([0, 0], dtype=np.uint64)
    candidates = np.array([[0, 0], [1, 3]], dtype=np.uint64)
    distances = video_hash.mean_distances(candidates, query)
    assert list(distances) == [0.0, 1.25]


def test_mean_distances_tolerates_offset():
    base = np.array([2**i - 1 for i in range(1, 17)], dtype=np.uint64)
    held = np.concatenate([base[:1].repeat(4), base[:-4]])
    distances = video_hash.mean_distances(held[None, :], base)
    assert distances[0] < video_hash.MAX_DISTANCE


def test_reencode_is_close(read_asset, tmp_path):
    original = read_asset("mp4.mp4")
    source = tmp_path / "in.mp4"
    target = tmp_path / "out.mp4"
    source.write_bytes(original)
    try:
        subprocess.run(
            [
                "ffmpeg", "-v", "error", "-y", "-i", str(source),
                "-vf", "scale=iw/2*2:ih/2*2", "-crf", "35", str(target),
            ],
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("ffmpeg unable to transcode test asset")

    _, original_hashes = video_hash.generate_fingerprint(original)
    _, copy_hashes = video_hash.generate_fingerprint(target.read_bytes())
    distance = video_hash.mean_distances(
        copy_hashes[None, :], original_hashes
    )[0]
    assert distance <= video_hash.MAX_DISTANCE
