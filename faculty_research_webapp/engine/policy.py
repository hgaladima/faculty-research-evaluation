"""
Scoring policies for the faculty research evaluation engine.

A policy is a plain dict holding every number and rule switch the engine uses.
Two presets ship:

  LEGACY       the Phase 1 rules, unchanged. Reproduces the original results exactly.
  PROVISIONAL  the default. Interim rules pending a decision by the annual review
               committee; each difference from LEGACY is recorded in PROVISIONAL_POLICY.md.

Nothing here is established policy until the committee adopts it.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math

GRANT_ROLES = ["PI", "MPI", "Co-PI", "Co-I", "collaborator", "consultant"]
SUBSTANTIVE_ROLES = ["PI", "MPI", "Co-PI", "Co-I"]
PRES_ROLES = ["presenter", "mentor", "coauthor"]
EXCEEDS_RULES = ["total", "breadth", "total_or_distinction", "breadth_or_distinction"]
REDUCED_RULES = ["waive_below_threshold", "documented_activity"]
ROLLING_BENCHMARKS = ["current_year", "standard_prior_years"]
ROUNDING_MODES = ["bankers", "half_up"]

LEGACY = {
    "policy_name": "Phase 1 original",
    # ---- Weights and classification ----
    "weights": {"P": 50.0, "G": 35.0, "R": 15.0},
    "anchor_share": 0.70,
    "saturation": {"P": 4.0, "G": 4.0, "R": 4.0},
    "benchmark_units": {"P": 2.0, "G": 1.0, "R": 1.0},
    "pub_min_count": 2,
    "exceeds_threshold": 85.0,
    "meets_threshold": 70.0,
    "enforce_meets_threshold": False,
    "approaching_threshold": 60.0,
    "exceeds_rule": "total_or_distinction",
    "breadth_level": 0.80,
    "distinction_min_total": 0.0,
    "domain_exceeds_level": 0.85,
    # ---- Adjustments ----
    "standard_research_effort": 40.0,
    "factor_min": 0.25,
    "factor_max": 1.5,
    "evaluate_zero_assignment": True,
    "reduced_assignment_rule": "waive_below_threshold",
    "reduced_assignment_factor": 0.5,
    "rolling_max_domains": 3,
    "rolling_benchmark": "current_year",
    # ---- Minimum expectations ----
    "grant_gate_requires_external": False,
    "award_gate_roles": list(GRANT_ROLES),
    "pres_gate_roles": list(PRES_ROLES),
    # ---- Publications ----
    "journal_tier_mult": {1: 1.50, 2: 1.25, 3: 1.00, 0: 0.0},
    "author_role_mult": {"lead": 1.00, "coauthor": 0.70},
    "student_mentee_increment": 0.25,
    "book_units": 3.0,
    "book_coauthor_mult": 0.7,
    "chapter_units": 0.75,
    "chapter_cap": None,
    "other_output_units": {"edited_book": 1.0, "technical_report": 0.5, "policy_brief": 0.5,
                           "software": 0.75, "dataset": 0.75, "editorial": 0.4,
                           "book_review": 0.2, "non_peer_reviewed_article": 0.4},
    "other_output_cap": 2.0,
    "editorial_units": {"editor": 1.0, "associate_editor": 0.75, "guest_editor": 0.5,
                        "editorial_board": 0.5, "manuscript_review": 0.1},
    "editorial_cap": 1.0,
    "impact_units": 0.5,
    "impact_cap": 1.0,
    "dedupe_doi": False,
    # ---- Grants ----
    "amount_bands": {"minor_max": 10_000, "large_min": 250_000},
    "submission_base": {"internal": 0.4, "minor": 0.5, "major": 1.0, "large": 1.5},
    "award_base": {"internal": 0.75, "minor": 1.0, "major": 2.0, "large": 3.0},
    "grant_role_mult": {"PI": 1.0, "MPI": 1.0, "Co-PI": 0.8, "Co-I": 0.5,
                        "collaborator": 0.25, "consultant": 0.25},
    "noncompetitive_mult": 0.5,
    "noncompetitive_award_mult": 0.75,
    "scored_bonus": 0.25,
    "submission_cap": 2.5,
    "implementation_units": 0.5,
    "implementation_cap": 1.0,
    "grant_review_units": {"federal_panel": 0.75, "other_panel": 0.4},
    "grant_review_cap": 0.75,
    "development_units": 0.25,
    "development_cap": 0.75,
    "dedupe_submission_award": False,
    # ---- Presentations ----
    "pres_type_base": {"keynote": 2.0, "plenary": 2.0, "invited": 1.25, "oral": 1.0,
                       "panel": 0.75, "workshop": 0.75, "poster": 0.6,
                       "institutional": 0.3, "outreach": 0.3, "seminar": 0.2},
    "venue_tier_mult": {"A": 1.25, "B": 1.0, "C": 0.6, "0": 0.0},
    "pres_role_mult": {"presenter": 1.0, "mentor": 0.5, "coauthor": 0.4},
    "chair_units": 0.3,
    "chair_cap": 0.6,
    "local_cap": 1.0,
    # ---- Missing data and rounding ----
    "missing_defaults": {"venue": "B", "pres_role": "presenter", "book_role": "lead"},
    "rounding": "bankers",
    "total_from_rounded_parts": False,
}


def _provisional() -> dict:
    p = copy.deepcopy(LEGACY)
    p.update({
        "policy_name": "Provisional 2026 (pending committee approval)",
        "enforce_meets_threshold": True,
        "exceeds_rule": "breadth_or_distinction",
        "distinction_min_total": 80.0,
        "evaluate_zero_assignment": False,
        "reduced_assignment_rule": "documented_activity",
        "rolling_max_domains": 1,
        "rolling_benchmark": "standard_prior_years",
        "award_gate_roles": list(SUBSTANTIVE_ROLES),
        "pres_gate_roles": ["presenter", "mentor"],
        "chapter_cap": 2.25,
        "dedupe_doi": True,
        "dedupe_submission_award": True,
        "missing_defaults": {"venue": "C", "pres_role": "coauthor", "book_role": "coauthor"},
        "rounding": "half_up",
        "total_from_rounded_parts": True,
    })
    p["author_role_mult"] = {"lead": 1.00, "second": 0.85, "coauthor": 0.70}
    p["other_output_units"].update({"published_abstract": 0.2, "non_peer_reviewed_book": 1.0,
                                    "non_peer_reviewed_chapter": 0.4})
    return p


PROVISIONAL = _provisional()
PRESETS = {"Provisional 2026": PROVISIONAL, "Phase 1 original": LEGACY}

TIER_KEYS = [1, 2, 3, 0]


def normalise(policy: dict) -> dict:
    """Return a copy with journal-tier keys as ints (JSON turns them into strings)."""
    p = copy.deepcopy(policy)
    p["journal_tier_mult"] = {int(k): float(v) for k, v in p["journal_tier_mult"].items()}
    return p


def to_json(policy: dict) -> str:
    return json.dumps(policy, indent=2, sort_keys=True, default=str)


def from_json(text: str) -> dict:
    return normalise(json.loads(text))


def fingerprint(policy: dict) -> str:
    """Short, stable identifier of the settings; printed on every report."""
    def canon(v):
        if isinstance(v, dict):
            return {str(k): canon(x) for k, x in v.items()}
        if isinstance(v, list):
            return [canon(x) for x in v]
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        return v

    canonical = json.dumps(canon(normalise(policy)), sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:10]


def minimum_score(policy: dict) -> float:
    """Score of a faculty member who meets every minimum and earns no excellence credit."""
    return policy["anchor_share"] * sum(policy["weights"].values())


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _mistyped(policy: dict) -> list[str]:
    """Settings whose value is blank or of the wrong kind, judged against the Phase 1 preset."""
    bad = []
    for key, ref in LEGACY.items():
        value = policy[key]
        if key == "chapter_cap":
            ok = value is None or _is_number(value)
        elif isinstance(ref, bool):
            ok = isinstance(value, bool)
        elif isinstance(ref, (int, float)):
            ok = _is_number(value)
        elif isinstance(ref, str):
            ok = isinstance(value, str) and bool(value.strip())
        elif isinstance(ref, list):
            ok = isinstance(value, list)
        else:
            ok = isinstance(value, dict)
            if ok:
                numeric = all(isinstance(x, (int, float)) for x in ref.values())
                bad += [f"{key}.{sub}" for sub, x in value.items()
                        if not (_is_number(x) if numeric else isinstance(x, str))]
        if not ok:
            bad.append(key)
    return bad


def check_policy(policy: dict) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). A policy with errors must not be saved."""
    errors, warnings = [], []
    if not isinstance(policy, dict):
        return ["The policy is not in the expected format."], []
    missing = [k for k in LEGACY if k not in policy]
    if missing:
        return [f"Missing settings: {', '.join(sorted(missing))}"], []
    mistyped = _mistyped(policy)
    if mistyped:
        return [f"These settings are blank or not valid: {', '.join(mistyped)}. Enter a value for each."], []

    w = policy["weights"]
    if any(v < 0 for v in w.values()):
        errors.append("Domain weights cannot be negative.")
    if abs(sum(w.values()) - 100.0) > 1e-6:
        errors.append(f"Domain weights must sum to 100 (they sum to {sum(w.values()):g}).")
    if not 0 < policy["anchor_share"] < 1:
        errors.append("The share of points earned at the minimum must be between 0 and 1.")
    if policy["meets_threshold"] >= policy["exceeds_threshold"]:
        errors.append("The Exceeds threshold must be higher than the Meets threshold.")
    if not 0 <= policy["approaching_threshold"] <= policy["meets_threshold"]:
        errors.append("The Approaching threshold must lie between 0 and the Meets threshold.")
    if not 0 < policy["exceeds_threshold"] <= 100:
        errors.append("The Exceeds threshold must be between 0 and 100.")
    for name in ("breadth_level", "domain_exceeds_level"):
        if not 0 < policy[name] <= 1:
            errors.append(f"{name} must be between 0 and 1.")
    if not 0 <= policy["distinction_min_total"] <= 100:
        errors.append("The floor score for the large-award route must be between 0 and 100.")
    if policy["pub_min_count"] < 1 or int(policy["pub_min_count"]) != policy["pub_min_count"]:
        errors.append("The publication minimum must be a whole number of at least 1.")
    if not 0 < policy["standard_research_effort"] <= 100:
        errors.append("Standard research effort must be between 0 and 100 percent.")
    if not 0 < policy["factor_min"] <= 1 <= policy["factor_max"]:
        errors.append("The adjustment factor range must satisfy 0 < minimum <= 1 <= maximum.")
    if not 0 < policy["reduced_assignment_factor"] <= 1:
        errors.append("The reduced-assignment factor must be between 0 and 1.")
    if policy["rolling_max_domains"] not in (0, 1, 2, 3):
        errors.append("The rolling window may rescue 0, 1, 2 or 3 domains.")
    for name, allowed in (("exceeds_rule", EXCEEDS_RULES), ("reduced_assignment_rule", REDUCED_RULES),
                          ("rolling_benchmark", ROLLING_BENCHMARKS), ("rounding", ROUNDING_MODES)):
        if policy[name] not in allowed:
            errors.append(f"{name} must be one of: {', '.join(allowed)}.")
    for d in ("P", "G", "R"):
        if policy["saturation"][d] <= 0:
            errors.append(f"Saturation for domain {d} must be greater than 0.")
        if policy["benchmark_units"][d] < 0:
            errors.append(f"Benchmark units for domain {d} cannot be negative.")
    if set(int(k) for k in policy["journal_tier_mult"]) != set(TIER_KEYS):
        errors.append("Journal tier multipliers must be given for tiers 1, 2, 3 and 0.")
    for required, table in (({"lead", "coauthor"}, "author_role_mult"),
                            (set(GRANT_ROLES), "grant_role_mult"),
                            (set(PRES_ROLES), "pres_role_mult"),
                            ({"internal", "minor", "major", "large"}, "submission_base"),
                            ({"internal", "minor", "major", "large"}, "award_base"),
                            ({"A", "B", "C", "0"}, "venue_tier_mult")):
        absent = required - set(policy[table])
        if absent:
            errors.append(f"{table} is missing: {', '.join(sorted(absent))}.")
    for table in ("journal_tier_mult", "author_role_mult", "other_output_units", "editorial_units",
                  "submission_base", "award_base", "grant_role_mult", "grant_review_units",
                  "pres_type_base", "venue_tier_mult", "pres_role_mult"):
        if any(float(v) < 0 for v in policy[table].values()):
            errors.append(f"{table} cannot contain negative values.")
    for name in ("other_output_cap", "editorial_cap", "impact_cap", "submission_cap", "implementation_cap",
                 "grant_review_cap", "development_cap", "chair_cap", "local_cap", "student_mentee_increment",
                 "book_units", "chapter_units", "impact_units", "scored_bonus", "implementation_units",
                 "development_units", "chair_units", "noncompetitive_mult", "noncompetitive_award_mult",
                 "book_coauthor_mult"):
        if policy[name] < 0:
            errors.append(f"{name} cannot be negative.")
    if policy["chapter_cap"] is not None and policy["chapter_cap"] < 0:
        errors.append("chapter_cap cannot be negative.")
    bands = policy["amount_bands"]
    if not 0 < bands["minor_max"] < bands["large_min"]:
        errors.append("Award size bands must satisfy 0 < minor ceiling < large floor.")
    if not set(policy["award_gate_roles"]) <= set(GRANT_ROLES):
        errors.append("award_gate_roles contains an unknown grant role.")
    if not set(policy["pres_gate_roles"]) <= set(PRES_ROLES) or not policy["pres_gate_roles"]:
        errors.append("pres_gate_roles must list at least one known presentation role.")
    md = policy["missing_defaults"]
    if md.get("venue") not in policy["venue_tier_mult"] or md.get("pres_role") not in policy["pres_role_mult"] \
            or md.get("book_role") not in policy["author_role_mult"]:
        errors.append("missing_defaults refers to an unknown venue tier or role.")

    if not errors:
        floor = minimum_score(policy)
        if policy["enforce_meets_threshold"] and floor < policy["meets_threshold"] - 1e-9:
            warnings.append(
                f"A faculty member who meets every minimum scores {floor:g}, below the Meets threshold of "
                f"{policy['meets_threshold']:g}. Meeting all minimums would not be enough for Meets Expectations.")
        if not policy["enforce_meets_threshold"] and abs(floor - policy["meets_threshold"]) > 1e-9:
            warnings.append(
                f"Meeting every minimum yields {floor:g}, which differs from the Meets threshold of "
                f"{policy['meets_threshold']:g}; the threshold is not enforced, so the minimums alone decide Meets.")
        if policy["exceeds_threshold"] <= floor:
            warnings.append("The Exceeds threshold is not above the score earned by meeting the minimums.")
    return errors, warnings


def diff(old: dict, new: dict) -> list[tuple[str, object, object]]:
    """List (setting, old value, new value) for every leaf value that differs."""
    out = []
    old, new = normalise(old), normalise(new)
    for key in sorted(set(old) | set(new)):
        a, b = old.get(key), new.get(key)
        if isinstance(a, dict) and isinstance(b, dict):
            for sub in sorted(set(a) | set(b), key=str):
                if a.get(sub) != b.get(sub):
                    out.append((f"{key}.{sub}", a.get(sub), b.get(sub)))
        elif a != b:
            out.append((key, a, b))
    return out
