import json
import os
from datetime import datetime
from unittest.mock import patch

import pytest

from szurubooru import db, model
from szurubooru.func import cache, tag_categories, tags


@pytest.fixture(autouse=True)
def purge_cache():
    cache.purge()


def _assert_tag_siblings(result, expected_names_and_occurrences):
    actual_names_and_occurences = [
        (tag.names[0].name, occurrences) for tag, occurrences in result
    ]
    assert actual_names_and_occurences == expected_names_and_occurrences


@pytest.mark.parametrize(
    "input,expected_tag_names",
    [
        (
            [("a", "a", True), ("b", "b", False), ("c", "c", False)],
            list("bca"),
        ),
        (
            [("c", "a", True), ("b", "b", False), ("a", "c", False)],
            list("bac"),
        ),
        (
            [("a", "c", True), ("b", "b", False), ("c", "a", False)],
            list("cba"),
        ),
        (
            [("a", "c", False), ("b", "b", False), ("c", "a", True)],
            list("bac"),
        ),
    ],
)
def test_sort_tags(
    input, expected_tag_names, tag_factory, tag_category_factory
):
    db_tags = []
    for tag in input:
        tag_name, category_name, category_is_default = tag
        db_tags.append(
            tag_factory(
                names=[tag_name],
                category=tag_category_factory(
                    name=category_name, default=category_is_default
                ),
            )
        )
    db.session.add_all(db_tags)
    db.session.flush()
    actual_tag_names = [tag.names[0].name for tag in tags.sort_tags(db_tags)]
    assert actual_tag_names == expected_tag_names


def test_serialize_tag_when_empty():
    assert tags.serialize_tag(None, None) is None


def test_serialize_tag(post_factory, tag_factory, tag_category_factory):
    cat = tag_category_factory(name="cat")
    tag = tag_factory(names=["tag1", "tag2"], category=cat)
    # tag.tag_id = 1
    tag.description = "description"
    tag.suggestions = [
        tag_factory(names=["sug1"], category=cat),
        tag_factory(names=["sug2"], category=cat),
    ]
    tag.implications = [
        tag_factory(names=["impl1"], category=cat),
        tag_factory(names=["impl2"], category=cat),
    ]
    tag.last_edit_time = datetime(1998, 1, 1)

    post1 = post_factory()
    post1.tags = [tag]
    post2 = post_factory()
    post2.tags = [tag]
    db.session.add_all([tag, post1, post2])
    db.session.flush()

    result = tags.serialize_tag(tag)
    result["suggestions"].sort(key=lambda relation: relation["names"][0])
    result["implications"].sort(key=lambda relation: relation["names"][0])
    assert result == {
        "names": ["tag1", "tag2"],
        "version": 1,
        "category": "cat",
        "creationTime": datetime(1996, 1, 1, 0, 0),
        "lastEditTime": datetime(1998, 1, 1, 0, 0),
        "description": "description",
        "suggestions": [
            {"names": ["sug1"], "category": "cat", "usages": 0},
            {"names": ["sug2"], "category": "cat", "usages": 0},
        ],
        "implications": [
            {"names": ["impl1"], "category": "cat", "usages": 0},
            {"names": ["impl2"], "category": "cat", "usages": 0},
        ],
        "usages": 2,
    }


@pytest.mark.parametrize(
    "name_to_search,expected_to_find",
    [
        ("name", True),
        ("NAME", True),
        ("alias", True),
        ("ALIAS", True),
        ("-", False),
    ],
)
def test_try_get_tag_by_name(name_to_search, expected_to_find, tag_factory):
    tag = tag_factory(names=["name", "ALIAS"])
    db.session.add(tag)
    db.session.flush()
    if expected_to_find:
        assert tags.try_get_tag_by_name(name_to_search) == tag
    else:
        assert tags.try_get_tag_by_name(name_to_search) is None


@pytest.mark.parametrize(
    "name_to_search,expected_to_find",
    [
        ("name", True),
        ("NAME", True),
        ("alias", True),
        ("ALIAS", True),
        ("-", False),
    ],
)
def test_get_tag_by_name(name_to_search, expected_to_find, tag_factory):
    tag = tag_factory(names=["name", "ALIAS"])
    db.session.add(tag)
    db.session.flush()
    if expected_to_find:
        assert tags.get_tag_by_name(name_to_search) == tag
    else:
        with pytest.raises(tags.TagNotFoundError):
            tags.get_tag_by_name(name_to_search)


