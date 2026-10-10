"""Faculty Research Evaluation: local web application.  Run with:  streamlit run app.py"""
from __future__ import annotations

import copy
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

import exports
import forms
import storage
import ui
from engine import PRESETS, check_policy, evaluate, fingerprint
from engine.policy import (EXCEEDS_RULES, GRANT_ROLES, PRES_ROLES, REDUCED_RULES, ROLLING_BENCHMARKS,
                           ROUNDING_MODES, diff, minimum_score, normalise, to_json)
from engine.research_eval import INCOMPLETE, NOT_EVALUATED
from engine.scenarios import SCENARIOS

POLICY_NOTE = Path(__file__).resolve().parent.parent / "PROVISIONAL_POLICY.md"

RANKS = ["Assistant Professor", "Associate Professor", "Professor", "Other"]
APPOINTMENTS = ["Tenure-track", "Tenured", "Non-tenure-track", "Other"]
INFO_DEFAULTS = {
    "name": "", "faculty_id": "", "rank": RANKS[0], "department": "", "appointment": APPOINTMENTS[0],
    "evaluation_year": str(date.today().year), "research_effort": None, "months_active": 12.0,
    "first_year": False, "sessions_chaired": 0, "proposals_in_development": 0, "unfunded_projects": 0,
    "manuscripts_under_review": 0, "abstracts_submitted": 0,
    "use_pubs_prior2": False, "pubs_prior2": 0, "use_grant_active_years_prior2": False,
    "grant_active_years_prior2": 0, "use_pres_prior2": False, "pres_prior2": 0,
    "ctx_awards": "", "ctx_mentoring": "", "ctx_community": "", "ctx_notes": "",
}
CONTEXT_LABELS = {"ctx_awards": "Research awards and recognition",
                  "ctx_mentoring": "Research mentoring and dissertation supervision",
                  "ctx_community": "Community-engaged, translational and interdisciplinary work",
                  "ctx_notes": "Evaluator notes"}
TABLES = {
    "pubs": (forms.PUB_COLUMNS, ["Peer reviewed", "Student or mentee first author", "Credited in a prior year"],
             ["Documented impacts", "Impact factor (info)"]),
    "grants": (forms.GRANT_COLUMNS, ["Competitive", "Also submitted this year", "Scored or discussed",
                                     "Credited in a prior year"], ["Total amount ($)"]),
    "pres": (forms.PRES_COLUMNS, ["Peer-reviewed abstract (info)"], []),
    "editorial": (forms.EDITORIAL_COLUMNS, [], ["Count"]),
    "reviews": (forms.REVIEW_COLUMNS, [], ["Count"]),
}
TRUE_BY_DEFAULT = {"Peer reviewed", "Competitive"}

JOURNAL_TIER_HELP = ("Tier 1: top quartile (Q1) of its subject category, or the flagship journal of a major "
                     "society in the field. Tier 2: second quartile (Q2). Tier 3: other peer-reviewed journal "
                     "indexed in MEDLINE, Scopus or Web of Science. Questionable: no verifiable peer review.")
VENUE_TIER_HELP = ("Tier A: major national or international society meeting with competitive peer-reviewed "
                   "abstract selection. Tier B: regional or state society meeting, or a national meeting with "
                   "light review. Tier C: local meeting or limited review. Quality counts more than geography.")

OPTION_LABELS = {
    "total": "Score at or above the Exceeds threshold",
    "breadth": "Score at or above the threshold AND two domains strong",
    "total_or_distinction": "Score at or above the threshold, OR a new large competitive award as PI/MPI",
    "breadth_or_distinction": "Threshold AND two domains strong, OR a new large competitive award as PI/MPI",
    "waive_below_threshold": "Waive grant and presentation minimums outright",
    "documented_activity": "Require documented activity in place of the full minimum",
    "current_year": "This year's (possibly prorated) minimum for all three years",
    "standard_prior_years": "This year's minimum plus the standard minimum for the two prior years",
    "bankers": "Round half to even (Python default)", "half_up": "Round half up (matches Excel)",
}

