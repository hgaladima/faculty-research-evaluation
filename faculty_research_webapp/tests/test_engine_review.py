"""Tests for the findings of the engine review (numbered as reported) and the boundaries it found untested."""
import copy
import random

import pytest

from engine import LEGACY, PROVISIONAL, check_policy, evaluate, fingerprint, report, validate
from engine.policy import diff, from_json, normalise, to_json
from engine.research_eval import DOES_NOT_MEET, EXCEEDS, INCOMPLETE, MEETS, _round1
from engine.scenarios import SCENARIOS, A
from test_engine import COMPARED, ORIGINAL, _random_profile

MIN_G = [{"size": "major", "role": "Co-I"}]
MIN_R = [{"type": "poster", "venue": "B", "role": "presenter"}]
PI_MAJOR = {"size": "major", "role": "PI"}


def profile(**kw):
    base = {"publications": [A(3), A(3)], "submissions": MIN_G, "presentations": MIN_R}
    base.update(kw)
    return base


def policy(base=PROVISIONAL, **settings):
    p = copy.deepcopy(base)
    for key, value in settings.items():
        if isinstance(value, dict) and isinstance(p.get(key), dict):
            p[key] = {**p[key], **value}
        else:
            p[key] = value
    return p


def pending(result):
    return [f for f in result["flags"] if "pending verification" in f]


# 1 ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("award_role", [None, "consultant", "collaborator", "PI"])
def test_1_recording_the_award_never_removes_the_grant_minimum(award_role):
    submitted = evaluate(profile(submissions=[dict(PI_MAJOR, id="G1")]), PROVISIONAL)
    award = {"size": "major", "id": "G1"} | ({"role": award_role} if award_role else {})
    funded = evaluate(profile(submissions=[dict(PI_MAJOR, id="G1")], awards=[award]), PROVISIONAL)
    assert submitted["gates"]["G"] and funded["gates"]["G"]
    assert funded["class"] != DOES_NOT_MEET


def test_1_a_non_qualifying_submission_still_does_not_meet_the_minimum_when_funded():
    fac = profile(submissions=[{"size": "major", "role": "collaborator", "id": "G1"}],
                  awards=[{"size": "major", "role": "consultant", "id": "G1"}])
    assert evaluate(fac, PROVISIONAL)["gates"]["G"] is False


# 2 ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("weights", [(50.2, 34.9, 14.9), (33.34, 33.33, 33.33), (42.5, 42.5, 15.0),
                                     (50.0, 35.0, 15.0), (0.5, 99.0, 0.5)])
def test_2_meeting_every_minimum_is_meets_under_any_weights(weights):
    p = policy(weights=dict(zip("PGR", weights)))
    assert check_policy(p)[0] == []
    r = evaluate(profile(publications=[A(3, "coauthor")] * 2), p)
    assert (r["total"], r["class"]) == (70.0, MEETS)
    assert round(r["P"] + r["G"] + r["R"], 1) == r["total"]


def test_2_meeting_every_minimum_is_meets_across_half_point_weight_splits():
    fac = profile(publications=[A(3, "coauthor")] * 2)
    for p_weight in range(0, 201, 7):
        for g_weight in range(0, 201 - p_weight, 5):
            weights = {"P": p_weight / 2, "G": g_weight / 2, "R": (200 - p_weight - g_weight) / 2}
            r = evaluate(fac, policy(weights=weights))
            assert (r["total"], r["class"]) == (70.0, MEETS), weights


def test_2_displayed_parts_add_up_and_stay_within_a_tenth_of_the_true_score():
    rng = random.Random(7)
    for _ in range(600):
        fac = _random_profile(rng)
        r = evaluate(fac, PROVISIONAL)
        if not r["scored"]:
            continue
        assert round(r["P"] + r["G"] + r["R"], 1) == r["total"]
        for d in r["domains"].values():
            assert abs(d["score"] - (d["anchor"] + d["excellence"])) <= 0.1 + 1e-9


