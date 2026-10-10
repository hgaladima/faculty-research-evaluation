"""Form mapping and a smoke test of the Streamlit app."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import exports
import forms
from engine import LEGACY, PROVISIONAL, evaluate
from engine.scenarios import SCENARIOS

APP = str(Path(__file__).resolve().parents[1] / "app.py")
COMPARED = ("P", "G", "R", "total", "class", "gates", "pub_count", "units")


def through_the_forms(fac, policy):
    f = forms.rows_from_faculty(fac)
    built, problems = forms.build_faculty(f["info"], f["pubs"], f["grants"], f["pres"], f["editorial"],
                                          f["reviews"], policy)
    assert problems == []
    return built


@pytest.mark.parametrize("policy", [PROVISIONAL, LEGACY], ids=["provisional", "phase1"])
@pytest.mark.parametrize("i", range(22))
def test_scenario_entered_through_the_forms_scores_the_same(i, policy):
    direct = evaluate(SCENARIOS[i], policy)
    via_forms = evaluate(through_the_forms(SCENARIOS[i], policy), policy)
    assert {k: via_forms[k] for k in COMPARED} == {k: direct[k] for k in COMPARED}


def test_incomplete_rows_are_reported_not_scored():
    _, problems = forms.build_faculty({}, [{"Title": "A paper", "Type": "Journal article"}],
                                      [{"Title": "R01", "Status": forms.SUBMITTED, "Role": "PI"}],
                                      [{"Title": "Talk", "Type": "Poster"}], [], [], PROVISIONAL)
    assert len(problems) == 3


def test_proposal_funded_in_the_same_year_is_one_award():
    row = {"Title": "R21", "Source": "External", "Total amount ($)": 275000.0, "Role": "PI", "Competitive": True,
           "Status": forms.AWARDED, "Also submitted this year": True}
    fac, problems = forms.build_faculty({}, [], [row], [], [], [], PROVISIONAL)
    assert problems == [] and fac["awards"][0]["size"] == "large"
    assert fac["submissions"][0]["id"] == fac["awards"][0]["id"]
    assert evaluate(fac, PROVISIONAL)["units"]["G"] == 3.0


def test_reports_are_generated():
    fac = SCENARIOS[18]
    result = evaluate(fac, PROVISIONAL)
    meta = {"version": 1, "locked": False, "approved_by": ""}
    info = {"name": "Dr. A & B <test>", "evaluation_year": "2026"}
    context = {"Evaluator notes": "Strong year & <broad> portfolio"}
    assert exports.pdf_bytes(info, result, meta, context)[:4] == b"%PDF"
    assert exports.excel_bytes(info, result, PROVISIONAL, meta, context)[:2] == b"PK"


def test_app_runs_and_scores_an_example(tmp_path, monkeypatch):
    import storage
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "POLICY_FILE", tmp_path / "policy.json")
    monkeypatch.setattr(storage, "LOG_FILE", tmp_path / "policy_log.jsonl")
    monkeypatch.setattr(storage, "EVAL_DIR", tmp_path / "evaluations")
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception, at.exception
    at.sidebar.selectbox[1].select("S19 Exceptional across all domains").run()
    at.sidebar.button[2].click().run()
    assert not at.exception, at.exception
    shown = " ".join(h.proto.body for h in at.get("html"))
    assert "Exceeds Expectations" in shown and 'data-score="100"' in shown
