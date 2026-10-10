"""Check the Excel calculator against the scoring engine by entering cases into the workbook in real Excel.

Run from faculty_research_webapp/:  python -m tools.validate_excel [random cases per policy]

Each case is a filled-in entry form (the same tables the web app uses). Python scores it with
forms.build_faculty + engine.evaluate; Excel scores it with the workbook's formulas. The two must agree on the
three domain scores, the overall score, the classification and which minimums are met.
"""
from __future__ import annotations

import copy
import random
import sys
import tempfile
from pathlib import Path

import forms
from engine import LEGACY, PROVISIONAL, evaluate
from engine.research_eval import INCOMPLETE
from engine.scenarios import SCENARIOS
from tools import build_excel_calculator as builder
from tools.excel_com import excel, formula_errors, open_copy

FIRST = builder.FIRST
INPUT_RANGES = {"pubs": ("Publications", forms.PUB_COLUMNS, builder.ROWS["pubs"]),
                "grants": ("Grants", forms.GRANT_COLUMNS, builder.ROWS["grants"]),
                "pres": ("Presentations", forms.PRES_COLUMNS, builder.ROWS["pres"])}
OUTPUTS = ("c_showP", "c_showG", "c_showR", "c_total", "c_class", "c_gP", "c_gG", "c_gR", "c_basis", "c_approaching")
INFO_CELLS = {"name": "f_name", "faculty_id": "f_id", "evaluation_year": "f_year", "research_effort": "f_effort",
              "months_active": "f_months", "sessions_chaired": "o_chaired", "proposals_in_development": "o_pid",
              "unfunded_projects": "o_unfunded", "manuscripts_under_review": "o_manuscripts",
              "abstracts_submitted": "o_abstracts"}
ROLLING_CELLS = {"pubs_prior2": "o_pubs_prior2", "grant_active_years_prior2": "o_grant_prior2",
                 "pres_prior2": "o_pres_prior2"}


def variant_policies() -> dict:
    """Policies that flip every rule switch the workbook implements. All round half up, as Excel does."""
    phase1 = dict(copy.deepcopy(LEGACY), rounding="half_up", policy_name="Phase 1 rules, rounding half up")
    mixed = copy.deepcopy(PROVISIONAL)
    mixed.update(policy_name="Mixed switches", exceeds_rule="breadth", rolling_max_domains=2,
                 rolling_benchmark="current_year", grant_gate_requires_external=True, chapter_cap=None,
                 dedupe_doi=False, normalise_ids=False, evaluate_zero_assignment=True,
                 weights={"P": 42.5, "G": 42.5, "R": 15.0}, exceeds_threshold=80.0, breadth_level=0.75,
                 missing_defaults={"venue": "B", "pres_role": "presenter", "book_role": "lead"},
                 pres_gate_roles=["presenter"], award_gate_roles=["PI", "MPI"], pub_min_count=3,
                 standard_research_effort=50.0, approaching_threshold=55.0)
    strict = copy.deepcopy(PROVISIONAL)
    strict.update(policy_name="Total-only, no dedupe of awards", exceeds_rule="total", dedupe_submission_award=False,
                  honour_prior_year_publications=False, total_from_rounded_parts=False, anchor_share=0.6,
                  reduced_assignment_rule="waive_below_threshold", rolling_max_domains=3,
                  weights={"P": 33.4, "G": 33.3, "R": 33.3}, distinction_min_total=60.0, submission_cap=1.0)
    return {"Provisional": PROVISIONAL, "Phase 1 rules (half-up)": phase1, "Mixed switches": mixed,
            "Total-only": strict}


def scenario_form(fac: dict) -> dict:
    return forms.rows_from_faculty(fac)


