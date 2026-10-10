# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A faculty research and scholarship evaluation tool for a School of Public Health (Old Dominion University): Publications, Grants and Presentations → a 0-100 score and an Exceeds / Meets / Does Not Meet classification. It is a decision aid for the annual review, not a verdict.

Document map, in order of authority:

- `prompt0..md` (double dot in the filename) – Phase 1 brief; the project baseline for intent.
- `prompt2.md` – Phase 2 brief: scoring-policy settings page, web app, Excel calculator, validation workbook, user guide. SAS is out of scope.
- `REVIEW_FINDINGS.md` – numbered gaps in the Phase 1 logic. Other documents and test names cite these numbers (for example 2.5).
- `PROVISIONAL_POLICY.md` – every threshold and criterion the provisional policy applies, with its source and the finding it answers. Section 8 is generated: after changing a default run `python -m tools.write_policy_tables` from `faculty_research_webapp/`. Sections 1-7 are hand-written and must be updated to match. The app's Guide tab displays this file.
- `docs/` – the two ODU source documents. Neither states numeric minimums.
- `research_eval.py.txt`, `scenarios.py.txt`, `sensitivity.py.txt` – the original Phase 1 engine. **Do not edit them**: the tests load them as the reference that the "Phase 1 original" preset must reproduce.
- `prompt1.md` – unrelated (a docs-editor PRD). Ignore it.

Generated deliverables at the repo root. Never edit them by hand; change the generator and rebuild:

- `faculty_research_calculator.xlsx` – the engine as Excel formulas (no macros), from `tools/build_excel_calculator.py`.
- `faculty_evaluation_validation.xlsx` – Python vs Excel vs web app, from `tools/build_validation_workbook.py`.
- `user_guide.pdf` – from `tools/build_user_guide.py`; its numbers come from the policy and its worked example from the engine. The screenshots in `guide_images/` are captured by hand from the running app.

## Commands

Run everything from `faculty_research_webapp/`:

```bash
pip install -r requirements.txt
streamlit run app.py                      # the app, http://localhost:8501
python -m pytest                          # all tests
python -m pytest tests/test_engine.py -k "2_5"    # one test, by finding number or name
python -m engine.sensitivity              # Phase 1 vs provisional on the 22 scenarios
python -m tools.write_policy_tables       # regenerate section 8 of PROVISIONAL_POLICY.md
python -m tools.build_excel_calculator    # rebuild the Excel calculator
python -m tools.validate_excel 40         # Excel vs engine, in real Excel (Windows; about 1 s per case)
python -m tools.build_validation_workbook # rebuild the validation workbook (about 15 minutes)
python -m tools.build_user_guide          # rebuild the user guide PDF
FRE_EXCEL=1 python -m pytest tests/test_excel_calculator.py   # include the tests that drive Excel
```

## Architecture

**Anchor-and-excellence model** (`engine/research_eval.py`). Each domain has a weight (P 50, G 35, R 15) and a minimum-expectation gate. Meeting the gate earns the anchor (70% of the weight). Quality-weighted units above the domain benchmark earn the remaining 30%, linearly up to a saturation cap. Meeting every gate therefore yields exactly 70.

`evaluate(fac, policy)`:

1. `validate` runs first. Any error returns class `Incomplete: input errors` with no score; the engine never raises on bad input, whatever its shape (a fuzz test corrupts random records to hold this). Yes/no fields must be real booleans.
2. `adjustment_factor` = (research effort / standard) × (months active / 12), clamped. It scales the publication benchmark and the saturation caps.
3. `pub_units` / `grant_units` / `pres_units` return units, gate and partial signals, flags, and `lines` (the per-item breakdown shown to users).
4. Gate resolution: the annual gate, then first-year, reduced-assignment and three-year rolling-window allowances. `gate_basis` records which one applied.
5. `_display_scores`: the overall score is the rounded true total; with `total_from_rounded_parts` on, one domain score is shown 0.1 off its own rounding where needed so the parts add up.
6. Classification: gates first, then the `exceeds_rule`. `class_basis` records why.

`flags` are for committee attention; `notes` explain an allowance or proration.

**A policy is a plain dict** (`engine/policy.py`) holding every number and rule switch. Two presets:

- `LEGACY` – Phase 1 behaviour, exactly.
- `PROVISIONAL` – the default; `LEGACY` plus the overrides in `_provisional()`.