# 3 ---------------------------------------------------------------------------------------------
def test_3_phase1_preset_ignores_a_prior_year_mark_on_publications_as_phase1_did():
    fac = profile(publications=[A(1), A(1, counted_in_prior_year=True)])
    old, new = ORIGINAL.evaluate(copy.deepcopy(fac)), evaluate(fac, LEGACY)
    assert {k: new[k] for k in COMPARED} == {k: old[k] for k in COMPARED}
    assert new["pub_count"] == 2 and evaluate(fac, PROVISIONAL)["pub_count"] == 1


def test_3_phase1_preset_matches_phase1_on_profiles_with_dois_ids_and_prior_year_marks():
    rng = random.Random(31)
    for _ in range(1200):
        fac = _random_profile(rng)
        for pub in fac["publications"]:
            if rng.random() < 0.4:
                pub["doi"] = rng.choice(["10.1/a", "10.1/A ", "https://doi.org/10.1/a", "10.1/b"])
            if rng.random() < 0.2:
                pub["counted_in_prior_year"] = True
            if rng.random() < 0.3:
                pub["title"] = rng.choice(["A study", " ", "Trial <1>"])
        for grant in fac["submissions"] + fac["awards"]:
            if rng.random() < 0.5:
                grant["id"] = rng.choice(["G1", "g1", "G1 ", 0, 1, "1"])
        old, new = ORIGINAL.evaluate(copy.deepcopy(fac)), evaluate(fac, LEGACY)
        assert {k: new[k] for k in COMPARED} == {k: old[k] for k in COMPARED}, fac


# 4 ---------------------------------------------------------------------------------------------
MALFORMED = [
    "not a record", None, [],
    {"publications": None}, {"publications": [1]}, {"publications": "x"},
    {"publications": [A(1, doi=123)]}, {"publications": [A(1, title=5)]},
    {"publications": [{"type": ["article"]}]}, {"publications": [A([1])]}, {"publications": [A(1, ["lead"])]},
    {"submissions": [{"size": "major", "role": "PI", "id": [1]}]}, {"submissions": [{"size": ["major"]}]},
    {"awards": [{"size": "major", "role": "PI", "amount": float("nan")}]}, {"awards": [None]},
    {"active_projects": [3]}, {"active_projects": [{"role": ["PI"]}]},
    {"rolling": None}, {"rolling": []}, {"grant_reviews": [["x"]]}, {"grant_reviews": "federal_panel"},
    {"editorial": [{"role": ["x"]}]}, {"editorial": [{}]},
    {"presentations": [{"type": ["oral"]}]}, {"presentations": [{"type": "oral", "venue": ["A"]}]},
    {"research_effort": float("nan")}, {"months_active": float("inf")}, {"research_effort": "40"},
]


@pytest.mark.parametrize("fac", MALFORMED, ids=[repr(m)[:48] for m in MALFORMED])
def test_4_malformed_input_is_incomplete_never_a_crash(fac):
    for p in (PROVISIONAL, LEGACY):
        r = evaluate(fac, p)
        assert r["class"] == INCOMPLETE and r["errors"] and not r["scored"]


def test_4_an_entry_with_an_empty_role_is_scored_and_flagged():
    r = evaluate(profile(publications=[{"type": "article", "tier": 1, "role": None}, A(3)]), PROVISIONAL)
    assert r["scored"] and r["pub_count"] == 2 and len(pending(r)) == 1


def test_4_randomly_corrupted_records_never_raise():
    rng = random.Random(404)
    junk = [None, "x", "", [], {}, 1.5, -3, True, float("nan"), ["a"], {"a": 1}, 10 ** 12]

    def corrupt(node):
        if isinstance(node, dict) and node:
            key = rng.choice(list(node))
            if rng.random() < 0.5 or not isinstance(node[key], (dict, list)):
                node[key] = rng.choice(junk)
            else:
                corrupt(node[key])
        elif isinstance(node, list) and node:
            i = rng.randrange(len(node))
            if rng.random() < 0.4:
                node[i] = rng.choice(junk)
            else:
                corrupt(node[i])

    for _ in range(3000):
        fac = _random_profile(rng)
        for _ in range(rng.randint(1, 3)):
            corrupt(fac)
        for p in (PROVISIONAL, LEGACY):
            evaluate(fac, p)