def random_form(rng: random.Random) -> dict:
    """A random filled-in form, including incomplete rows, unverified entries, duplicates and prior-year marks."""
    pick = lambda options, blank=0.0: None if rng.random() < blank else rng.choice(list(options))
    flag = lambda p=0.3, blank=0.3: None if rng.random() < blank else rng.random() < p
    pubs = []
    for _ in range(rng.choice([0, 1, 2, 2, 3, 4, 6, 9])):
        pubs.append({"Title": pick(["A study", "Trial", ""], 0.2), "Journal or publisher": pick(["J Public Health", ""], 0.5),
                     "Type": pick(forms.PUB_TYPES, 0.01), "Peer reviewed": flag(0.85),
                     "Journal tier": pick(forms.JOURNAL_TIERS, 0.01), "Authorship": pick(forms.AUTHORSHIP, 0.01),
                     "Student or mentee first author": flag(0.3), "Documented impacts": pick([0, 1, 2, 3], 0.6),
                     "DOI": pick(["10.1/a", "10.1/A ", "https://doi.org/10.1/a", "doi:10.1/b", "10.1/b", "10.9/c"], 0.5),
                     "Quartile (info)": pick(forms.QUARTILES, 0.7), "Impact factor (info)": pick([1.2, 4.5], 0.7),
                     "Credited in a prior year": flag(0.12, 0.5)})
    grants = []
    for _ in range(rng.choice([0, 1, 1, 2, 3, 5])):
        grants.append({"Title": pick(["R01", "Seed grant", ""], 0.2), "Funder": pick(["NIH", "Foundation"], 0.5),
                       "Source": pick(forms.GRANT_SOURCES, 0.3),
                       "Total amount ($)": pick([5_000, 9_999.99, 10_000, 80_000, 249_999, 250_000, 1_200_000], 0.01),
                       "Role": pick(forms.GRANT_ROLES, 0.01), "Competitive": flag(0.8),
                       "Status": pick(forms.GRANT_STATUSES, 0.01), "Also submitted this year": flag(0.35, 0.4),
                       "Scored or discussed": flag(0.3, 0.4), "Credited in a prior year": flag(0.12, 0.5)})
    pres = []
    for _ in range(rng.choice([0, 1, 1, 2, 3, 6])):
        pres.append({"Title": pick(["Talk", ""], 0.3), "Meeting": pick(["APHA", "State meeting"], 0.4),
                     "Location (info)": pick(["Atlanta"], 0.6), "Scope (info)": pick(forms.PRES_SCOPES, 0.6),
                     "Type": pick(forms.PRES_TYPES, 0.01), "Venue tier": pick(forms.VENUE_TIERS, 0.01),
                     "Role": pick(forms.PRES_ROLES, 0.01), "Peer-reviewed abstract (info)": flag(0.5, 0.6)})
    editorial = [{"Role": pick(forms.EDITORIAL_ROLES, 0.1), "Count": pick([1, 2, 8], 0.4)} for _ in range(rng.randint(0, 3))]
    reviews = [{"Panel type": pick(forms.REVIEW_TYPES, 0.1), "Count": pick([1, 2], 0.5)} for _ in range(rng.randint(0, 2))]
    info = {"name": "Random case", "faculty_id": "", "evaluation_year": "2026",
            "research_effort": pick([0, 10, 19, 20, 30, 40, 40, 60, 80], 0.25),
            "months_active": pick([0, 5, 6, 9, 12, 12], 0.2), "first_year": rng.random() < 0.15}
    for key in ("sessions_chaired", "proposals_in_development", "unfunded_projects", "manuscripts_under_review",
                "abstracts_submitted"):
        info[key] = rng.choice([0, 0, 1, 2, 3])
    for key in ROLLING_CELLS:
        info[f"use_{key}"] = rng.random() < 0.4
        info[key] = rng.choice([0, 1, 2, 4, 7])
    info["grant_active_years_prior2"] = min(info["grant_active_years_prior2"], 2)
    return {"info": info, "pubs": pubs, "grants": grants, "pres": pres, "editorial": editorial, "reviews": reviews}


def python_result(form: dict, policy: dict) -> dict:
    fac, problems = forms.build_faculty(form["info"], form["pubs"], form["grants"], form["pres"], form["editorial"],
                                        form["reviews"], policy)
    if problems:
        return {"scored": False, "class": "Incomplete", "problems": problems}
    r = evaluate(fac, policy)
    assert r["class"] != INCOMPLETE, r["errors"]
    return {"scored": r["scored"], "class": r["class"], "P": r["P"], "G": r["G"], "R": r["R"], "total": r["total"],
            "gates": [r["gates"][d] for d in "PGR"], "approaching": r["approaching"]}


def _cell(value):
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return None if forms._blank(value) else value