POLICY_GROUPS = [
    ("Weights and classification", True, [
        ("weights.P", "Publications: maximum points", "num"),
        ("weights.G", "Grants and contracts: maximum points", "num"),
        ("weights.R", "Presentations: maximum points", "num"),
        ("anchor_share", "Share of a domain's points earned by meeting its minimum (0-1)", "num"),
        ("meets_threshold", "Meets Expectations threshold", "num"),
        ("enforce_meets_threshold", "Meets also requires the score to reach the Meets threshold", "bool"),
        ("exceeds_threshold", "Exceeds Expectations threshold", "num"),
        ("exceeds_rule", "Rule for Exceeds Expectations", EXCEEDS_RULES),
        ("breadth_level", "A domain is 'strong' at this share of its points (0-1)", "num"),
        ("distinction_min_total", "Floor score for the large-award route to Exceeds", "num"),
        ("approaching_threshold", "Flag as 'approaching' at this score when one minimum is unmet", "num"),
        ("domain_exceeds_level", "A domain shows 'Exceeds' at this share of its points (0-1)", "num"),
    ]),
    ("Minimum expectations", True, [
        ("pub_min_count", "Peer-reviewed publications expected per year", "int"),
        ("grant_gate_requires_external", "Grant minimum requires an external (not internal) submission", "bool"),
        ("award_gate_roles", "Roles on a new award that satisfy the grant minimum", ("multi", GRANT_ROLES)),
        ("pres_gate_roles", "Roles that satisfy the presentation minimum", ("multi", PRES_ROLES)),
    ]),
    ("Adjustments for effort, leave and career stage", True, [
        ("standard_research_effort", "Standard research assignment (%)", "num"),
        ("factor_min", "Lowest adjustment factor", "num"),
        ("factor_max", "Highest adjustment factor", "num"),
        ("evaluate_zero_assignment", "Rate faculty with 0% research effort or 0 active months", "bool"),
        ("reduced_assignment_factor", "Reduced assignment applies at or below this factor", "num"),
        ("reduced_assignment_rule", "Treatment of a reduced assignment", REDUCED_RULES),
        ("rolling_max_domains", "Domains the three-year rolling window may rescue in one year", [0, 1, 2, 3]),
        ("rolling_benchmark", "Publication requirement over the rolling window", ROLLING_BENCHMARKS),
    ]),
    ("Counting rules", True, [
        ("dedupe_doi", "Count a publication once when the same DOI is entered twice", "bool"),
        ("dedupe_submission_award", "Credit a proposal funded in the same year as an award only", "bool"),
        ("amount_bands.minor_max", "Awards below this amount are 'minor' ($)", "num"),
        ("amount_bands.large_min", "Awards at or above this amount are 'large' ($)", "num"),
        ("rounding", "Rounding of displayed scores", ROUNDING_MODES),
        ("total_from_rounded_parts", "Overall score is the sum of the displayed domain scores", "bool"),
        ("missing_defaults.venue", "Venue tier assumed when not yet verified", ["A", "B", "C"]),
        ("missing_defaults.pres_role", "Presentation role assumed when missing", PRES_ROLES),
        ("missing_defaults.book_role", "Book author role assumed when missing", ["lead", "coauthor"]),
    ]),
    ("Benchmarks, increments and caps (in units)", False, [
        ("benchmark_units.P", "Publications: benchmark units at the standard minimum", "num"),
        ("benchmark_units.G", "Grants: benchmark units", "num"),
        ("benchmark_units.R", "Presentations: benchmark units", "num"),
        ("saturation.P", "Publications: units above benchmark for full excellence credit", "num"),
        ("saturation.G", "Grants: units above benchmark for full excellence credit", "num"),
        ("saturation.R", "Presentations: units above benchmark for full excellence credit", "num"),
        ("student_mentee_increment", "Increment when a student or mentee is first author", "num"),
        ("book_units", "Scholarly book (lead author)", "num"),
        ("book_coauthor_mult", "Book: multiplier for a non-lead author", "num"),
        ("chapter_units", "Book chapter", "num"),
        ("chapter_cap", "Cap on book-chapter credit (blank = no cap)", "optnum"),
        ("other_output_cap", "Cap on other scholarly outputs", "num"),
        ("editorial_cap", "Cap on editorial and review service", "num"),
        ("impact_units", "Each documented impact on policy or practice", "num"),
        ("impact_cap", "Cap on documented impacts", "num"),
        ("noncompetitive_mult", "Noncompetitive submission multiplier", "num"),
        ("noncompetitive_award_mult", "Noncompetitive award or contract multiplier", "num"),
        ("scored_bonus", "Bonus for a scored or discussed proposal", "num"),
        ("submission_cap", "Cap on credit from submissions", "num"),
        ("implementation_units", "Each active funded project in a substantive role", "num"),
        ("implementation_cap", "Cap on active-project credit", "num"),
        ("grant_review_cap", "Cap on grant-review credit", "num"),
        ("development_units", "Each proposal in development or unfunded project", "num"),
        ("development_cap", "Cap on development credit", "num"),
        ("chair_units", "Each session chaired or organised", "num"),
        ("chair_cap", "Cap on session-chair credit", "num"),
        ("local_cap", "Cap on institutional, outreach and seminar presentations", "num"),
    ]),
]
POLICY_TABLES = [
    ("journal_tier_mult", "Journal tier multipliers (0 = questionable venue)"),
    ("author_role_mult", "Author role multipliers"),
    ("other_output_units", "Other scholarly outputs (units each)"),
    ("editorial_units", "Editorial and peer-review service (units each)"),
    ("submission_base", "Proposal submitted: base units by size band"),
    ("award_base", "Award received: base units by size band"),
    ("grant_role_mult", "Grant role multipliers"),
    ("grant_review_units", "Grant review panels (units each)"),
    ("pres_type_base", "Presentation type: base units"),
    ("venue_tier_mult", "Venue tier multipliers"),
    ("pres_role_mult", "Presentation role multipliers"),
]


