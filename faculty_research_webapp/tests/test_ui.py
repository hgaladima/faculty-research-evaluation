"""The result panel must only say what the engine result supports."""
import copy

import pytest
from streamlit.testing.v1 import AppTest

import storage
import ui
from engine import LEGACY, PROVISIONAL, evaluate
from engine.research_eval import DOES_NOT_MEET, EXCEEDS, MEETS
from engine.scenarios import SCENARIOS, A
from test_app import APP

MIN_G = [{"size": "major", "role": "Co-I"}]
MIN_R = [{"type": "poster", "venue": "B", "role": "presenter"}]


def scenario(tag):
    return next(s for s in SCENARIOS if s["name"].startswith(tag + " "))


def test_reason_for_a_score_below_the_meets_threshold():
    policy = copy.deepcopy(PROVISIONAL)
    policy["anchor_share"] = 0.6
    result = evaluate(scenario("S1"), policy)
    assert (result["class"], result["class_basis"]) == (DOES_NOT_MEET, "below_meets_threshold")
    reason = ui.result_reason(result, policy)
    assert "below the Meets threshold of 70" in reason and "points away" not in reason


def test_approaching_always_carries_a_committee_flag():
    fac = {"publications": [A(3), A(3)], "submissions": [{"size": "major", "role": "PI"}],
           "presentations": [{"type": "seminar", "role": "presenter"}]}
    result = evaluate(fac, PROVISIONAL)
    assert result["class"] == DOES_NOT_MEET and result["approaching"] and result["total"] < 70
    assert any("approaching expectations" in f for f in result["flags"])
    assert "flagged for committee review" in ui.result_reason(result, PROVISIONAL)


def test_reason_for_exceeds_through_the_award_route():
    result = evaluate(scenario("S8"), PROVISIONAL)
    assert (result["class"], result["class_basis"]) == (EXCEEDS, "exceeds_on_award")
    assert result["total"] < PROVISIONAL["exceeds_threshold"]
    assert "the score itself is below the Exceeds threshold" in ui.result_reason(result, PROVISIONAL)


def test_reason_for_a_high_score_without_two_strong_domains():
    result = evaluate(scenario("S14"), PROVISIONAL)
    assert (result["class"], result["class_basis"]) == (MEETS, "meets_lacks_breadth")
    assert "two domains" in ui.result_reason(result, PROVISIONAL)


@pytest.mark.parametrize("policy", [PROVISIONAL, LEGACY], ids=["provisional", "phase1"])
def test_every_scenario_gets_a_reason_consistent_with_its_class(policy):
    for fac in SCENARIOS:
        result = evaluate(fac, policy)
        reason = ui.result_reason(result, policy)
        unmet = any(not d["minimum_met"] for d in result["domains"].values())
        assert reason.startswith("Minimum expectation not met") == unmet
        if result["class"] == EXCEEDS:
            assert "points away" not in reason


def test_scale_does_not_colour_class_zones():
    html = ui.result_instrument(evaluate(scenario("S20"), PROVISIONAL), PROVISIONAL, "S20")
    assert "zone" not in html and 'class="reached"' in html


@pytest.mark.parametrize("meets, exceeds, has_end, low", [
    (70, 85, True, False), (70, 95, False, False), (70, 75, True, True), (5, 85, True, False)])
def test_scale_labels_avoid_collisions(meets, exceeds, has_end, low):
    html = ui.scale_ticks(meets, exceeds)
    assert ('tick end' in html) == has_end
    assert ('exceeds low' in html) == low
    assert ('tick start' in html) == (meets >= 8)


def test_stylesheet_takes_base_colours_from_the_theme():
    css = ui.stylesheet({"theme.primaryColor": "#ABCDEF"}.get)
    assert "--harbor: #ABCDEF" in css and "--ink: #14202B" in css


def test_saved_evaluation_names_and_subjects(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "EVAL_DIR", tmp_path)
    first = {"name": "Smith, J.", "faculty_id": "", "evaluation_year": "2026"}
    second = {"name": "Smith J", "faculty_id": "", "evaluation_year": "2026"}
    assert storage.evaluation_name(first) == storage.evaluation_name(second) == "Smith_J_2026"
    assert storage.saved_subject("Smith_J_2026") is None
    storage.save_evaluation({"form": {"info": first}})
    assert storage.saved_subject("Smith_J_2026") == "Smith, J., 2026"


def _app(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "POLICY_FILE", tmp_path / "policy.json")
    monkeypatch.setattr(storage, "LOG_FILE", tmp_path / "policy_log.jsonl")
    monkeypatch.setattr(storage, "EVAL_DIR", tmp_path / "evaluations")
    return AppTest.from_file(APP, default_timeout=60).run()


def _button(at, label):
    return next(b for b in at.button if b.label == label)


def test_zero_activity_year_can_be_recorded(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch)
    assert any("Nothing to evaluate yet" in h.proto.body for h in at.get("html"))
    at.text_input(key="info_name").set_value("Dr. Quiet Year").run()
    shown = " ".join(h.proto.body for h in at.get("html"))
    assert "Nothing to evaluate yet" not in shown and "Does Not Meet Expectations" in shown
    _button(at, "Save evaluation").click().run()
    assert not at.exception and storage.list_evaluations() == ["Dr_Quiet_Year_2026"]


def test_saving_over_another_evaluation_needs_confirmation(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch)
    at.text_input(key="info_name").set_value("Smith, J.").run()
    _button(at, "Save evaluation").click().run()
    _button(at, "New blank evaluation").click().run()
    at.text_input(key="info_name").set_value("Smith J").run()
    assert any("already exists" in w.value for w in at.warning)
    assert _button(at, "Save evaluation").disabled
    at.checkbox(key="replace_Smith_J_2026").check().run()
    assert not _button(at, "Save evaluation").disabled
