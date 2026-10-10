# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A faculty research and scholarship evaluation tool for a School of Public Health (Old Dominion University): Publications, Grants and Presentations → a 0-100 score and an Exceeds / Meets / Does Not Meet classification. It is a decision aid for the annual review, not a verdict.

Document map, in order of authority:

- `prompt0..md` (double dot in the filename) – Phase 1 brief; the project baseline for intent.
- `prompt2.md` – Phase 2 brief: scoring-policy settings page, web app, Excel calculator, validation workbook, user guide. SAS is out of scope.
- `REVIEW_FINDINGS.md` – numbered gaps in the Phase 1 logic. Other documents and test names cite these numbers (for example 2.5).
- `PROVISIONAL_POLICY.md` – every threshold and criterion the provisional policy applies, with its source and the finding it answers. Section 8 is generated from `engine/policy.py`; regenerate it when a default changes. The app's Guide tab displays this file.
- `docs/` – the two ODU source documents. Neither states numeric minimums.
- `research_eval.py.txt`, `scenarios.py.txt`, `sensitivity.py.txt` – the original Phase 1 engine. **Do not edit them**: the tests load them as the reference that the "Phase 1 original" preset must reproduce.
- `prompt1.md` – unrelated (a docs-editor PRD). Ignore it.

Not built yet from Phase 2: the Excel calculator, the validation workbook and the user guide PDF.

## Commands

Run everything from `faculty_research_webapp/`:

```bash
pip install -r requirements.txt
streamlit run app.py                      # the app, http://localhost:8501
python -m pytest                          # all tests
python -m pytest tests/test_engine.py -k "2_5"    # one test, by finding number or name
python -m engine.sensitivity              # Phase 1 vs provisional on the 22 scenarios
```

## Architecture

**Anchor-and-excellence model** (`engine/research_eval.py`). Each domain has a weight (P 50, G 35, R 15) and a minimum-expectation gate. Meeting the gate earns the anchor (70% of the weight). Quality-weighted units above the domain benchmark earn the remaining 30%, linearly up to a saturation cap. Meeting every gate therefore yields exactly 70.

`evaluate(fac, policy)`:

1. `validate` runs first. Any error returns class `Incomplete: input errors` with no score; the engine never raises on bad input.
2. `adjustment_factor` = (research effort / standard) × (months active / 12), clamped. It scales the publication benchmark and the saturation caps.
3. `pub_units` / `grant_units` / `pres_units` return units, gate and partial signals, flags, and `lines` (the per-item breakdown shown to users).
4. Gate resolution: the annual gate, then first-year, reduced-assignment and three-year rolling-window allowances. `gate_basis` records which one applied.
5. Classification: gates first, then the `exceeds_rule`.

`flags` are for committee attention; `notes` explain an allowance or proration.

**A policy is a plain dict** (`engine/policy.py`) holding every number and rule switch. Two presets:

- `LEGACY` – Phase 1 behaviour, exactly.
- `PROVISIONAL` – the default; `LEGACY` plus the overrides in `_provisional()`.

The governing rule: **a scoring change is a new policy key whose `LEGACY` value reproduces Phase 1.** Never change behaviour unconditionally, and never put a literal in the engine. `tests/test_engine.py` enforces this by comparing the engine under `LEGACY` with the original `.py.txt` engine on the 22 scenarios and 1,500 random profiles. Then add the key to `check_policy`, to `POLICY_GROUPS` or `POLICY_TABLES` in `app.py` so it appears on the settings page, and to `PROVISIONAL_POLICY.md`.

`fingerprint(policy)` is a short hash printed on every report. It treats 10000 and 10000.0 as equal because the settings widgets return floats.

**App layers.** `app.py` (Streamlit screens) → `forms.py` (entry tables ↔ engine record; `rows_from_faculty` is the inverse of `build_faculty`, and a test round-trips all 22 scenarios through both) → `engine`. `storage.py` writes the active policy, its change log and saved evaluations under `data/` (git-ignored; personnel data). `exports.py` builds the PDF and Excel reports.

**Look and feel.** Base colours, radius and typefaces come from `.streamlit/config.toml`; `ui.stylesheet` reads them through `st.get_option`, so do not hard-code a theme colour in `ui.py` (only the green, amber and red status colours live there). `ui.py` also holds the hand-built HTML (masthead, sidebar policy card, result panel), injected with `st.html`. The sentence under the classification comes from `ui.result_reason`, which switches on the engine's `class_basis`; add a branch there whenever the engine gains a new way to reach a class. Every user-entered string passed into that HTML must go through `html.escape`. The two typefaces (Public Sans, Newsreader; both SIL Open Font License) are bundled in `static/` and served by Streamlit's static serving, so the app works offline. The result panel is the one deliberately bold element: a 0-100 scale with the Meets and Exceeds thresholds, and per-domain bars with a line at the points earned by meeting the minimum.

Streamlit state: each entry table's base DataFrame lives in `st.session_state["tables"]` and the editor key carries a revision number. Loading a form goes through `pending_form` plus `st.rerun()` so widget state is set before the widgets exist. Do not write the editor's return value back into `tables`.

The Scoring policy tab builds a `draft` from the widgets on every run and compares it with the saved policy; a locked policy renders the same widgets disabled.

## Gotchas

- Journal tier is an int (`0`-`3`; 0 is a questionable venue); venue tier is a string (`"A"`, `"B"`, `"C"`, `"0"`). JSON turns tier keys into strings; `policy.normalise` restores them.
- Publication `count` (drives the gate) and `units` (drive excellence) are separate tallies: a book counts as 2, only the first chapter counts, tier-0 and non-peer-reviewed articles count as 0.
- Scenarios reuse dict objects through list multiplication (`[A(0)] * 5`); deep-copy before mutating.
- `engine/scenarios.py` is the Phase 1 file plus an explicit `role: presenter` on presentations, because the provisional policy treats a missing role as coauthor.
- `forms.build_faculty` depends on the policy (award size bands, whether the `second` author role exists), so rebuild the record when comparing two policies.
- The standard research effort (40%) is unconfirmed and scales every prorated expectation.
