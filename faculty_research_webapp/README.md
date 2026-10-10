# Faculty Research Evaluation: web application

A locally run tool for the annual review of faculty research and scholarship. Enter a faculty member's publications, grants and presentations; the app returns a 0-100 research score, a classification (Exceeds, Meets or Does Not Meet Expectations) and a line-by-line explanation of the points.

It is a decision aid. The scoring policy it ships with is provisional until the annual review committee adopts it; see `../PROVISIONAL_POLICY.md`.

## Run it

Requires Python 3.11 or later.

```bash
pip install -r requirements.txt
streamlit run app.py
```

On Windows, double-click `run_app.bat` after installing the requirements. The app opens in your browser at `http://localhost:8501`.

## Use it

1. **Faculty** – name, year, assigned research effort and months active.
2. **Publications, Grants, Presentations, Other activity** – one row per item; pick from the dropdowns.
3. **Results** – score, classification, minimums met, and how each point was earned. Save the evaluation, or download the report as PDF or Excel.
4. **Scoring policy** – every threshold and criterion. Review the effect of a change on the 22 test profiles before saving, then approve and lock the policy for the year.

To try it without typing, load one of the 22 hypothetical profiles from the sidebar.

## Data and access

The app listens on this computer only (`localhost`); other machines on the network cannot reach it. That is set in `.streamlit/config.toml`. Do not change it: the app has no login, so anyone who could reach it could read every evaluation and reopen the policy.

Saved evaluations, the active policy and its change log are written to the `data/` folder next to the app, as plain files. Treat `data/` as personnel records, and run the app only on a machine authorised evaluators use. Institutional deployment would need single sign-on, role-based access, encrypted storage and IT review first.

If two windows are open, a policy saved in one is picked up by the other on its next action; a save from an out-of-date window is refused.

## Tests

```bash
python -m pytest
```

The tests include an exact reproduction of the Phase 1 results: under the "Phase 1 original" preset the engine matches the original `research_eval.py.txt` on all 22 scenarios and on 1,500 random profiles.

## Layout

| Path | Purpose |
|---|---|
| `engine/research_eval.py` | Scoring engine |
| `engine/policy.py` | The two policy presets, policy checks and fingerprint |
| `engine/scenarios.py` | The 22 test profiles |
| `engine/sensitivity.py` | Compare classifications under two policies |
| `forms.py` | Maps the entry tables to the engine's input |
| `storage.py` | Policy, change log and saved evaluations on disk |
| `exports.py` | PDF and Excel reports |
| `app.py` | The screens |
| `ui.py`, `.streamlit/config.toml` | Styling: theme, stylesheet and the result panel |
| `static/` | Bundled typefaces (Public Sans and Newsreader, SIL Open Font License) |