# ------------------------------------------------------------------------------- state
def make_table(name: str, rows: list[dict]) -> pd.DataFrame:
    columns, bool_cols, num_cols = TABLES[name]
    df = pd.DataFrame(rows, columns=columns).astype(object)
    for c in bool_cols:
        df[c] = df[c].map(lambda v: (c in TRUE_BY_DEFAULT) if pd.isna(v) else bool(v)).astype(bool)
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    return df


def table_records(df: pd.DataFrame) -> list[dict]:
    return df.astype(object).where(df.notna(), None).to_dict("records")


def apply_form(form: dict) -> None:
    for key, default in INFO_DEFAULTS.items():
        value = form["info"].get(key, default)
        st.session_state[f"info_{key}"] = default if value is None and default is not None else value
    if st.session_state["info_research_effort"] is None:
        st.session_state["info_research_effort"] = active_policy()["standard_research_effort"]
    for key, default in INFO_DEFAULTS.items():
        if isinstance(default, int) and not isinstance(default, bool):
            st.session_state[f"info_{key}"] = int(st.session_state[f"info_{key}"])
    for key in ("research_effort", "months_active"):
        st.session_state[f"info_{key}"] = float(st.session_state[f"info_{key}"])
    st.session_state["tables"] = {name: make_table(name, form.get(name, [])) for name in TABLES}
    st.session_state["rev"] = st.session_state.get("rev", 0) + 1


def active_policy() -> dict:
    return st.session_state["policy_state"]["policy"]


def init_state() -> None:
    if "policy_state" not in st.session_state:
        st.session_state["policy_state"] = storage.load_policy_state()
        st.session_state["pol_rev"] = 0
        st.session_state["draft_base"] = copy.deepcopy(active_policy())
        st.session_state["loaded_stamp"] = None
        apply_form({"info": {}})
    if "pending_form" in st.session_state:
        pending = st.session_state.pop("pending_form")
        st.session_state["loaded_stamp"] = pending.get("stamp")
        apply_form(pending["form"])


def current_info() -> dict:
    return {key: st.session_state.get(f"info_{key}", default) for key, default in INFO_DEFAULTS.items()}


# ------------------------------------------------------------------------------- sidebar
def sidebar() -> None:
    meta = st.session_state["policy_state"]["meta"]
    st.sidebar.html(ui.sidebar_brand())
    st.sidebar.markdown("**Scoring policy in force**")
    st.sidebar.html(ui.policy_card(active_policy()["policy_name"], meta["version"], fingerprint(active_policy()),
                                   meta["locked"], meta["approved_by"]))
    st.sidebar.markdown("**Evaluation file**")
    if st.sidebar.button("New blank evaluation", width="stretch"):
        st.session_state["pending_form"] = {"form": {"info": {}}, "stamp": None}
        st.rerun()
    saved = storage.list_evaluations()
    choice = st.sidebar.selectbox("Saved evaluations", saved, index=None, placeholder="Choose a saved evaluation")
    if st.sidebar.button("Open saved evaluation", disabled=choice is None, width="stretch"):
        record = storage.load_evaluation(choice)
        st.session_state["pending_form"] = {"form": record["form"], "stamp": record["policy"]["fingerprint"]}
        st.rerun()
    example = st.sidebar.selectbox("Example profiles (hypothetical)", [s["name"] for s in SCENARIOS], index=None,
                                   placeholder="Choose one of the 22 test profiles")
    if st.sidebar.button("Load example profile", disabled=example is None, width="stretch"):
        fac = next(s for s in SCENARIOS if s["name"] == example)
        form = forms.rows_from_faculty(fac)
        form["info"]["evaluation_year"] = str(date.today().year)
        st.session_state["pending_form"] = {"form": form, "stamp": None}
        st.rerun()