@pytest.mark.parametrize(
    "names,expected_indexes",
    [
        ([], []),
        (["name1"], [0]),
        (["NAME1"], [0]),
        (["alias1"], [0]),
        (["ALIAS1"], [0]),
        (["name2"], [1]),
        (["name1", "name1"], [0]),
        (["name1", "NAME1"], [0]),
        (["name1", "alias1"], [0]),
        (["name1", "alias2"], [0, 1]),
        (["NAME1", "alias2"], [0, 1]),
        (["name1", "ALIAS2"], [0, 1]),
        (["name2", "alias1"], [0, 1]),
    ],
)
def test_get_tag_by_names(names, expected_indexes, tag_factory):
    input_tags = [
        tag_factory(names=["name1", "ALIAS1"]),
        tag_factory(names=["name2", "ALIAS2"]),
    ]
    db.session.add_all(input_tags)
    db.session.flush()
    expected_ids = [input_tags[i].tag_id for i in expected_indexes]
    actual_ids = [tag.tag_id for tag in tags.get_tags_by_names(names)]
    assert actual_ids == expected_ids


@pytest.mark.parametrize(
    "names,expected_indexes,expected_created_names",
    [
        ([], [], []),
        (["name1"], [0], []),
        (["NAME1"], [0], []),
        (["alias1"], [0], []),
        (["ALIAS1"], [0], []),
        (["name2"], [1], []),
        (["name1", "name1"], [0], []),
        (["name1", "NAME1"], [0], []),
        (["name1", "alias1"], [0], []),
        (["name1", "alias2"], [0, 1], []),
        (["NAME1", "alias2"], [0, 1], []),
        (["name1", "ALIAS2"], [0, 1], []),
        (["name2", "alias1"], [0, 1], []),
        (["new"], [], ["new"]),
        (["new", "name1"], [0], ["new"]),
        (["new", "NAME1"], [0], ["new"]),
        (["new", "alias1"], [0], ["new"]),
        (["new", "ALIAS1"], [0], ["new"]),
        (["new", "name2"], [1], ["new"]),
        (["new", "name1", "name1"], [0], ["new"]),
        (["new", "name1", "NAME1"], [0], ["new"]),
        (["new", "name1", "alias1"], [0], ["new"]),
        (["new", "name1", "alias2"], [0, 1], ["new"]),
        (["new", "NAME1", "alias2"], [0, 1], ["new"]),
        (["new", "name1", "ALIAS2"], [0, 1], ["new"]),
        (["new", "name2", "alias1"], [0, 1], ["new"]),
        (["new", "new"], [], ["new"]),
        (["new", "NEW"], [], ["new"]),
        (["new", "new2"], [], ["new", "new2"]),
    ],
)
def test_get_or_create_tags_by_names(
    names,
    expected_indexes,
    expected_created_names,
    tag_factory,
    tag_category_factory,
    config_injector,
):
    config_injector({"tag_name_regex": ".*"})
    category = tag_category_factory()
    input_tags = [
        tag_factory(names=["name1", "ALIAS1"], category=category),
        tag_factory(names=["name2", "ALIAS2"], category=category),
    ]
    db.session.add_all(input_tags)
    db.session.flush()
    result = tags.get_or_create_tags_by_names(names)
    expected_ids = [input_tags[i].tag_id for i in expected_indexes]
    actual_ids = [tag.tag_id for tag in result[0]]
    actual_created_names = [tag.names[0].name for tag in result[1]]
    assert actual_ids == expected_ids
    assert actual_created_names == expected_created_names


def test_get_tag_siblings_for_unused(tag_factory):
    tag = tag_factory(names=["tag"])
    db.session.add(tag)
    db.session.flush()
    _assert_tag_siblings(tags.get_tag_siblings(tag), [])


def test_get_tag_siblings_for_used_alone(tag_factory, post_factory):
    tag = tag_factory(names=["tag"])
    post = post_factory()
    post.tags = [tag]
    db.session.add_all([post, tag])
    db.session.flush()
    _assert_tag_siblings(tags.get_tag_siblings(tag), [])


def test_get_tag_siblings_for_used_with_others(tag_factory, post_factory):
    tag1 = tag_factory(names=["t1"])
    tag2 = tag_factory(names=["t2"])
    post = post_factory()
    post.tags = [tag1, tag2]
    db.session.add_all([post, tag1, tag2])
    db.session.flush()
    _assert_tag_siblings(tags.get_tag_siblings(tag1), [("t2", 1)])
    _assert_tag_siblings(tags.get_tag_siblings(tag2), [("t1", 1)])