The governing rule: **a scoring change is a new policy key whose `LEGACY` value reproduces Phase 1.** Never change behaviour unconditionally, and never put a literal in the engine. The tests enforce this by comparing the engine under `LEGACY` with the original `.py.txt` engine on the 22 scenarios and on random profiles; when a new input field can affect scoring, add it to the random generators (`_random_profile` in `tests/test_engine.py`, and the DOI/id/prior-year battery in `tests/test_engine_review.py`), because a field the generators never produce is not covered. Then add the key to `POLICY_GROUPS` or `POLICY_TABLES` in `policy_labels.py` so it appears on the settings page and in the policy note, and describe it in `PROVISIONAL_POLICY.md`. `check_policy` types every key against `LEGACY` automatically; add a range check there if the key needs one.

`check_policy` must reject every policy the engine cannot run: a test asserts that any accepted variant scores all 22 scenarios without raising. `normalise` gives the canonical form (known keys only, int tier keys, whole-number settings as ints, role lists in standard order); `evaluate` normalises a policy that arrives with string tier keys.

`fingerprint(policy)` is a short hash of the scoring settings, printed on every report. It ignores the policy name, treats 10000 and 10000.0 as equal (the settings widgets return floats), and treats `True` and `1` as different.

**App layers.** `app.py` (Streamlit screens) → `forms.py` (entry tables ↔ engine record; `rows_from_faculty` is the inverse of `build_faculty`, and a test round-trips all 22 scenarios through both) → `engine`. `storage.py` writes the active policy, its change log and saved evaluations under `data/` (git-ignored; personnel data). `exports.py` builds the PDF and Excel reports.

**Excel calculator.** The scoring rules exist in three places that must agree: `engine/research_eval.py`, `forms.build_faculty` (how an entry row becomes engine input) and the formulas written by `tools/build_excel_calculator.py`. A rule change must be made in all three, then checked with `python -m tools.validate_excel`, which types cases into the workbook through Excel (COM) and compares every score, class and minimum with the engine under four policies that between them flip every switch. The workbook mirrors the web entry form, not the raw engine record: one grant row with a Status, exactly as `forms.py` defines it. Settings are named cells (`s_<policy key>`), per-row calculations are named columns (`PUB_`, `GRA_`, `PRE_`), and each step of `evaluate` is one named line on the Calc sheet (`c_...`). Use only functions available since Excel 2007 (no LET, XLOOKUP, IFS or TEXTJOIN). Excel rounds half up only, so the unmodified Phase 1 preset cannot be reproduced there. Excel refuses to open a workbook containing one syntactically invalid formula; `tests/test_excel_calculator.py` checks brackets and names without needing Excel.

**Look and feel.** Base colours, radius and typefaces come from `.streamlit/config.toml`; `ui.stylesheet` reads them through `st.get_option`, so do not hard-code a theme colour in `ui.py` (only the green, amber and red status colours live there). `ui.py` also holds the hand-built HTML (masthead, sidebar policy card, result panel), injected with `st.html`. The sentence under the classification comes from `ui.result_reason`, which switches on the engine's `class_basis`; add a branch there whenever the engine gains a new way to reach a class. Every user-entered string passed into that HTML must go through `html.escape`. The two typefaces (Public Sans, Newsreader; both SIL Open Font License) are bundled in `static/` and served by Streamlit's static serving, so the app works offline. The result panel is the one deliberately bold element: a 0-100 scale with the Meets and Exceeds thresholds, and per-domain bars with a line at the points earned by meeting the minimum.

Streamlit state: each entry table's base DataFrame lives in `st.session_state["tables"]` and the editor key carries a revision number. Loading a form goes through `pending_form` plus `st.rerun()` so widget state is set before the widgets exist. Do not write the editor's return value back into `tables`.

The Scoring policy tab builds a `draft` from the widgets on every run and compares it with the saved policy; a locked policy renders the same widgets disabled.

## Gotchas

- Journal tier is an int (`0`-`3`; 0 is a questionable venue); venue tier is a string (`"A"`, `"B"`, `"C"`, `"0"`). JSON turns tier keys into strings; `policy.normalise` restores them.
- When checking that a test would notice a regression, inject the bug into a scratch copy of the engine and run the engine tests; several early tests passed for the wrong reason until this was done.
- Publication `count` (drives the gate) and `units` (drive excellence) are separate tallies: a book counts as 2, only the first chapter counts, tier-0 and non-peer-reviewed articles count as 0.
- Scenarios reuse dict objects through list multiplication (`[A(0)] * 5`); deep-copy before mutating.
- `engine/scenarios.py` is the Phase 1 file plus an explicit `role: presenter` on presentations, because the provisional policy treats a missing role as coauthor.
- `forms.build_faculty` depends on the policy (award size bands, whether the `second` author role exists), so rebuild the record when comparing two policies.
- The standard research effort (40%) is unconfirmed and scales every prorated expectation.