# ------------------------------------------------------------------------------- data entry
def editor(name: str, column_config: dict) -> pd.DataFrame:
    return st.data_editor(st.session_state["tables"][name], key=f"{name}_{st.session_state['rev']}",
                          num_rows="dynamic", width="stretch", hide_index=True, column_config=column_config)


def tab_info() -> None:
    st.subheader("Faculty information")
    a, b = st.columns(2)
    a.text_input("Faculty member name", key="info_name")
    b.text_input("Faculty ID", key="info_faculty_id")
    a.selectbox("Academic rank", RANKS, key="info_rank")
    b.text_input("Department", key="info_department")
    a.selectbox("Appointment type", APPOINTMENTS, key="info_appointment")
    b.text_input("Evaluation year", key="info_evaluation_year")
    st.subheader("Research assignment and adjustments")
    a, b, c = st.columns(3)
    a.number_input("Assigned research effort (%)", 0.0, 100.0, step=5.0, key="info_research_effort",
                   help=f"The policy's standard research assignment is "
                        f"{active_policy()['standard_research_effort']:g}%. Expectations are prorated from it.")
    b.number_input("Months active in the evaluation period", 0.0, 12.0, step=1.0, key="info_months_active",
                   help="Subtract approved medical, parental or other non-research leave. "
                        "Count sabbatical and research leave as active months.")
    c.checkbox("First-year faculty member", key="info_first_year")


def tab_pubs() -> pd.DataFrame:
    st.subheader("Publications and scholarly outputs")
    st.caption("One row per item published in the evaluation year. An item counts in the year it first "
               "appears (online or in print), and only once.")
    return editor("pubs", {
        "Type": st.column_config.SelectboxColumn(options=list(forms.PUB_TYPES), required=True),
        "Peer reviewed": st.column_config.CheckboxColumn(default=True),
        "Journal tier": st.column_config.SelectboxColumn(options=list(forms.JOURNAL_TIERS), help=JOURNAL_TIER_HELP),
        "Authorship": st.column_config.SelectboxColumn(
            options=list(forms.AUTHORSHIP),
            help="Sole, first, senior (last) and corresponding authors receive lead credit."),
        "Student or mentee first author": st.column_config.CheckboxColumn(
            default=False, help="Tick when a student or mentee is first author and you are senior or corresponding."),
        "Documented impacts": st.column_config.NumberColumn(
            min_value=0, step=1, help="Documented uses in policy, guidelines or practice."),
        "Quartile (info)": st.column_config.SelectboxColumn(options=forms.QUARTILES, help="Recorded; not scored."),
        "Impact factor (info)": st.column_config.NumberColumn(min_value=0.0, help="Recorded; not scored."),
        "Credited in a prior year": st.column_config.CheckboxColumn(default=False),
    })


def tab_grants() -> pd.DataFrame:
    st.subheader("Grants and contracts")
    bands = active_policy()["amount_bands"]
    st.caption(f"One row per proposal, award or continuing project. Enter the total amount for the full project "
               f"period: under ${bands['minor_max']:,.0f} is minor, ${bands['large_min']:,.0f} or more is large. "
               f"For a proposal submitted and funded in the same year, enter one row as 'Awarded this year' and "
               f"tick 'Also submitted this year'.")
    return editor("grants", {
        "Source": st.column_config.SelectboxColumn(options=forms.GRANT_SOURCES, default="External"),
        "Total amount ($)": st.column_config.NumberColumn(min_value=0, format="$%d"),
        "Role": st.column_config.SelectboxColumn(options=list(forms.GRANT_ROLES), required=True),
        "Competitive": st.column_config.CheckboxColumn(
            default=True, help="Untick for sole-source contracts and other noncompetitive funding."),
        "Status": st.column_config.SelectboxColumn(options=forms.GRANT_STATUSES, required=True),
        "Also submitted this year": st.column_config.CheckboxColumn(default=False),
        "Scored or discussed": st.column_config.CheckboxColumn(
            default=False, help="The proposal received a score or was discussed by the review panel."),
        "Credited in a prior year": st.column_config.CheckboxColumn(default=False),
    })