def test_get_tag_siblings_used_for_multiple_others(tag_factory, post_factory):
    tag1 = tag_factory(names=["t1"])
    tag2 = tag_factory(names=["t2"])
    tag3 = tag_factory(names=["t3"])
    post1 = post_factory()
    post2 = post_factory()
    post3 = post_factory()
    post4 = post_factory()
    post1.tags = [tag1, tag2, tag3]
    post2.tags = [tag1, tag3]
    post3.tags = [tag2]
    post4.tags = [tag2]
    db.session.add_all([post1, post2, post3, post4, tag1, tag2, tag3])
    db.session.flush()
    _assert_tag_siblings(tags.get_tag_siblings(tag1), [("t3", 2), ("t2", 1)])
    _assert_tag_siblings(tags.get_tag_siblings(tag2), [("t1", 1), ("t3", 1)])
    # even though tag2 is used more widely, tag1 is more relevant to tag3
    _assert_tag_siblings(tags.get_tag_siblings(tag3), [("t1", 2), ("t2", 1)])


def _assert_tag_recommendations(result, expected_names_and_scores):
    actual = [(tag.names[0].name, round(score, 5)) for tag, score in result]
    expected = [
        (name, round(score, 5)) for name, score in expected_names_and_scores
    ]
    assert actual == expected


def test_get_tag_recommendations_for_unused_input(tag_factory):
    tag = tag_factory(names=["tag"])
    db.session.add(tag)
    db.session.flush()
    assert tags.get_tag_recommendations([tag]) == []


def test_get_tag_recommendations_no_other_tags(tag_factory, post_factory):
    tag = tag_factory(names=["tag"])
    post = post_factory()
    post.tags = [tag]
    db.session.add_all([post, tag])
    db.session.flush()
    assert tags.get_tag_recommendations([tag]) == []


def test_get_tag_recommendations_single_input_tag(tag_factory, post_factory):
    t1 = tag_factory(names=["t1"])
    t2 = tag_factory(names=["t2"])
    t3 = tag_factory(names=["t3"])
    post1 = post_factory()
    post1.tags = [t1, t2]
    post2 = post_factory()
    post2.tags = [t3]
    db.session.add_all([post1, post2, t1, t2, t3])
    db.session.flush()
    # 2 posts total, t2 co-occurs with t1 once
    # both t1 and t2 have a post_count of 1 => pmi = log(1 * 2 / (1 * 1)) = log(2)
    # joint_prob = 1/2, so npmi = log(2) / -log(1/2) = 1.0
    _assert_tag_recommendations(tags.get_tag_recommendations([t1]), [("t2", 1.0)])


def test_get_tag_recommendations_multiple_input_tags_aggregate(
    tag_factory, post_factory
):
    t1 = tag_factory(names=["t1"])
    t2 = tag_factory(names=["t2"])
    tag_a = tag_factory(names=["ta"])
    tag_b = tag_factory(names=["tb"])
    post1 = post_factory()
    post1.tags = [t1, t2, tag_a]
    post2 = post_factory()
    post2.tags = [t1, tag_b]
    db.session.add_all([post1, post2, t1, t2, tag_a, tag_b])
    db.session.flush()
    # ta co-occurs with t1 once (pmi=log(1*2/(1*2))=0, npmi=0) and with
    # t2 once (pmi=log(1*2/(1*1))=log(2), joint_prob=1/2, npmi=1.0); tb
    # co-occurs with t1 only (pmi=0, npmi=0)
    expected_score_a = 0.0 + 1.0
    expected_score_b = 0.0
    _assert_tag_recommendations(
        tags.get_tag_recommendations([t1, t2]),
        [("ta", expected_score_a), ("tb", expected_score_b)],
    )