def enter(book, form: dict) -> None:
    """Type one form into the open workbook (replacing whatever was there)."""
    for key, (sheet, columns, n) in INPUT_RANGES.items():
        rows = [[_cell(row.get(c)) for c in columns] for row in form[key]]
        rows += [[None] * len(columns)] * (n - len(rows))
        target = book.Worksheets(sheet).Range(f"A{FIRST}:{builder.col(len(columns))}{FIRST + n - 1}")
        target.Value = tuple(tuple(row) for row in rows)
    other = book.Worksheets("Other")
    for letters, key, columns, n in (("AB", "editorial", forms.EDITORIAL_COLUMNS, builder.ROWS["editorial"]),
                                     ("EF", "reviews", forms.REVIEW_COLUMNS, builder.ROWS["reviews"])):
        rows = [[_cell(row.get(c)) for c in columns] for row in form[key]] + [[None, None]] * n
        other.Range(f"{letters[0]}{FIRST}:{letters[1]}{FIRST + n - 1}").Value = tuple(tuple(r) for r in rows[:n])
    info = form["info"]
    for key, name in INFO_CELLS.items():
        book.Names(name).RefersToRange.Value = _cell(info.get(key))
    book.Names("f_first_year").RefersToRange.Value = "Yes" if info.get("first_year") else None
    for key, name in ROLLING_CELLS.items():
        book.Names(name).RefersToRange.Value = info.get(key, 0) if info.get(f"use_{key}") else None


def excel_result(book) -> dict:
    v = {name: book.Names(name).RefersToRange.Value for name in OUTPUTS}
    if v["c_basis"] == "incomplete":
        return {"scored": False, "class": "Incomplete"}
    if v["c_basis"] == "not_evaluated":
        return {"scored": False, "class": v["c_class"]}
    return {"scored": True, "class": v["c_class"], "P": round(v["c_showP"], 1), "G": round(v["c_showG"], 1),
            "R": round(v["c_showR"], 1), "total": round(v["c_total"], 1),
            "gates": [bool(v["c_gP"]), bool(v["c_gG"]), bool(v["c_gR"])], "approaching": bool(v["c_approaching"])}


def agree(py: dict, xl: dict) -> bool:
    keys = ("scored", "class", "P", "G", "R", "total", "gates", "approaching") if py["scored"] else ("scored", "class")
    return all(py.get(k) == xl.get(k) for k in keys)


def check_cases(policy: dict, cases: list[tuple[str, dict]], app) -> list[dict]:
    """Score every (label, form) under one policy in both engines; one record per case."""
    path = Path(tempfile.mkdtemp(prefix="fre_calc_")) / "calculator.xlsx"
    builder.main(path, policy)
    records = []
    with open_copy(app, path) as book:
        app.Calculation = -4135
        for label, form in cases:
            too_big = any(len(form[key]) > n for key, (_, _, n) in INPUT_RANGES.items())
            if too_big:
                continue
            enter(book, form)
            app.Calculate()
            py, xl = python_result(form, policy), excel_result(book)
            records.append({"case": label, "python": py, "excel": xl, "match": agree(py, xl), "form": form})
        errors = formula_errors(book)
    if errors:
        raise AssertionError(f"Formula errors in the workbook: {errors[:10]}")
    path.unlink(missing_ok=True)
    return records


def run(random_per_policy: int = 150, seed: int = 2026) -> dict:
    """All checks: the 22 scenarios and random forms under every variant policy."""
    out = {}
    with excel() as app:
        for name, policy in variant_policies().items():
            rng = random.Random(seed)
            cases = [(s["name"], scenario_form(s)) for s in SCENARIOS]
            cases += [(f"Random {i + 1}", random_form(rng)) for i in range(random_per_policy)]
            out[name] = check_cases(policy, cases, app)
    return out


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    failures = 0
    for name, records in run(n).items():
        bad = [r for r in records if not r["match"]]
        failures += len(bad)
        scored = sum(r["python"]["scored"] for r in records)
        print(f"{name}: {len(records)} cases ({scored} scored), {len(bad)} mismatches")
        for r in bad[:8]:
            print("   ", r["case"], "\n      python:", r["python"], "\n      excel: ", r["excel"])
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
