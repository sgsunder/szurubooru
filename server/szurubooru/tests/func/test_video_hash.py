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
    assert (
        video_hash.DISTANCE_CUTOFF
        == video_hash.DISTANCE_CUTOFF_BITS / video_hash.HASH_BITS
    )