def test_get_tag_recommendations_rare_specific_beats_common_generic(
    tag_factory, post_factory
):
    t1 = tag_factory(names=["t1"])
    tag_generic = tag_factory(names=["generic"])
    tag_rare = tag_factory(names=["rare"])
    post_generic = post_factory()
    post_generic.tags = [t1, tag_generic]
    post_rare = post_factory()
    post_rare.tags = [t1, tag_rare]
    # tag_generic co-occurs with t1 only once, like tag_rare, but also
    # shows up on a bunch of unrelated posts, so it shouldn't outrank
    # tag_rare just because it's more popular overall.
    solo_posts = []
    for _ in range(9):
        solo_post = post_factory()
        solo_post.tags = [tag_generic]
        solo_posts.append(solo_post)
    db.session.add_all(
        [post_generic, post_rare, t1, tag_generic, tag_rare] + solo_posts
    )
    db.session.flush()
    scores = {
        tag.names[0].name: score
        for tag, score in tags.get_tag_recommendations([t1])
    }
    assert scores["rare"] > scores["generic"]


def test_get_tag_recommendations_excludes_input_tags(
    tag_factory, post_factory
):
    t1 = tag_factory(names=["t1"])
    t2 = tag_factory(names=["t2"])
    t3 = tag_factory(names=["t3"])
    post = post_factory()
    post.tags = [t1, t2, t3]
    db.session.add_all([post, t1, t2, t3])
    db.session.flush()
    result_names = [
        tag.names[0].name for tag, _ in tags.get_tag_recommendations([t1, t2])
    ]
    assert "t1" not in result_names
    assert "t2" not in result_names
    assert "t3" in result_names


def test_get_tag_recommendations_respects_limit(tag_factory, post_factory):
    t1 = tag_factory(names=["t1"])
    new_objects = [t1]
    for i, name in enumerate(["c1", "c2", "c3", "c4", "c5"]):
        candidate = tag_factory(names=[name])
        co_post = post_factory()
        co_post.tags = [t1, candidate]
        new_objects += [candidate, co_post]
        for _ in range(i):
            solo_post = post_factory()
            solo_post.tags = [candidate]
            new_objects.append(solo_post)
    db.session.add_all(new_objects)
    db.session.flush()
    result = tags.get_tag_recommendations([t1], limit=3)
    assert [tag.names[0].name for tag, _ in result] == ["c1", "c2", "c3"]


def test_get_tag_recommendations_tie_break_by_name(tag_factory, post_factory):
    t1 = tag_factory(names=["t1"])
    tag_a = tag_factory(names=["aaa"])
    tag_b = tag_factory(names=["bbb"])
    post_a = post_factory()
    post_a.tags = [t1, tag_a]
    post_b = post_factory()
    post_b.tags = [t1, tag_b]
    db.session.add_all([post_a, post_b, t1, tag_a, tag_b])
    db.session.flush()
    result = tags.get_tag_recommendations([t1])
    assert [tag.names[0].name for tag, _ in result] == ["aaa", "bbb"]


def test_get_tag_recommendations_deduplicates_input_tags(
    tag_factory, post_factory
):
    t1 = tag_factory(names=["t1"])
    t2 = tag_factory(names=["t2"])
    post = post_factory()
    post.tags = [t1, t2]
    db.session.add_all([post, t1, t2])
    db.session.flush()
    result_dup = tags.get_tag_recommendations([t1, t1])
    result_single = tags.get_tag_recommendations([t1])
    _assert_tag_recommendations(
        result_dup,
        [(tag.names[0].name, score) for tag, score in result_single],
    )


@pytest.mark.parametrize(
    "weight, expected_score",
    [
        (1.0, 0.5),  # default: gamma=1, identity transform
        (4.0, 0.5**0.5),  # weight>1: gamma=0.5, pulls toward the max
        (0.25, 0.5**2),  # weight<1: gamma=2, pulls toward zero
    ],
)
def test_get_tag_recommendations_category_weight_is_configurable(
    weight, expected_score, tag_factory, tag_category_factory, post_factory
):
    category = tag_category_factory(
        name="weighted", recommendation_weight=weight
    )
    db.session.add(category)
    t1 = tag_factory(names=["t1"])
    candidate = tag_factory(names=["candidate"], category=category)
    post_a = post_factory()
    post_a.tags = [t1, candidate]
    post_b = post_factory()
    post_b.tags = [candidate]
    post_c = post_factory()
    post_d = post_factory()
    db.session.add_all(
        [post_a, post_b, post_c, post_d, t1, candidate]
    )
    db.session.flush()
    # t1 usages=1, candidate usages=2, co=1, total_posts=4:
    # pmi = log(1*4/(2*1)) = log(2); joint_prob = 1/4
    # npmi = log(2) / -log(1/4) = 0.5 (the unweighted score)
    _assert_tag_recommendations(
        tags.get_tag_recommendations([t1]),
        [("candidate", expected_score)],
    )