# 5 ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("first", [A(0, doi="10.1/x"), A(1, doi="10.1/x", peer_reviewed=False),
                                   A(3, "coauthor", doi="10.1/x"), {"type": "mystery", "doi": "10.1/x"}])
def test_5_duplicate_doi_keeps_the_copy_with_the_most_credit_in_any_order(first):
    best, other = A(1, doi="10.1/x"), A(3)
    one = evaluate(profile(publications=[first, best, other]), PROVISIONAL)
    two = evaluate(profile(publications=[best, first, other]), PROVISIONAL)
    alone = evaluate(profile(publications=[best, other]), PROVISIONAL)
    assert one["P"] == two["P"] == alone["P"] and one["pub_count"] == two["pub_count"] == 2


def test_5_doi_written_as_a_web_address_is_the_same_doi():
    fac = profile(publications=[A(1, doi="https://doi.org/10.1/X"), A(1, doi="10.1/x"), A(1, doi="doi:10.1/x ")])
    assert evaluate(fac, PROVISIONAL)["pub_count"] == 1
    assert evaluate(fac, LEGACY)["pub_count"] == 3


# 6 ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("value, shown", [(0.7 * 42.5, 29.8), (46.849999999999994, 46.9), (0.25, 0.3),
                                          (0.35, 0.4), (2.675, 2.7), (38.75, 38.8), (69.95, 70.0),
                                          (10.04, 10.0), (0.0, 0.0)])
def test_6_half_up_rounding_is_exact(value, shown):
    assert _round1(value, PROVISIONAL) == shown


def test_6_phase1_preset_keeps_python_rounding():
    assert _round1(0.25, LEGACY) == 0.2 and _round1(0.35, LEGACY) == 0.3


def test_6_a_score_ending_in_5_rounds_up_inside_the_engine():
    fac = {"research_effort": 60, "months_active": 5, "first_year": True,
           "publications": [A(1, "second"), A(3, "coauthor")], "editorial": [{"role": "editor"}]}
    raw = evaluate(fac, policy(total_from_rounded_parts=False))
    assert raw["domains"]["P"]["anchor"] + raw["domains"]["P"]["excellence"] == pytest.approx(46.85)
    assert raw["P"] == 46.9
    assert evaluate(fac, policy(total_from_rounded_parts=False, rounding="bankers"))["P"] == 46.8


# 7 ---------------------------------------------------------------------------------------------
def drop(table, key):
    return {table: {k: v for k, v in PROVISIONAL[table].items() if k != key}}


BAD_POLICIES = {
    "weights without R": {"weights": {"P": 60, "G": 40}},
    "no credit value for non-peer-reviewed articles": drop("other_output_units", "non_peer_reviewed_article"),
    "size band in one table only": {"submission_base": dict(PROVISIONAL["submission_base"], huge=2.0)},
    "text in a number table": {"author_role_mult": {"lead": "1", "coauthor": 0.7}},
    "blank weight": {"weights": {"P": float("nan"), "G": 35, "R": 15}},
    "text weight": {"weights": {"P": "50", "G": 35, "R": 15}},
    "text publication minimum": {"pub_min_count": "2"},
    "yes/no publication minimum": {"pub_min_count": True},
    "fractional publication minimum": {"pub_min_count": 2.5},
    "blank cap": {"submission_cap": None},
    "saturation without G": drop("saturation", "G"),
    "benchmark without P": drop("benchmark_units", "P"),
    "amount bands without large": drop("amount_bands", "large_min"),
    "missing-data defaults without venue": drop("missing_defaults", "venue"),
    "grant roles without PI": drop("grant_role_mult", "PI"),
    "credit for a questionable journal": {"journal_tier_mult": {1: 1.5, 2: 1.25, 3: 1.0, 0: 0.5}},
    "credit for a questionable venue": {"venue_tier_mult": {"A": 1.25, "B": 1.0, "C": 0.6, "0": 0.2}},
    "negative weight": {"weights": {"P": 120, "G": -35, "R": 15}},
    "anchor share of 0": {"anchor_share": 0}, "anchor share of 1": {"anchor_share": 1},
    "zero saturation": {"saturation": {"P": 0, "G": 4, "R": 4}},
    "zero standard effort": {"standard_research_effort": 0},
    "text yes/no setting": {"enforce_meets_threshold": "false"},
    "unknown exceeds rule": {"exceeds_rule": "always"},
    "role list of numbers": {"award_gate_roles": [1, 2]},
}


