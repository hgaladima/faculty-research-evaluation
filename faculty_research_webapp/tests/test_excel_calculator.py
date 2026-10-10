"""The Excel calculator: static checks always, and a comparison with the engine when Excel is available.

The comparison drives a real copy of Excel and takes about a minute, so it runs only when FRE_EXCEL=1 is set:
    FRE_EXCEL=1 python -m pytest tests/test_excel_calculator.py
"""
import os
import re

import pytest

import forms
from engine import LEGACY, PROVISIONAL
from engine.scenarios import SCENARIOS
from tools import build_excel_calculator as builder
from tools import validate_excel

NAME = re.compile(r"\b(?:[scfoxd]_\w+|L_\w+|(?:PUB|GRA|PRE|OT|TR|RM|AU|PT|OO|ED|GR|SZ|RV|PR|VN|RO)_\w+)\b")
needs_excel = pytest.mark.skipif(os.environ.get("FRE_EXCEL") != "1", reason="set FRE_EXCEL=1 to drive Excel")


@pytest.fixture(scope="module")
def workbook():
    return builder.Calculator(PROVISIONAL).build()


def formulas(wb):
    for ws in wb:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    yield ws.title, cell.coordinate, cell.value


def test_every_formula_has_balanced_brackets(workbook):
    for sheet, ref, formula in formulas(workbook):
        text = re.sub(r'"[^"]*"', '""', formula)
        assert text.count("(") == text.count(")"), f"{sheet}!{ref}"


def test_every_name_used_in_a_formula_is_defined(workbook):
    defined = {name.lower() for name in workbook.defined_names}
    for sheet, ref, formula in formulas(workbook):
        for used in NAME.findall(re.sub(r'"[^"]*"', '""', formula)):
            assert used.lower() in defined, f"{sheet}!{ref} uses undefined name {used}"


def test_defined_names_are_unique_ignoring_case(workbook):
    names = [name.lower() for name in workbook.defined_names]
    assert len(names) == len(set(names))


def test_every_policy_setting_reaches_the_workbook(workbook):
    defined = set(workbook.defined_names)
    in_tables = {"journal_tier_mult", "author_role_mult", "other_output_units", "editorial_units", "submission_base",
                 "award_base", "grant_role_mult", "grant_review_units", "pres_type_base", "venue_tier_mult",
                 "pres_role_mult", "award_gate_roles", "pres_gate_roles", "policy_name"}
    for key, value in PROVISIONAL.items():
        if key in in_tables:
            continue
        names = [f"s_{key}_{sub}" for sub in value] if isinstance(value, dict) else [f"s_{key}"]
        assert set(names) <= defined, key


def test_entry_sheets_use_the_same_columns_and_choices_as_the_web_forms(workbook):
    for sheet, columns in (("Publications", forms.PUB_COLUMNS), ("Grants", forms.GRANT_COLUMNS),
                           ("Presentations", forms.PRES_COLUMNS)):
        headers = [workbook[sheet].cell(row=builder.HEADER, column=i + 1).value for i in range(len(columns))]
        assert headers == columns
    lists = {ws_col[0].value: [c.value for c in ws_col[1:] if c.value] for ws_col in workbook["Lists"].iter_cols()}
    assert lists["L_pubtype"] == list(forms.PUB_TYPES) and lists["L_status"] == forms.GRANT_STATUSES
    assert lists["L_grantrole"] == list(forms.GRANT_ROLES) and lists["L_presrole"] == list(forms.PRES_ROLES)


def test_entry_cells_are_unlocked_and_calculated_cells_locked(workbook):
    ws = workbook["Publications"]
    assert ws.protection.sheet and not ws["A5"].protection.locked and ws["N5"].protection.locked
    assert workbook["Settings"].protection.sheet and workbook["Settings"]["B8"].protection.locked


@needs_excel
def test_excel_matches_the_engine_on_the_22_scenarios_and_random_cases():
    import random
    from tools.excel_com import excel
    rng = random.Random(5)
    cases = [(s["name"], validate_excel.scenario_form(s)) for s in SCENARIOS]
    cases += [(f"Random {i}", validate_excel.random_form(rng)) for i in range(25)]
    with excel() as app:
        records = validate_excel.check_cases(PROVISIONAL, cases, app)
    assert len(records) == len(cases)
    assert [r["case"] for r in records if not r["match"]] == []


@needs_excel
def test_the_comparison_notices_a_workbook_built_from_a_different_policy():
    from tools.excel_com import excel
    cases = [(s["name"], validate_excel.scenario_form(s)) for s in SCENARIOS]
    half_up_phase1 = dict(LEGACY, rounding="half_up")
    with excel() as app:
        path_records = validate_excel.check_cases(half_up_phase1, cases, app)
    assert all(r["match"] for r in path_records)
    disagree = [s["name"] for s in SCENARIOS
                if validate_excel.python_result(validate_excel.scenario_form(s), PROVISIONAL)["class"]
                != next(r for r in path_records if r["case"] == s["name"])["excel"]["class"]]
    assert len(disagree) >= 3