def test_get_tag_recommendations_strong_signal_survives_low_weight(
    tag_factory, tag_category_factory, post_factory
):
    # weight=0.25 => gamma=2: a moderate match (npmi=0.5) is crushed to
    # 0.5**2=0.25, but a near-perfect match (npmi=1.0) barely moves
    # (1.0**2=1.0)
    #
    # a strong enough signal still breaks through a
    # low-weighted category instead of being flattened along with weak
    # matches in the same category.
    category = tag_category_factory(name="low", recommendation_weight=0.25)
    db.session.add(category)
    t_strong = tag_factory(names=["t_strong"])
    t_moderate = tag_factory(names=["t_moderate"])
    candidate_strong = tag_factory(
        names=["candidate_strong"], category=category
    )
    candidate_moderate = tag_factory(
        names=["candidate_moderate"], category=category
    )
    post_s = post_factory()
    post_s.tags = [t_strong, candidate_strong]
    post_m = post_factory()
    post_m.tags = [t_moderate, candidate_moderate]
    post_m2 = post_factory()
    post_m2.tags = [candidate_moderate]
    post_f = post_factory()
    db.session.add_all(
        [
            post_s,
            post_m,
            post_m2,
            post_f,
            t_strong,
            t_moderate,
            candidate_strong,
            candidate_moderate,
        ]
    )
    db.session.flush()
    _assert_tag_recommendations(
        tags.get_tag_recommendations([t_strong, t_moderate]),
        [("candidate_strong", 1.0), ("candidate_moderate", 0.25)],
    )


def test_delete(tag_factory):
    tag = tag_factory(names=["tag"])
    tag.suggestions = [tag_factory(names=["sug"])]
    tag.implications = [tag_factory(names=["imp"])]
    db.session.add(tag)
    db.session.flush()
    assert db.session.query(model.Tag).count() == 3
    tags.delete(tag)
    db.session.flush()
    assert db.session.query(model.Tag).count() == 2


def test_merge_tags_deletes_source_tag(tag_factory):
    source_tag = tag_factory(names=["source"])
    target_tag = tag_factory(names=["target"])
    db.session.add_all([source_tag, target_tag])
    db.session.flush()
    tags.merge_tags(source_tag, target_tag)
    db.session.flush()
    assert tags.try_get_tag_by_name("source") is None
    tag = tags.get_tag_by_name("target")
    assert tag is not None


def test_merge_tags_with_itself(tag_factory):
    source_tag = tag_factory(names=["source"])
    db.session.add(source_tag)
    db.session.flush()
    with pytest.raises(tags.InvalidTagRelationError):
        tags.merge_tags(source_tag, source_tag)


def test_merge_tags_moves_usages(tag_factory, post_factory):
    source_tag = tag_factory(names=["source"])
    target_tag = tag_factory(names=["target"])
    post = post_factory()
    post.tags = [source_tag]
    db.session.add_all([source_tag, target_tag, post])
    db.session.commit()
    assert source_tag.post_count == 1
    assert target_tag.post_count == 0
    tags.merge_tags(source_tag, target_tag)
    db.session.commit()
    assert tags.try_get_tag_by_name("source") is None
    assert tags.get_tag_by_name("target").post_count == 1


def test_merge_tags_doesnt_duplicate_usages(tag_factory, post_factory):
    source_tag = tag_factory(names=["source"])
    target_tag = tag_factory(names=["target"])
    post = post_factory()
    post.tags = [source_tag, target_tag]
    db.session.add_all([source_tag, target_tag, post])
    db.session.flush()
    assert source_tag.post_count == 1
    assert target_tag.post_count == 1
    tags.merge_tags(source_tag, target_tag)
    db.session.flush()
    assert tags.try_get_tag_by_name("source") is None
    assert tags.get_tag_by_name("target").post_count == 1


def test_merge_tags_moves_child_relations(tag_factory):
    source_tag = tag_factory(names=["source"])
    target_tag = tag_factory(names=["target"])
    related_tag = tag_factory()
    source_tag.suggestions = [related_tag]
    source_tag.implications = [related_tag]
    db.session.add_all([source_tag, target_tag, related_tag])
    db.session.commit()
    assert source_tag.suggestion_count == 1
    assert source_tag.implication_count == 1
    assert target_tag.suggestion_count == 0
    assert target_tag.implication_count == 0
    tags.merge_tags(source_tag, target_tag)
    db.session.commit()
    assert tags.try_get_tag_by_name("source") is None
    assert tags.get_tag_by_name("target").suggestion_count == 1
    assert tags.get_tag_by_name("target").implication_count == 1