def tab_pres() -> pd.DataFrame:
    st.subheader("Scientific presentations")
    st.caption("One row per presentation. Venue tier is not used for institutional, outreach or seminar talks.")
    return editor("pres", {
        "Scope (info)": st.column_config.SelectboxColumn(options=forms.PRES_SCOPES, help="Recorded; not scored."),
        "Type": st.column_config.SelectboxColumn(options=list(forms.PRES_TYPES), required=True),
        "Venue tier": st.column_config.SelectboxColumn(options=list(forms.VENUE_TIERS), help=VENUE_TIER_HELP),
        "Role": st.column_config.SelectboxColumn(options=list(forms.PRES_ROLES), required=True),
        "Peer-reviewed abstract (info)": st.column_config.CheckboxColumn(default=False),
    })


def tab_other() -> tuple[pd.DataFrame, pd.DataFrame]:
    st.subheader("Other scholarly activities")
    st.caption("These are credited inside the three domains, with caps, as shown on the results tab.")
    a, b = st.columns(2)
    with a:
        st.markdown("**Editorial and peer-review service** (credited under Publications)")
        editorial = editor("editorial", {
            "Role": st.column_config.SelectboxColumn(options=list(forms.EDITORIAL_ROLES), required=True),
            "Count": st.column_config.NumberColumn(min_value=1, step=1, default=1)})
    with b:
        st.markdown("**Grant review panels** (credited under Grants)")
        reviews = editor("reviews", {
            "Panel type": st.column_config.SelectboxColumn(options=list(forms.REVIEW_TYPES), required=True),
            "Count": st.column_config.NumberColumn(min_value=1, step=1, default=1)})
    a, b, c = st.columns(3)
    a.number_input("Conference sessions chaired or organised", 0, step=1, key="info_sessions_chaired")
    b.number_input("Grant proposals in development (documented)", 0, step=1, key="info_proposals_in_development")
    c.number_input("Unfunded research projects under way", 0, step=1, key="info_unfunded_projects")
    a.number_input("Manuscripts under review", 0, step=1, key="info_manuscripts_under_review")
    b.number_input("Conference abstracts submitted", 0, step=1, key="info_abstracts_submitted")

    st.markdown("**Three-year rolling window** (only used when a minimum is unmet this year)")
    a, b, c = st.columns(3)
    for col, key, label in ((a, "pubs_prior2", "Publications counted in the two prior years"),
                            (b, "grant_active_years_prior2", "Prior two years with the grant minimum met (0-2)"),
                            (c, "pres_prior2", "Qualifying presentations in the two prior years")):
        col.checkbox(f"Provide: {label.lower()}", key=f"info_use_{key}")
        col.number_input(label, 0, step=1, key=f"info_{key}", disabled=not st.session_state[f"info_use_{key}"],
                         label_visibility="collapsed")

    st.markdown("**Recorded for the committee and the narrative (not scored)**")
    a, b = st.columns(2)
    a.text_area(CONTEXT_LABELS["ctx_awards"], key="info_ctx_awards", height=90)
    b.text_area(CONTEXT_LABELS["ctx_mentoring"], key="info_ctx_mentoring", height=90)
    a.text_area(CONTEXT_LABELS["ctx_community"], key="info_ctx_community", height=90)
    b.text_area(CONTEXT_LABELS["ctx_notes"], key="info_ctx_notes", height=90)
    return editorial, reviews