@pytest.mark.parametrize("change", BAD_POLICIES.values(), ids=BAD_POLICIES.keys())
def test_7_policies_the_engine_cannot_run_are_rejected_without_raising(change):
    p = copy.deepcopy(PROVISIONAL)
    p.update(copy.deepcopy(change))
    errors, _ = check_policy(p)
    assert errors


@pytest.mark.parametrize("text", ["{}", "[]", "null", '"policy"', '{"journal_tier_mult": {"top": 1.5}}',
                                  '{"journal_tier_mult": {"1": 1.5, "01": 1.2}}'])
def test_7_unusable_policy_text_is_reported_not_raised(text):
    try:
        errors, _ = check_policy(from_json(text))
    except ValueError as exc:
        errors = [str(exc)]
    assert errors


def test_7_whole_number_settings_entered_with_a_decimal_point_are_accepted_as_whole():
    p = policy(pub_min_count=2.0, rolling_max_domains=1.0)
    assert check_policy(p)[0] == []
    assert normalise(p)["pub_min_count"] == 2 and isinstance(normalise(p)["pub_min_count"], int)
    assert fingerprint(p) == fingerprint(PROVISIONAL)


def test_7_no_qualifying_award_role_is_allowed_with_a_warning():
    errors, warnings = check_policy(policy(award_gate_roles=[]))
    assert errors == [] and any("grant minimum" in w for w in warnings)


def test_7_every_accepted_variant_runs_on_every_scenario():
    rng = random.Random(77)
    numeric = [k for k, v in PROVISIONAL.items() if isinstance(v, float)]
    accepted = 0
    for _ in range(400):
        p = copy.deepcopy(PROVISIONAL)
        for key in rng.sample(numeric, 3):
            p[key] = rng.choice([0, 0.5, 1, 2.5, 60, 100, -1])
        table = rng.choice(["weights", "saturation", "journal_tier_mult", "grant_role_mult", "venue_tier_mult"])
        sub = rng.choice(list(p[table]))
        p[table][sub] = rng.choice([0, 0.5, 1, 33.3, 50])
        if check_policy(p)[0]:
            continue
        accepted += 1
        for fac in SCENARIOS:
            assert evaluate(fac, p)["scored"]
    assert accepted > 20


# 8 ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("fac", [
    {"first_year": "no"}, {"first_year": 1},
    {"publications": [A(1, peer_reviewed="no")]}, {"publications": [A(1, counted_in_prior_year="false")]},
    {"publications": [A(1, student_first=1)]},
    {"submissions": [dict(PI_MAJOR, competitive="no")]}, {"submissions": [dict(PI_MAJOR, scored="yes")]},
    {"awards": [dict(PI_MAJOR, counted_in_prior_year=0)]},
])
def test_8_yes_no_fields_accept_only_true_or_false(fac):
    r = evaluate(profile(**fac), PROVISIONAL)
    assert r["class"] == INCOMPLETE and any("yes or no" in e for e in r["errors"])


def test_8_real_true_and_false_are_accepted():
    fac = profile(first_year=False, publications=[A(1, peer_reviewed=True, student_first=False), A(3)],
                  submissions=[dict(PI_MAJOR, competitive=True, scored=False)])
    assert validate(fac, PROVISIONAL) == []


# 9 ---------------------------------------------------------------------------------------------
def test_9_a_policy_read_straight_from_json_scores_like_the_original():
    import json
    raw = json.loads(to_json(PROVISIONAL))
    assert all(isinstance(k, str) for k in raw["journal_tier_mult"])
    assert fingerprint(raw) == fingerprint(PROVISIONAL)
    for fac in SCENARIOS:
        a, b = evaluate(fac, raw), evaluate(fac, PROVISIONAL)
        assert (a["total"], a["class"], a["policy"]) == (b["total"], b["class"], b["policy"])