def test_merge_tags_doesnt_duplicate_child_relations(tag_factory):
    source_tag = tag_factory(names=["source"])
    target_tag = tag_factory(names=["target"])
    related_tag = tag_factory()
    source_tag.suggestions = [related_tag]
    source_tag.implications = [related_tag]
    target_tag.suggestions = [related_tag]
    target_tag.implications = [related_tag]
    db.session.add_all([source_tag, target_tag, related_tag])
    db.session.commit()
    assert source_tag.suggestion_count == 1
    assert source_tag.implication_count == 1
    assert target_tag.suggestion_count == 1
    assert target_tag.implication_count == 1
    tags.merge_tags(source_tag, target_tag)
    db.session.commit()
    assert tags.try_get_tag_by_name("source") is None
    assert tags.get_tag_by_name("target").suggestion_count == 1
    assert tags.get_tag_by_name("target").implication_count == 1


def test_merge_tags_moves_parent_relations(tag_factory):
    source_tag = tag_factory(names=["source"])
    target_tag = tag_factory(names=["target"])
    related_tag = tag_factory(names=["related"])
    related_tag.suggestions = [related_tag]
    related_tag.implications = [related_tag]
    db.session.add_all([source_tag, target_tag, related_tag])
    db.session.commit()
    assert source_tag.suggestion_count == 0
    assert source_tag.implication_count == 0
    assert target_tag.suggestion_count == 0
    assert target_tag.implication_count == 0
    tags.merge_tags(source_tag, target_tag)
    db.session.commit()
    assert tags.try_get_tag_by_name("source") is None
    assert tags.get_tag_by_name("related").suggestion_count == 1
    assert tags.get_tag_by_name("related").suggestion_count == 1
    assert tags.get_tag_by_name("target").suggestion_count == 0
    assert tags.get_tag_by_name("target").implication_count == 0


def test_merge_tags_doesnt_create_relation_loop_for_children(tag_factory):
    source_tag = tag_factory(names=["source"])
    target_tag = tag_factory(names=["target"])
    source_tag.suggestions = [target_tag]
    source_tag.implications = [target_tag]
    db.session.add_all([source_tag, target_tag])
    db.session.commit()
    assert source_tag.suggestion_count == 1
    assert source_tag.implication_count == 1
    assert target_tag.suggestion_count == 0
    assert target_tag.implication_count == 0
    tags.merge_tags(source_tag, target_tag)
    db.session.commit()
    assert tags.try_get_tag_by_name("source") is None
    assert tags.get_tag_by_name("target").suggestion_count == 0
    assert tags.get_tag_by_name("target").implication_count == 0


def test_merge_tags_doesnt_create_relation_loop_for_parents(tag_factory):
    source_tag = tag_factory(names=["source"])
    target_tag = tag_factory(names=["target"])
    target_tag.suggestions = [source_tag]
    target_tag.implications = [source_tag]
    db.session.add_all([source_tag, target_tag])
    db.session.commit()
    assert source_tag.suggestion_count == 0
    assert source_tag.implication_count == 0
    assert target_tag.suggestion_count == 1
    assert target_tag.implication_count == 1
    tags.merge_tags(source_tag, target_tag)
    db.session.commit()
    assert tags.try_get_tag_by_name("source") is None
    assert tags.get_tag_by_name("target").suggestion_count == 0
    assert tags.get_tag_by_name("target").implication_count == 0


def test_create_tag(fake_datetime):
    with patch("szurubooru.func.tags.update_tag_names"), patch(
        "szurubooru.func.tags.update_tag_category_name"
    ), patch("szurubooru.func.tags.update_tag_suggestions"), patch(
        "szurubooru.func.tags.update_tag_implications"
    ), fake_datetime(
        "1997-01-01"
    ):
        tag = tags.create_tag(["name"], "cat", ["sug"], ["imp"])
        assert tag.creation_time == datetime(1997, 1, 1)
        assert tag.last_edit_time is None
        tags.update_tag_names.assert_called_once_with(tag, ["name"])
        tags.update_tag_category_name.assert_called_once_with(tag, "cat")
        tags.update_tag_suggestions.assert_called_once_with(tag, ["sug"])
        tags.update_tag_implications.assert_called_once_with(tag, ["imp"])