# ------------------------------------------------------------------------------- results
def tab_results(form: dict) -> None:
    policy, meta = active_policy(), st.session_state["policy_state"]["meta"]
    info = form["info"]
    fac, problems = forms.build_faculty(info, form["pubs"], form["grants"], form["pres"], form["editorial"],
                                        form["reviews"], policy)
    if problems:
        st.error("Complete these entries before the evaluation can be calculated:\n\n" +
                 "\n".join(f"- {p}" for p in problems))
        return
    result = evaluate(fac, policy)
    stamp = st.session_state.get("loaded_stamp")
    if stamp and stamp != result["policy"]["fingerprint"]:
        st.warning(f"This evaluation was saved under a different scoring policy (fingerprint {stamp}). "
                   f"The results below use the policy now in force.")
    who = ", ".join(x for x in (info["name"] or "Unnamed faculty member", info["faculty_id"],
                                info["evaluation_year"]) if x)

    cls = result["class"]
    if cls == INCOMPLETE:
        st.error("The evaluation cannot be calculated until these input errors are fixed:\n\n" +
                 "\n".join(f"- {e}" for e in result["errors"]))
        return
    if cls == NOT_EVALUATED:
        st.warning(f"**{cls}.** " + " ".join(result["notes"]))
        return
    if not result["breakdown"] and "rolling" not in fac:
        st.html(ui.empty_state("Nothing to evaluate yet",
                               "Enter this year's publications, grants and presentations on the earlier tabs, "
                               "or load one of the example profiles from the sidebar."))
        return
    st.html(ui.result_instrument(result, policy, who))
    st.html(ui.notes_block([d["name"] for d in result["domains"].values() if d["status"] == "Exceeds"],
                           [d["name"] for d in result["domains"].values() if not d["minimum_met"]],
                           result["notes"], result["flags"], policy["domain_exceeds_level"]))

    st.markdown("#### How the points were earned")
    st.caption(f"Meeting a domain's minimum earns {policy['anchor_share']:.0%} of its points. Units above the "
               f"benchmark earn the rest, in proportion, up to the units needed for full excellence credit. "
               f"Adjustment factor for this evaluation: {result['factor']:g}.")
    st.dataframe(pd.DataFrame(exports.conversion_rows(result)[1:], columns=exports.conversion_rows(result)[0]),
                 hide_index=True, width="stretch")
    for key, d in result["domains"].items():
        lines = [line for line in result["breakdown"] if line["domain"] == key]
        with st.expander(f"{d['name']}: {len(lines)} line(s), {d['units']:.2f} units"):
            if lines:
                st.dataframe(pd.DataFrame([{"Item": line["item"], "How it was credited": line["detail"],
                                            "Units": round(line["units"], 3),
                                            "Counts toward minimum": line["toward_minimum"] or ""}
                                           for line in lines]), hide_index=True, width="stretch")
            else:
                st.write("No activity entered.")

    context = {label: info[key] for key, label in CONTEXT_LABELS.items()}
    if any(context.values()):
        st.markdown("#### Recorded, not scored")
        for label, text in context.items():
            if text:
                st.markdown(f"**{label}**  \n{text}")

    st.caption(f"Scoring policy: {exports.policy_stamp(result, meta).replace(' | ', ', ')}. {exports.DISCLAIMER}")
    a, b, c = st.columns(3)
    if a.button("Save evaluation", type="primary", width="stretch"):
        if not (info["name"] or info["faculty_id"]):
            st.error("Enter a faculty name or ID on the Faculty tab before saving.")
        else:
            name = storage.save_evaluation({"form": form, "result": result, "policy": result["policy"],
                                            "policy_version": meta["version"]})
            st.session_state["loaded_stamp"] = result["policy"]["fingerprint"]
            st.success(f"Saved as {name}. Reopen it from the sidebar.")
    file_stub = f"research_evaluation_{storage.slug(info['faculty_id'] or info['name'])}_{info['evaluation_year']}"
    b.download_button("Download report (PDF)", exports.pdf_bytes(info, result, meta, context),
                      f"{file_stub}.pdf", "application/pdf", width="stretch")
    c.download_button("Download report (Excel)", exports.excel_bytes(info, result, policy, meta, context),
                      f"{file_stub}.xlsx",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")


# ------------------------------------------------------------------------------- scoring policy
def _get(policy: dict, path: str):
    node = policy
    for part in path.split("."):
        node = node[part]
    return node


def _set(policy: dict, path: str, value) -> None:
    *parents, leaf = path.split(".")
    node = policy
    for part in parents:
        node = node[part]
    node[leaf] = value


def policy_widget(path: str, label: str, kind, base: dict, locked: bool):
    key = f"pol_{st.session_state['pol_rev']}_{path}"
    value = _get(base, path)
    if kind == "bool":
        return st.checkbox(label, value=bool(value), key=key, disabled=locked)
    if kind == "num":
        return st.number_input(label, value=float(value), key=key, disabled=locked, format="%g")
    if kind == "int":
        return st.number_input(label, value=int(value), min_value=1, step=1, key=key, disabled=locked)
    if kind == "optnum":
        return st.number_input(label, value=None if value is None else float(value), key=key, disabled=locked,
                               format="%g")
    if isinstance(kind, tuple):
        return st.multiselect(label, kind[1], default=list(value), key=key, disabled=locked)
    return st.selectbox(label, kind, index=kind.index(value), key=key, disabled=locked,
                        format_func=lambda v: OPTION_LABELS.get(v, str(v)))


def impact_preview(old: dict, new: dict) -> pd.DataFrame:
    rows = []
    profiles = [(s["name"], lambda p, s=s: s) for s in SCENARIOS]
    for name in storage.list_evaluations():
        f = storage.load_evaluation(name)["form"]
        profiles.append((f"Saved: {name}", lambda p, f=f: forms.build_faculty(
            f["info"], f["pubs"], f["grants"], f["pres"], f["editorial"], f["reviews"], p)[0]))
    for name, build in profiles:
        before, after = evaluate(build(old), old), evaluate(build(new), new)
        rows.append({"Profile": name, "Score now": before["total"], "Score after": after["total"],
                     "Class now": before["class"], "Class after": after["class"],
                     "Reclassified": "Yes" if before["class"] != after["class"] else ""})
    return pd.DataFrame(rows)


def tab_policy() -> None:
    state = st.session_state["policy_state"]
    saved, meta = state["policy"], state["meta"]
    locked = meta["locked"]
    st.subheader("Scoring policy")
    st.write("The thresholds and criteria below belong to the annual review committee. They are set once per "
             "evaluation year, approved, and locked, so that every faculty member is rated under the same rules. "
             "Every report carries the policy version and fingerprint.")
    if locked:
        st.success(f"Locked policy: version {meta['version']}, evaluation year {meta['evaluation_year'] or 'not set'}, "
                   f"approved by {meta['approved_by'] or 'not recorded'} on {meta['saved_at']}. Settings are read-only.")
        with st.expander("Unlock for editing"):
            who = st.text_input("Your name", key="unlock_who")
            reason = st.text_area("Reason for reopening the policy", key="unlock_reason")
            if st.button("Unlock", disabled=not (who.strip() and reason.strip())):
                st.session_state["policy_state"] = storage.unlock_policy(state, who=who.strip(), reason=reason.strip())
                st.rerun()
    else:
        st.warning("This policy is not locked. Its values are provisional defaults until the committee approves them.")
        a, b = st.columns([3, 1])
        preset = a.selectbox("Load a preset into the editor", list(PRESETS), index=None,
                             placeholder="Choose a preset", label_visibility="collapsed")
        if b.button("Load preset", disabled=preset is None, width="stretch"):
            st.session_state["draft_base"] = normalise(PRESETS[preset])
            st.session_state["pol_rev"] += 1
            st.rerun()

    base = st.session_state["draft_base"]
    draft = copy.deepcopy(base)
    draft["policy_name"] = st.text_input("Policy name", value=base["policy_name"], disabled=locked,
                                         key=f"pol_{st.session_state['pol_rev']}_name")
    for title, expanded, fields in POLICY_GROUPS:
        with st.expander(title, expanded=expanded):
            cols = st.columns(2)
            for i, (path, label, kind) in enumerate(fields):
                with cols[i % 2]:
                    _set(draft, path, policy_widget(path, label, kind, base, locked))
    with st.expander("Unit values and multipliers"):
        cols = st.columns(2)
        for i, (name, label) in enumerate(POLICY_TABLES):
            with cols[i % 2]:
                st.markdown(f"**{label}**")
                frame = pd.DataFrame({"Item": [str(k) for k in base[name]],
                                      "Value": [float(v) for v in base[name].values()]})
                edited = st.data_editor(frame, key=f"pol_{st.session_state['pol_rev']}_{name}", hide_index=True,
                                        disabled=["Item"] if not locked else True, width="stretch",
                                        column_config={"Value": st.column_config.NumberColumn(format="%g")})
                draft[name] = {k: float(v) for k, v in zip(edited["Item"], edited["Value"])}
    draft = normalise(draft)
    draft["pub_min_count"] = int(draft["pub_min_count"])

    errors, warnings = check_policy(draft)
    changes = diff(saved, draft)
    st.markdown("#### Check and preview")
    st.write(f"Fingerprint of the settings shown: `{fingerprint(draft)}`. Meeting every minimum earns "
             f"{minimum_score(draft):g} points under these settings.")
    for e in errors:
        st.error(e)
    for w in warnings:
        st.warning(w)
    if changes:
        st.markdown(f"**{len(changes)} setting(s) differ from the saved policy**")
        st.dataframe(pd.DataFrame(changes, columns=["Setting", "Saved value", "New value"]).astype(str),
                     hide_index=True, width="stretch")
    else:
        st.write("No differences from the saved policy.")
    if not errors and changes:
        preview = impact_preview(saved, draft)
        moved = int((preview["Reclassified"] == "Yes").sum())
        st.markdown(f"**Effect on the 22 test profiles and saved evaluations: {moved} reclassified**")
        st.dataframe(preview, hide_index=True, width="stretch")

    if not locked:
        st.markdown("#### Approve and lock")
        a, b = st.columns(2)
        who = a.text_input("Approved by (name and role)", key="approve_who")
        year = b.text_input("Evaluation year this policy applies to", value=str(date.today().year), key="approve_year")
        note = st.text_input("Note for the change log (for example, the committee meeting date)", key="approve_note")
        a, b = st.columns(2)
        if a.button("Save and lock policy", type="primary", disabled=bool(errors) or not who.strip(), width="stretch"):
            st.session_state["policy_state"] = storage.save_policy(state, draft, who=who.strip(), year=year.strip(),
                                                                  note=note.strip(), lock=True)
            st.session_state["draft_base"] = copy.deepcopy(draft)
            st.rerun()
        if b.button("Save as working draft (not locked)", disabled=bool(errors) or not changes, width="stretch"):
            st.session_state["policy_state"] = storage.save_policy(state, draft, who=who.strip() or "not recorded",
                                                                  year=year.strip(), note=note.strip(), lock=False)
            st.session_state["draft_base"] = copy.deepcopy(draft)
            st.rerun()
    st.download_button("Download the saved policy (JSON)", to_json(saved), "scoring_policy.json", "application/json")
    log = storage.read_log()
    with st.expander(f"Change log ({len(log)} entries)"):
        if log:
            st.dataframe(pd.DataFrame([{"When": e["when"], "Who": e["who"], "Action": e["action"],
                                        "Version": e["version"], "Fingerprint": e["fingerprint"],
                                        "Settings changed": len(e["changes"]), "Note": e["note"]} for e in log]),
                         hide_index=True, width="stretch")
        else:
            st.write("No changes recorded yet.")


def tab_guide() -> None:
    policy = active_policy()
    st.subheader("How the evaluation works")
    st.markdown(f"""
- **Three domains.** Publications ({policy['weights']['P']:g} points), grants and contracts
  ({policy['weights']['G']:g}) and presentations ({policy['weights']['R']:g}).
- **Minimums first.** Each domain has a minimum expectation. Meeting it earns {policy['anchor_share']:.0%} of the
  domain's points; work above the minimum earns the rest.
- **Classification.** Any unmet minimum gives *Does Not Meet Expectations*. With all minimums met the result is
  *Meets Expectations*, or *Exceeds Expectations* under the rule shown on the Scoring policy tab
  (threshold {policy['exceeds_threshold']:g}).
- **This tool is a decision aid.** It does not replace the chair's written evaluation or the faculty member's
  narrative on quality, impact and value.

**Journal tiers.** {JOURNAL_TIER_HELP}

**Venue tiers.** {VENUE_TIER_HELP}
""")
    if POLICY_NOTE.exists():
        with st.expander("Provisional policy note: every threshold and criterion applied, with sources"):
            st.markdown(POLICY_NOTE.read_text(encoding="utf-8"))


def main() -> None:
    st.set_page_config(page_title="Faculty Research Evaluation", page_icon=":material/school:", layout="wide")
    init_state()
    st.html(ui.CSS)
    sidebar()
    st.html(ui.masthead(st.session_state["info_name"], st.session_state["info_faculty_id"],
                        st.session_state["info_evaluation_year"]))
    tabs = st.tabs(["Faculty", "Publications", "Grants", "Presentations", "Other activity", "Results",
                    "Scoring policy", "Guide"])
    with tabs[0]:
        tab_info()
    with tabs[1]:
        pubs = tab_pubs()
    with tabs[2]:
        grants = tab_grants()
    with tabs[3]:
        pres = tab_pres()
    with tabs[4]:
        editorial, reviews = tab_other()
    form = {"info": current_info(), "pubs": table_records(pubs), "grants": table_records(grants),
            "pres": table_records(pres), "editorial": table_records(editorial), "reviews": table_records(reviews)}
    with tabs[5]:
        tab_results(form)
    with tabs[6]:
        tab_policy()
    with tabs[7]:
        tab_guide()


main()