@pytest.mark.parametrize("same", [
    {"policy_name": "Adopted by the committee"},
    {"award_gate_roles": ["Co-I", "PI", "MPI", "Co-PI", "PI"]},
    {"pres_gate_roles": ["mentor", "presenter"]},
    {"amount_bands": {"minor_max": 10000.0, "large_min": 250000.0}},
    {"note_to_self": "an unused extra setting"},
])
def test_9_policies_that_score_identically_share_a_fingerprint(same):
    p = dict(copy.deepcopy(PROVISIONAL), **same)
    assert fingerprint(p) == fingerprint(PROVISIONAL)
    if "policy_name" not in same:
        assert diff(PROVISIONAL, p) == []


def _leaves(p):
    for key, value in p.items():
        if key == "policy_name":
            continue
        if isinstance(value, dict):
            yield from ((key, sub) for sub in value)
        else:
            yield (key,)


@pytest.mark.parametrize("path", list(_leaves(PROVISIONAL)), ids=lambda p: ".".join(map(str, p)))
def test_9_every_setting_changes_the_fingerprint_and_shows_in_the_diff(path):
    p = copy.deepcopy(PROVISIONAL)
    node = p if len(path) == 1 else p[path[0]]
    old = node[path[-1]]
    if isinstance(old, bool):
        node[path[-1]] = not old
    elif isinstance(old, (int, float)):
        node[path[-1]] = old + 1
    elif isinstance(old, list):
        node[path[-1]] = old[:-1]
    elif old is None:
        node[path[-1]] = 1.0
    else:
        node[path[-1]] = old + "x"
    assert fingerprint(p) != fingerprint(PROVISIONAL)
    assert [d[0] for d in diff(PROVISIONAL, p)] == [".".join(map(str, path))]


def test_9_true_and_1_are_different_settings():
    assert diff(PROVISIONAL, policy(dedupe_doi=1)) == [("dedupe_doi", True, 1)]
    assert fingerprint(policy(dedupe_doi=1)) != fingerprint(PROVISIONAL)
    assert check_policy(policy(dedupe_doi=1))[0]


def test_9_duplicate_journal_tiers_are_refused():
    with pytest.raises(ValueError):
        normalise(policy(journal_tier_mult={"1": 1.2}))


# 10 --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("fac, expected", [
    ({"publications": [{"type": "book"}, A(3), A(3)]}, 1),
    ({"publications": [{"type": "article", "tier": 2}, A(3)]}, 1),
    ({"publications": [{"type": "article", "role": "lead"}, {"type": "article", "role": "lead"}]}, 2),
    ({"active_projects": [{}]}, 1),
    ({"awards": [{"size": "major"}], "presentations": [{"type": "oral"}]}, 3),
])
def test_10_every_unverified_entry_is_flagged_by_name(fac, expected):
    r = evaluate(profile(**fac), PROVISIONAL)
    assert len(pending(r)) == expected
    assert all(f.split(":")[0].split(" (")[0].rsplit(" ", 1)[1].isdigit() for f in pending(r))


def test_10_an_active_project_without_a_role_appears_in_the_breakdown():
    r = evaluate(profile(submissions=[], active_projects=[{"title": "Cohort"}, {"role": "consultant"}]), PROVISIONAL)
    lines = [l for l in r["breakdown"] if l["item"].startswith("Active project")]
    assert len(lines) == 2 and all(l["units"] == 0 for l in lines) and r["gates"]["G"] is False


# 11 --------------------------------------------------------------------------------------------
def test_11_text_report_prints_the_maxima_the_result_was_scored_with():
    p = policy(weights={"P": 40.0, "G": 40.0, "R": 20.0})
    text = report(evaluate(SCENARIOS[0], p), PROVISIONAL)
    assert "| Publications | 28.0/40 |" in text and "| Presentations | 14.0/20 |" in text


def test_11_distinguished_level_is_a_setting():
    fac = profile(publications=[A(1)] * 3, presentations=[], submissions=[])
    assert not any("distinguished" in f for f in evaluate(fac, PROVISIONAL)["flags"])
    assert any("distinguished" in f for f in evaluate(fac, policy(distinguished_level=0.5))["flags"])


