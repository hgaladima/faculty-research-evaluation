"""Engine tests. Run from faculty_research_webapp/:  python -m pytest"""
import copy
import importlib.machinery
import importlib.util
import random
from pathlib import Path

import pytest

from engine import LEGACY, PROVISIONAL, check_policy, evaluate, fingerprint, validate
from engine.policy import from_json, to_json
from engine.research_eval import DOES_NOT_MEET, EXCEEDS, INCOMPLETE, MEETS, NOT_EVALUATED
from engine.scenarios import SCENARIOS, A
from engine.sensitivity import compare

ROOT = Path(__file__).resolve().parents[2]
COMPARED = ("P", "G", "R", "total", "class", "gates", "factor", "pub_benchmark", "pub_count", "units")


def _load_original(name):
    path = str(ROOT / f"{name}.py.txt")
    loader = importlib.machinery.SourceFileLoader(f"phase1_{name}", path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


ORIGINAL = _load_original("research_eval")
ORIGINAL_SCENARIOS = _load_original("scenarios").SCENARIOS

MIN_G = [{"size": "major", "role": "Co-I"}]
MIN_R = [{"type": "poster", "venue": "B", "role": "presenter"}]


def profile(**kw):
    base = {"publications": [A(3), A(3)], "submissions": MIN_G, "presentations": MIN_R}
    base.update(kw)
    return base


# ---------------------------------------------------------------- Phase 1 reproduction
@pytest.mark.parametrize("i", range(22))
def test_legacy_policy_reproduces_phase1_scenario(i):
    old = ORIGINAL.evaluate(ORIGINAL_SCENARIOS[i])
    new = evaluate(SCENARIOS[i], LEGACY)
    assert {k: new[k] for k in COMPARED} == {k: old[k] for k in COMPARED}


def test_phase1_baseline_counts():
    out = compare(LEGACY, LEGACY)
    assert out["before"] == {EXCEEDS: 5, MEETS: 13, DOES_NOT_MEET: 4}


def _random_profile(rng):
    def article():
        d = {"type": "article", "tier": rng.choice([0, 1, 2, 3, 3, None]), "role": rng.choice(["lead", "coauthor"])}
        if rng.random() < 0.2:
            d["student_first"] = True
        if rng.random() < 0.15:
            d["documented_impacts"] = rng.randint(1, 3)
        if rng.random() < 0.1:
            d["peer_reviewed"] = False
        return d

    def other_pub():
        return {"type": rng.choice(["book", "chapter", "policy_brief", "technical_report", "software",
                                    "dataset", "book_review", "edited_book", "published_abstract"]),
                "peer_reviewed": rng.random() < 0.85}

    def grant():
        d = {"size": rng.choice(["internal", "minor", "major", "large"]),
             "role": rng.choice(["PI", "MPI", "Co-PI", "Co-I", "collaborator", "consultant"])}
        if rng.random() < 0.25:
            d["competitive"] = False
        if rng.random() < 0.25:
            d["scored"] = True
        if rng.random() < 0.3:
            d["id"] = rng.choice(["G1", "G2", "G3"])
        return d

    def pres():
        d = {"type": rng.choice(["keynote", "plenary", "invited", "oral", "panel", "workshop", "poster",
                                 "institutional", "outreach", "seminar"]),
             "venue": rng.choice(["A", "B", "C", "0"])}
        if rng.random() < 0.6:
            d["role"] = rng.choice(["presenter", "mentor", "coauthor"])
        return d

    fac = {"name": "random",
           "publications": [article() for _ in range(rng.randint(0, 6))] + [other_pub() for _ in range(rng.randint(0, 3))],
           "submissions": [grant() for _ in range(rng.randint(0, 4))],
           "awards": [dict(grant(), counted_in_prior_year=rng.random() < 0.15) for _ in range(rng.randint(0, 2))],
           "presentations": [pres() for _ in range(rng.randint(0, 5))],
           "active_projects": [{"role": rng.choice(["PI", "Co-I", "consultant"])} for _ in range(rng.randint(0, 3))],
           "grant_reviews": [rng.choice(["federal_panel", "other_panel"]) for _ in range(rng.randint(0, 2))],
           "editorial": [{"role": rng.choice(["editor", "editorial_board", "manuscript_review"]), "n": rng.randint(1, 8)}
                         for _ in range(rng.randint(0, 2))],
           "sessions_chaired": rng.randint(0, 3), "proposals_in_development": rng.randint(0, 3),
           "unfunded_projects": rng.randint(0, 2), "manuscripts_under_review": rng.randint(0, 2),
           "abstracts_submitted": rng.randint(0, 2),
           "research_effort": rng.choice([0, 10, 19, 20, 30, 40, 40, 40, 60, 80]),
           "months_active": rng.choice([0, 5, 6, 9, 12, 12, 12]),
           "first_year": rng.random() < 0.15}
    for a in fac["awards"]:
        a.pop("scored", None)
    if rng.random() < 0.4:
        fac["rolling"] = {"pubs_prior2": rng.randint(0, 8), "grant_active_years_prior2": rng.randint(0, 2),
                          "pres_prior2": rng.randint(0, 4)}
    return fac


def test_legacy_policy_matches_phase1_engine_on_random_profiles():
    rng = random.Random(20261010)
    for _ in range(1500):
        fac = _random_profile(rng)
        old = ORIGINAL.evaluate(copy.deepcopy(fac))
        new = evaluate(fac, LEGACY)
        assert {k: new[k] for k in COMPARED} == {k: old[k] for k in COMPARED}, fac


# ---------------------------------------------------------------- policies
def test_shipped_policies_are_valid():
    assert check_policy(PROVISIONAL)[0] == []
    assert check_policy(LEGACY)[0] == []


def test_policy_survives_json_round_trip():
    restored = from_json(to_json(PROVISIONAL))
    assert restored == PROVISIONAL
    assert fingerprint(restored) == fingerprint(PROVISIONAL)
    assert fingerprint(PROVISIONAL) != fingerprint(LEGACY)


def test_policy_check_rejects_bad_weights_and_thresholds():
    bad = copy.deepcopy(PROVISIONAL)
    bad["weights"] = {"P": 60, "G": 35, "R": 15}
    bad["exceeds_threshold"] = 60
    errors, _ = check_policy(bad)
    assert any("sum to 100" in e for e in errors)
    assert any("Exceeds threshold" in e for e in errors)


def test_policy_check_warns_when_minimums_fall_below_meets_threshold():
    p = copy.deepcopy(PROVISIONAL)
    p["anchor_share"] = 0.6
    errors, warnings = check_policy(p)
    assert errors == [] and any("below the Meets threshold" in w for w in warnings)
    assert evaluate(profile(), p)["class"] == DOES_NOT_MEET


# ---------------------------------------------------------------- provisional rules (REVIEW_FINDINGS ids)
def test_meeting_every_minimum_is_exactly_meets():
    r = evaluate(profile(publications=[A(3, "coauthor")] * 2), PROVISIONAL)
    assert (r["total"], r["class"]) == (70.0, MEETS)


def test_2_3_presentation_minimum_requires_presenting():
    fac = profile(presentations=[{"type": "poster", "venue": "B", "role": "coauthor"}])
    assert evaluate(fac, LEGACY)["gates"]["R"] is True
    r = evaluate(fac, PROVISIONAL)
    assert r["gates"]["R"] is False and r["class"] == DOES_NOT_MEET
    assert r["domains"]["R"]["status"] == "Approaching"
    mentor = profile(presentations=[{"type": "poster", "venue": "B", "role": "mentor"}])
    assert evaluate(mentor, PROVISIONAL)["gates"]["R"] is True


def test_2_4_consultant_on_award_does_not_meet_grant_minimum():
    fac = profile(submissions=[], awards=[{"size": "minor", "role": "consultant", "competitive": False}])
    assert evaluate(fac, LEGACY)["gates"]["G"] is True
    assert evaluate(fac, PROVISIONAL)["gates"]["G"] is False


def test_2_5_publication_volume_alone_is_not_exceeds():
    fac = profile(publications=[A(3)] * 6)
    assert evaluate(fac, LEGACY)["class"] == EXCEEDS
    r = evaluate(fac, PROVISIONAL)
    assert r["total"] == 85.0 and r["class"] == MEETS


def test_2_6_large_award_route_needs_floor_score():
    weak = profile(publications=[A(3, "coauthor")] * 2, submissions=[], awards=[{"size": "large", "role": "PI"}])
    assert evaluate(weak, LEGACY)["class"] == EXCEEDS
    assert evaluate(weak, PROVISIONAL)["class"] == MEETS
    strong = profile(publications=[A(2), A(2), A(3, "coauthor")], awards=[{"size": "large", "role": "PI"}],
                     presentations=[{"type": "oral", "venue": "A", "role": "presenter"}] * 2)
    assert evaluate(strong, PROVISIONAL)["class"] == EXCEEDS


def test_2_7_one_unmet_minimum_with_a_strong_score_is_flagged_approaching():
    fac = profile(publications=[A(1)] * 3 + [A(2)] * 3, presentations=[],
                  awards=[{"size": "large", "role": "Co-PI"}])
    r = evaluate(fac, PROVISIONAL)
    assert r["class"] == DOES_NOT_MEET and r["approaching"] is True


@pytest.mark.parametrize("effort", [19, 20])
def test_3_1_reduced_assignment_needs_documented_activity_not_a_waiver(effort):
    nothing = {"research_effort": effort, "publications": [A(3, "coauthor")]}
    r = evaluate(nothing, PROVISIONAL)
    assert r["gates"] == {"P": True, "G": False, "R": False} and r["class"] == DOES_NOT_MEET
    documented = dict(nothing, proposals_in_development=1, presentations=[{"type": "seminar", "role": "presenter"}])
    r = evaluate(documented, PROVISIONAL)
    assert r["class"] == MEETS
    assert any("Reduced research assignment" in n for n in r["notes"])


def test_3_1_legacy_waiver_is_now_explained_in_the_notes():
    r = evaluate({"research_effort": 19, "publications": [A(3, "coauthor")]}, LEGACY)
    assert r["class"] == MEETS and sum("waived" in n for n in r["notes"]) == 2


@pytest.mark.parametrize("field", ["research_effort", "months_active"])
def test_3_2_no_research_assignment_is_not_evaluated(field):
    r = evaluate(profile(**{field: 0}), PROVISIONAL)
    assert r["class"] == NOT_EVALUATED and r["scored"] is False


def test_3_6_rolling_window_rescues_only_one_domain():
    fac = {"rolling": {"pubs_prior2": 6, "grant_active_years_prior2": 2, "pres_prior2": 2},
           "manuscripts_under_review": 1, "proposals_in_development": 1, "abstracts_submitted": 1}
    assert evaluate(fac, LEGACY)["class"] == MEETS
    r = evaluate(fac, PROVISIONAL)
    assert sum(r["gates"].values()) == 1 and r["class"] == DOES_NOT_MEET


def test_3_6_rolling_window_uses_standard_minimum_for_prior_years():
    fac = profile(months_active=6, publications=[], rolling={"pubs_prior2": 3}, manuscripts_under_review=1)
    assert evaluate(fac, LEGACY)["gates"]["P"] is True
    assert evaluate(fac, PROVISIONAL)["gates"]["P"] is False
    fac["rolling"]["pubs_prior2"] = 5
    assert evaluate(fac, PROVISIONAL)["gates"]["P"] is True


def test_4_1_same_grant_is_not_credited_as_submission_and_award():
    award = {"size": "major", "role": "PI", "id": "G1"}
    alone = evaluate(profile(submissions=[], awards=[award]), PROVISIONAL)
    both = evaluate(profile(submissions=[dict(award)], awards=[award]), PROVISIONAL)
    assert both["total"] == alone["total"]
    assert evaluate(profile(submissions=[dict(award)], awards=[award]), LEGACY)["G"] > alone["G"]


def test_4_2_duplicate_doi_is_counted_once():
    one = evaluate(profile(publications=[A(1, doi="10.1/x")]), PROVISIONAL)
    two = evaluate(profile(publications=[A(1, doi="10.1/x"), A(1, doi="10.1/X ")]), PROVISIONAL)
    assert two["pub_count"] == 1 and two["P"] == one["P"]
    assert any("duplicate DOI" in f for f in two["flags"])


def test_4_3_publication_credited_in_a_prior_year_is_excluded():
    r = evaluate(profile(publications=[A(1), A(1, counted_in_prior_year=True)]), PROVISIONAL)
    assert r["pub_count"] == 1 and r["gates"]["P"] is False


def test_4_6_chapter_credit_is_capped_and_unknown_types_are_flagged():
    six = evaluate(profile(publications=[{"type": "chapter"}] * 6), PROVISIONAL)
    assert six["units"]["P"] == 2.25
    assert evaluate(profile(publications=[{"type": "chapter"}] * 6), LEGACY)["units"]["P"] == 4.5
    r = evaluate(profile(publications=[A(3), A(3), {"type": "mystery"}]), PROVISIONAL)
    assert any("not credited" in f for f in r["flags"])
    abstract = evaluate(profile(publications=[A(3), A(3), {"type": "published_abstract"}]), PROVISIONAL)
    assert abstract["units"]["P"] == 2.2


def test_4_7_second_author_sits_between_lead_and_coauthor():
    u = {role: evaluate(profile(publications=[A(1, role)] * 2), PROVISIONAL)["units"]["P"]
         for role in ("lead", "second", "coauthor")}
    assert u["lead"] > u["second"] > u["coauthor"]


def test_6_6_displayed_parts_add_up_to_the_total():
    for fac in SCENARIOS:
        r = evaluate(fac, PROVISIONAL)
        assert round(r["P"] + r["G"] + r["R"], 1) == r["total"]


def test_breakdown_units_add_up_to_domain_units():
    for fac in SCENARIOS:
        r = evaluate(fac, PROVISIONAL)
        for d in "PGR":
            listed = sum(line["units"] for line in r["breakdown"] if line["domain"] == d)
            assert listed == pytest.approx(r["domains"][d]["units"])


def test_provisional_classification_of_the_22_scenarios():
    out = compare(LEGACY, PROVISIONAL)
    assert out["after"] == {EXCEEDS: 2, MEETS: 15, DOES_NOT_MEET: 5}
    changed = {r["Profile"].split()[0] for r in out["rows"] if r["Reclassified"]}
    assert changed == {"S2", "S9", "S12", "S14"}


# ---------------------------------------------------------------- validation (section 6)
@pytest.mark.parametrize("fac, fragment", [
    ({"awards": [{"role": "PI", "amount": 5000}]}, "size band"),
    ({"presentations": [{"type": "oral", "venue": 0}]}, "venue tier"),
    ({"publications": [A("2")]}, "journal tier"),
    ({"presentations": [{"type": "oral", "venue": "A", "role": "speaker"}]}, "role"),
    ({"proposals_in_development": -3}, "whole number"),
    ({"sessions_chaired": -2}, "whole number"),
    ({"research_effort": 140}, "Research effort"),
    ({"months_active": 14}, "Months active"),
    ({"awards": [{"size": "minor", "role": "PI", "amount": 400_000}]}, "inconsistent"),
    ({"grant_reviews": ["study_section"]}, "Grant review"),
    ({"editorial": [{"role": "chief"}]}, "Editorial"),
    ({"presentations": [{"type": "lecture"}]}, "presentation type"),
    ({"rolling": {"pubs_prior2": -1}}, "Rolling-window"),
])
def test_invalid_input_is_reported_and_never_scored(fac, fragment):
    for policy in (PROVISIONAL, LEGACY):
        r = evaluate(fac, policy)
        assert r["class"] == INCOMPLETE and r["scored"] is False
        assert any(fragment in e for e in r["errors"]), r["errors"]


def test_valid_scenarios_have_no_validation_errors():
    for fac in SCENARIOS:
        assert validate(fac, PROVISIONAL) == []


def test_missing_role_and_venue_are_flagged_and_treated_conservatively():
    r = evaluate(profile(presentations=[{"type": "oral"}], awards=[{"size": "major"}]), PROVISIONAL)
    assert r["gates"]["R"] is False
    assert sum("pending verification" in f for f in r["flags"]) == 3