def test_update_tag_category_name(tag_factory):
    with patch("szurubooru.func.tag_categories.get_category_by_name"):
        tag_categories.get_category_by_name.return_value = "mocked"
        tag = tag_factory()
        tags.update_tag_category_name(tag, "cat")
        tag_categories.get_category_by_name.assert_called_once_with("cat")
        assert tag.category == "mocked"


def test_update_tag_names_to_empty(tag_factory):
    tag = tag_factory()
    with pytest.raises(tags.InvalidTagNameError):
        tags.update_tag_names(tag, [])


def test_update_tag_names_with_invalid_name(config_injector, tag_factory):
    config_injector({"tag_name_regex": "^[a-z]*$"})
    tag = tag_factory()
    with pytest.raises(tags.InvalidTagNameError):
        tags.update_tag_names(tag, ["0"])


def test_update_tag_names_with_too_long_string(config_injector, tag_factory):
    config_injector({"tag_name_regex": "^[a-z]*$"})
    tag = tag_factory()
    with pytest.raises(tags.InvalidTagNameError):
        tags.update_tag_names(tag, ["a" * 300])


def test_update_tag_names_with_duplicate_names(config_injector, tag_factory):
    config_injector({"tag_name_regex": "^[a-z]*$"})
    tag = tag_factory()
    tags.update_tag_names(tag, ["a", "A"])
    assert [tag_name.name for tag_name in tag.names] == ["a"]


def test_update_tag_names_trying_to_use_taken_name(
    config_injector, tag_factory
):
    config_injector({"tag_name_regex": "^[a-zA-Z]*$"})
    existing_tag = tag_factory(names=["a"])
    db.session.add(existing_tag)
    tag = tag_factory()
    db.session.add(tag)
    db.session.flush()
    with pytest.raises(tags.TagAlreadyExistsError):
        tags.update_tag_names(tag, ["a"])
    with pytest.raises(tags.TagAlreadyExistsError):
        tags.update_tag_names(tag, ["A"])


@pytest.mark.parametrize("name", list("aA"))
def test_update_tag_names_reusing_own_name(config_injector, tag_factory, name):
    config_injector({"tag_name_regex": "^[a-zA-Z]*$"})
    tag = tag_factory(names=["a"])
    db.session.add(tag)
    db.session.flush()
    tags.update_tag_names(tag, [name])
    assert [tag_name.name for tag_name in tag.names] == [name]


def test_update_tag_names_changing_primary_name(config_injector, tag_factory):
    config_injector({"tag_name_regex": "^[a-zA-Z]*$"})
    tag = tag_factory(names=["a", "b"])
    db.session.add(tag)
    db.session.flush()
    tags.update_tag_names(tag, ["b", "a"])
    db.session.flush()
    db.session.refresh(tag)
    assert [tag_name.name for tag_name in tag.names] == ["b", "a"]


@pytest.mark.parametrize("attempt", ["name", "NAME", "alias", "ALIAS"])
def test_update_tag_suggestions_with_itself(attempt, tag_factory):
    tag = tag_factory(names=["name", "ALIAS"])
    with pytest.raises(tags.InvalidTagRelationError):
        tags.update_tag_suggestions(tag, [attempt])


def test_update_tag_suggestions(tag_factory):
    tag = tag_factory(names=["name", "ALIAS"])
    with patch("szurubooru.func.tags.get_tags_by_names"):
        tags.get_tags_by_names.return_value = ["returned tags"]
        tags.update_tag_suggestions(tag, ["test"])
        assert tag.suggestions == ["returned tags"]


@pytest.mark.parametrize("attempt", ["name", "NAME", "alias", "ALIAS"])
def test_update_tag_implications_with_itself(attempt, tag_factory):
    tag = tag_factory(names=["name", "ALIAS"])
    with pytest.raises(tags.InvalidTagRelationError):
        tags.update_tag_implications(tag, [attempt])


def test_update_tag_implications(tag_factory):
    tag = tag_factory(names=["name", "ALIAS"])
    with patch("szurubooru.func.tags.get_tags_by_names"):
        tags.get_tags_by_names.return_value = ["returned tags"]
        tags.update_tag_implications(tag, ["test"])
        assert tag.implications == ["returned tags"]


def test_update_tag_description(tag_factory):
    tag = tag_factory()
    tags.update_tag_description(tag, "test")
    assert tag.description == "test"