@pytest.mark.parametrize("ids", [("G1", "g1 "), (1, "1"), (0, 0), ("x", " X")])
def test_11_grant_ids_match_ignoring_case_spaces_and_number_type(ids):
    once = evaluate(profile(submissions=[dict(PI_MAJOR, id=ids[0])]), PROVISIONAL)
    twice = evaluate(profile(submissions=[dict(PI_MAJOR, id=ids[0]), dict(PI_MAJOR, id=ids[1])]), PROVISIONAL)
    funded = evaluate(profile(submissions=[dict(PI_MAJOR, id=ids[0])], awards=[dict(PI_MAJOR, id=ids[1])]),
                      PROVISIONAL)
    award_only = evaluate(profile(submissions=[], awards=[dict(PI_MAJOR, id=ids[1])]), PROVISIONAL)
    assert twice["G"] == once["G"] and funded["G"] == award_only["G"]


# ---------------------------------------------------------------- boundaries the review found untested
def test_approaching_starts_exactly_at_its_threshold_and_needs_exactly_one_unmet_minimum():
    one_unmet = profile(publications=[A(1)] * 2, presentations=[])
    total = evaluate(one_unmet, PROVISIONAL)["total"]
    assert evaluate(one_unmet, policy(approaching_threshold=total))["approaching"] is True
    assert evaluate(one_unmet, policy(approaching_threshold=round(total + 0.1, 1)))["approaching"] is False
    two_unmet = profile(publications=[A(1)] * 6, presentations=[], submissions=[])
    assert evaluate(two_unmet, policy(approaching_threshold=0.0))["approaching"] is False
    met = evaluate(profile(), policy(approaching_threshold=0.0))
    assert met["approaching"] is False


def test_exceeds_boundaries_are_inclusive():
    fac = SCENARIOS[18]
    strong = profile(publications=[A(1)] * 4, submissions=[PI_MAJOR], awards=[dict(PI_MAJOR)],
                     presentations=MIN_R)
    r = evaluate(strong, PROVISIONAL)
    shares = sorted((d["share"] for d in r["domains"].values()), reverse=True)
    assert r["total"] >= 85 and shares[1] >= 0.8 > shares[2]
    assert evaluate(strong, policy(breadth_level=shares[1]))["class"] == EXCEEDS
    assert evaluate(strong, policy(breadth_level=min(1.0, shares[1] + 0.001)))["class"] == MEETS
    assert evaluate(strong, policy(exceeds_threshold=r["total"]))["class"] == EXCEEDS
    assert evaluate(strong, policy(exceeds_threshold=round(r["total"] + 0.1, 1)))["class"] == MEETS
    assert evaluate(fac, PROVISIONAL)["class"] == EXCEEDS


def test_exceeds_needs_two_strong_domains_not_three():
    fac = profile(publications=[A(1)] * 4, submissions=[PI_MAJOR], awards=[dict(PI_MAJOR)], presentations=MIN_R)
    r = evaluate(fac, PROVISIONAL)
    assert sum(d["share"] >= 0.8 for d in r["domains"].values()) == 2 and r["class"] == EXCEEDS


def test_large_award_floor_is_inclusive():
    fac = profile(publications=[A(2), A(2), A(3, "coauthor")], awards=[{"size": "large", "role": "PI"}],
                  presentations=[{"type": "oral", "venue": "A", "role": "presenter"}] * 2)
    total = evaluate(fac, PROVISIONAL)["total"]
    assert total < 85
    assert evaluate(fac, policy(distinction_min_total=total))["class"] == EXCEEDS
    assert evaluate(fac, policy(distinction_min_total=round(total + 0.1, 1)))["class"] == MEETS


