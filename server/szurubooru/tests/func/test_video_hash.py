import pytest

from szurubooru.func import video_hash


def test_generate_hash_produces_a_64_bit_hash(read_asset, config_injector):
    packed_hash = video_hash.generate_hash(read_asset("mp4.mp4"))
    assert isinstance(packed_hash, bytes)
    assert len(packed_hash) == video_hash.HASH_BITS // 8


def test_generate_hash_supports_webm(read_asset, config_injector):
    packed_hash = video_hash.generate_hash(read_asset("webm.webm"))
    assert isinstance(packed_hash, bytes)
    assert len(packed_hash) == video_hash.HASH_BITS // 8


def test_hash_is_deterministic(read_asset, config_injector):
    content = read_asset("mp4.mp4")
    hash1 = video_hash.generate_hash(content)
    hash2 = video_hash.generate_hash(content)
    assert hash1 == hash2
    assert video_hash.normalized_distance(hash1, hash2) == 0.0


def test_generate_hash_for_similar_video(read_asset, config_injector):
    # mp4-similar.mp4 is mp4.mp4's 8x8 black frame with every pixel nudged
    # from #000000 to #010101 (visually indistinguishable, but not byte-identical)
    hash1 = video_hash.generate_hash(read_asset("mp4.mp4"))
    hash2 = video_hash.generate_hash(read_asset("mp4-similar.mp4"))

    assert hash1 != hash2

    distance = video_hash.normalized_distance(hash1, hash2)
    assert 0 < distance < 0.35


def test_generate_hash_for_different_video(read_asset, config_injector):
    hash1 = video_hash.generate_hash(read_asset("mp4.mp4"))
    hash2 = video_hash.generate_hash(read_asset("mp4-different.mp4"))

    distance = video_hash.normalized_distance(hash1, hash2)
    assert distance > video_hash.DISTANCE_CUTOFF


def test_generate_hash_distinguishes_short_real_world_length_clips(read_asset, config_injector):
    # Regression test for a production bug: mp4-clip-a.mp4 (a moving test
    # pattern) and mp4-clip-b.mp4 (color bars) are both 2 seconds long
    # which was short enough to have tripped the old frame-sampling formula
    #
    # A 2s clip at 1 fps yields only ~2 frames, so the collage videohash
    # builds the hash from ends up mostly black padding, leading to excessive
    # false positives / collisions
    #
    # _get_frame_interval now scales sampling up for short clips instead of
    # capping at 1 fps, so these two clearly-different clips should land
    # nowhere near DISTANCE_CUTOFF.
    hash1 = video_hash.generate_hash(read_asset("mp4-clip-a.mp4"))
    hash2 = video_hash.generate_hash(read_asset("mp4-clip-b.mp4"))

    distance = video_hash.normalized_distance(hash1, hash2)
    assert distance > video_hash.DISTANCE_CUTOFF


def test_get_frame_interval_scales_up_for_short_videos():
    assert video_hash._get_frame_interval(b"") == video_hash._DEFAULT_FRAME_INTERVAL

    fi_8s = video_hash._get_frame_interval_for_duration(8.0)
    assert fi_8s > 1.0
    assert fi_8s == pytest.approx(60.0 / 8.0)

    # Very short (sub-second) clips are capped at _MAX_FRAME_INTERVAL rather
    # than being asked to sample at an absurd frame rate.
    fi_tiny = video_hash._get_frame_interval_for_duration(0.01)
    assert fi_tiny == video_hash._MAX_FRAME_INTERVAL

    # Very long videos are still floored at _MIN_FRAME_INTERVAL so hashing
    # time stays bounded.
    fi_long = video_hash._get_frame_interval_for_duration(10000.0)
    assert fi_long == video_hash._MIN_FRAME_INTERVAL


def test_hamming_distance():
    zero = (0).to_bytes(8, "big")
    all_ones = (2**64 - 1).to_bytes(8, "big")
    one_bit = (1).to_bytes(8, "big")

    assert video_hash.hamming_distance(zero, zero) == 0
    assert video_hash.hamming_distance(zero, all_ones) == 64
    assert video_hash.hamming_distance(zero, one_bit) == 1
    assert video_hash.normalized_distance(zero, all_ones) == 1.0
    assert video_hash.normalized_distance(zero, one_bit) == 1 / 64


def test_distance_cutoff_is_a_fraction_of_hash_bits():
    assert 0 < video_hash.DISTANCE_CUTOFF < 1
    assert video_hash.DISTANCE_CUTOFF == video_hash.DISTANCE_CUTOFF_BITS / video_hash.HASH_BITS