def test_rolling_window_grant_rescue_needs_its_conditions_and_uses_the_one_slot():
    base = {"publications": [A(3), A(3)], "presentations": MIN_R, "proposals_in_development": 1,
            "rolling": {"grant_active_years_prior2": 2}}
    assert evaluate(base, PROVISIONAL)["gates"]["G"] is True
    assert evaluate(dict(base, proposals_in_development=0, unfunded_projects=1), PROVISIONAL)["gates"]["G"] is False
    assert evaluate(dict(base, rolling={"grant_active_years_prior2": 1}), PROVISIONAL)["gates"]["G"] is False
    both = {"proposals_in_development": 1, "abstracts_submitted": 1, "publications": [A(3), A(3)],
            "rolling": {"grant_active_years_prior2": 2, "pres_prior2": 2}}
    assert evaluate(both, PROVISIONAL)["gates"] == {"P": True, "G": True, "R": False}
    assert evaluate(both, policy(rolling_max_domains=2))["gates"] == {"P": True, "G": True, "R": True}
    assert evaluate(both, policy(rolling_max_domains=0))["gates"] == {"P": True, "G": False, "R": False}


def test_settings_that_had_no_test():
    internal = profile(submissions=[{"size": "internal", "role": "PI"}])
    assert evaluate(internal, PROVISIONAL)["gates"]["G"] is True
    assert evaluate(internal, policy(grant_gate_requires_external=True))["gates"]["G"] is False

    three = profile(publications=[A(1)] * 3)
    share = evaluate(three, PROVISIONAL)["domains"]["P"]["share"]
    assert 0.85 < share < 1
    assert evaluate(three, policy(domain_exceeds_level=share))["domains"]["P"]["status"] == "Exceeds"
    assert evaluate(three, policy(domain_exceeds_level=share + 0.001))["domains"]["P"]["status"] == "Meets"

    assert evaluate({"publications": [{"type": "book", "role": "coauthor"}]}, PROVISIONAL)["units"]["P"] == 2.1
    assert evaluate({"publications": [{"type": "book", "role": "lead"}]}, PROVISIONAL)["units"]["P"] == 3.0
    assert evaluate({"publications": [{"type": "book", "role": "coauthor"}]},
                    policy(book_coauthor_mult=0.5))["units"]["P"] == 1.5

    oral = {"presentations": [{"type": "oral", "role": "presenter"}]}
    assert evaluate(oral, PROVISIONAL)["units"]["R"] == 0.6 and evaluate(oral, LEGACY)["units"]["R"] == 1.0
    assert evaluate({"publications": [{"type": "book"}]}, PROVISIONAL)["units"]["P"] == 2.1
    assert evaluate({"publications": [{"type": "book"}]}, LEGACY)["units"]["P"] == 3.0

    loose = {"publications": [{"type": "book", "peer_reviewed": False}, {"type": "chapter", "peer_reviewed": False}]}
    assert evaluate(loose, PROVISIONAL)["units"]["P"] == 1.4 and evaluate(loose, LEGACY)["units"]["P"] == 0.0


@pytest.mark.parametrize("fac, fragment", [
    ({"publications": [A(1, "senior")]}, "author role"),
    ({"publications": [{"type": "book", "role": "editor"}]}, "author role"),
    ({"submissions": [{"size": "major", "role": "Lead"}]}, "role"),
    ({"awards": [{"size": "major", "role": "pi"}]}, "role"),
    ({"active_projects": [{"role": "Investigator"}]}, "role"),
    ({"publications": [A(1, documented_impacts=-1)]}, "documented impacts"),
    ({"publications": [A(1, documented_impacts=1.5)]}, "documented impacts"),
    ({"publications": [A(True)]}, "journal tier"),
    ({"awards": [{"size": "major", "role": "PI", "amount": 300_000}]}, "inconsistent"),
    ({"awards": [{"size": "large", "role": "PI", "amount": 249_999}]}, "inconsistent"),
    ({"awards": [{"size": "minor", "role": "PI", "amount": 10_000}]}, "inconsistent"),
    ({"sessions_chaired": True}, "whole number"),
])
def test_validation_checks_that_had_no_test(fac, fragment):
    errors = validate(fac, PROVISIONAL)
    assert len(errors) == 1 and fragment in errors[0]


def test_amounts_on_a_band_boundary_are_consistent():
    fac = {"awards": [{"size": "major", "role": "PI", "amount": 10_000},
                      {"size": "large", "role": "PI", "amount": 250_000},
                      {"size": "minor", "role": "PI", "amount": 9_999.99},
                      {"size": "internal", "role": "PI", "amount": 5_000_000}]}
    assert validate(fac, PROVISIONAL) == []
