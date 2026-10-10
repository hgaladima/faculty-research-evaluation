"""
Faculty Research & Scholarship Evaluation Algorithm.

Anchor-and-excellence model:
  * Each required domain (Publications, Grants, Presentations) has a minimum-expectation
    "gate". Meeting the gate earns the domain's ANCHOR (a fixed share of its maximum).
  * Quality-weighted scholarly "units" above the domain benchmark earn EXCELLENCE points
    (the remaining share), rising linearly to a saturation cap.
  * Classification uses both the score and the gates, so excellence in one domain cannot
    mask an unmet minimum in another.

Every number and rule switch lives in the policy dict (see policy.py). Same inputs and the
same policy give the same outputs.
"""
from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

from .policy import PROVISIONAL, SUBSTANTIVE_ROLES, fingerprint, normalise

GATE_TYPES_PRES = {"keynote", "plenary", "invited", "oral", "panel", "workshop", "poster"}
LOCAL_TYPES_PRES = {"institutional", "outreach", "seminar"}
DOMAIN_NAMES = {"P": "Publications", "G": "Grants and contracts", "R": "Presentations"}

EXCEEDS = "Exceeds Expectations"
MEETS = "Meets Expectations"
DOES_NOT_MEET = "Does Not Meet Expectations"
NOT_EVALUATED = "Not Evaluated"
INCOMPLETE = "Incomplete: input errors"

COUNT_FIELDS = ("sessions_chaired", "proposals_in_development", "unfunded_projects",
                "manuscripts_under_review", "abstracts_submitted")
ROLLING_FIELDS = ("pubs_prior2", "grant_active_years_prior2", "pres_prior2")


LIST_FIELDS = ("publications", "submissions", "awards", "active_projects", "presentations", "editorial")
YES_NO_FIELDS = {"publications": ("peer_reviewed", "student_first", "counted_in_prior_year"),
                 "submissions": ("competitive", "scored"),
                 "awards": ("competitive", "scored", "counted_in_prior_year")}
DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:")


def _round1(x: float, cfg: dict) -> float:
    if cfg["rounding"] == "half_up":
        # Rounding to 9 places first removes binary noise: an exact 46.85 is held as 46.849999999999994.
        return float(Decimal(repr(round(float(x), 9))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    return round(x, 1)


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _known(value, table) -> bool:
    return isinstance(value, (str, int)) and not isinstance(value, bool) and value in table


def _label(item: dict, kind: str, i: int) -> str:
    title = item.get("title")
    title = title.strip() if isinstance(title, str) else ""
    return f"{kind} {i + 1}" + (f" ({title})" if title else "")


def _unique(seq: list[str]) -> list[str]:
    return list(dict.fromkeys(seq))


# ----------------------------------------------------------------------------------------
# Validation (always run before scoring; any error stops the evaluation)
# ----------------------------------------------------------------------------------------
def _structure_errors(fac) -> list[str]:
    if not isinstance(fac, dict):
        return ["The faculty record is not in the expected format."]
    errs = []
    for key in LIST_FIELDS:
        items = fac.get(key, [])
        if not isinstance(items, list) or not all(isinstance(x, dict) for x in items):
            errs.append(f"'{key}' must be a list of entries.")
    if not isinstance(fac.get("grant_reviews", []), list):
        errs.append("'grant_reviews' must be a list.")
    if not isinstance(fac.get("rolling", {}), dict):
        errs.append("'rolling' must hold the rolling-window figures.")
    return errs


def _entry_errors(item: dict, lab: str, yes_no: tuple) -> list[str]:
    errs = []
    for field in ("title", "doi"):
        if item.get(field) is not None and not isinstance(item[field], str):
            errs.append(f"{lab}: {field} must be text.")
    if item.get("id") is not None and not (isinstance(item["id"], str) or _is_int(item["id"])):
        errs.append(f"{lab}: id must be text or a whole number.")
    for field in yes_no:
        if field in item and not isinstance(item[field], bool):
            errs.append(f"{lab}: '{field.replace('_', ' ')}' must be yes or no (true or false), "
                        f"not {item[field]!r}.")
    return errs


def validate(fac: dict, cfg: dict = PROVISIONAL) -> list[str]:
    errs = _structure_errors(fac)
    if errs:
        return errs
    effort = fac.get("research_effort", cfg["standard_research_effort"])
    if not _is_num(effort) or not 0 <= effort <= 100:
        errs.append("Research effort must be a number from 0 to 100 percent.")
    months = fac.get("months_active", 12)
    if not _is_num(months) or not 0 <= months <= 12:
        errs.append("Months active must be a number from 0 to 12.")
    if not isinstance(fac.get("first_year", False), bool):
        errs.append(f"'First year' must be yes or no (true or false), not {fac['first_year']!r}.")
    for name in COUNT_FIELDS:
        v = fac.get(name, 0)
        if not _is_int(v) or v < 0:
            errs.append(f"{name.replace('_', ' ').capitalize()} must be a whole number, 0 or more.")
    for name in ROLLING_FIELDS:
        v = fac.get("rolling", {}).get(name)
        if v is not None and (not _is_int(v) or v < 0):
            errs.append(f"Rolling-window figure '{name}' must be a whole number, 0 or more.")

    for i, p in enumerate(fac.get("publications", [])):
        lab = _label(p, "Publication", i)
        errs += _entry_errors(p, lab, YES_NO_FIELDS["publications"])
        t = p.get("type", "article")
        if not isinstance(t, str) or not t:
            errs.append(f"{lab}: publication type is missing.")
            continue
        if t == "article" and p.get("peer_reviewed", True) is True:
            tier = p.get("tier")
            if tier is not None and not (_is_int(tier) and tier in cfg["journal_tier_mult"]):
                errs.append(f"{lab}: journal tier must be 1, 2, 3 or 0 (got {tier!r}).")
        if t in ("article", "book") and p.get("role") is not None and not _known(p["role"], cfg["author_role_mult"]):
            errs.append(f"{lab}: author role {p['role']!r} is not recognised "
                        f"(use {', '.join(cfg['author_role_mult'])}).")
        impacts = p.get("documented_impacts", 0)
        if not _is_int(impacts) or impacts < 0:
            errs.append(f"{lab}: documented impacts must be a whole number, 0 or more.")

    bands = cfg["amount_bands"]
    for kind, key in (("Submission", "submissions"), ("Award", "awards")):
        for i, s in enumerate(fac.get(key, [])):
            lab = _label(s, kind, i)
            errs += _entry_errors(s, lab, YES_NO_FIELDS[key])
            size = s.get("size")
            sized = _known(size, cfg["submission_base"]) and _known(size, cfg["award_base"])
            if not sized:
                errs.append(f"{lab}: size band must be one of {', '.join(cfg['submission_base'])} (got {size!r}).")
            if s.get("role") is not None and not _known(s["role"], cfg["grant_role_mult"]):
                errs.append(f"{lab}: role {s['role']!r} is not recognised.")
            amt = s.get("amount")
            if amt is not None:
                if not _is_num(amt) or amt < 0:
                    errs.append(f"{lab}: amount must be a number, 0 or more.")
                elif sized and size != "internal":
                    band = "minor" if amt < bands["minor_max"] else "major" if amt < bands["large_min"] else "large"
                    if size != band:
                        errs.append(f"{lab}: amount ${amt:,.0f} is inconsistent with size band '{size}' "
                                    f"(expected '{band}').")
    for i, p in enumerate(fac.get("active_projects", [])):
        lab = _label(p, "Active project", i)
        errs += _entry_errors(p, lab, ())
        if p.get("role") is not None and not _known(p["role"], cfg["grant_role_mult"]):
            errs.append(f"{lab}: role {p['role']!r} is not recognised.")
    for r in fac.get("grant_reviews", []):
        if not _known(r, cfg["grant_review_units"]):
            errs.append(f"Grant review type {r!r} is not recognised.")
    for i, e in enumerate(fac.get("editorial", [])):
        if not _known(e.get("role"), cfg["editorial_units"]):
            errs.append(f"Editorial activity {i + 1}: role {e.get('role')!r} is not recognised.")
        n = e.get("n", 1)
        if not _is_int(n) or n < 0:
            errs.append(f"Editorial activity {i + 1}: count must be a whole number, 0 or more.")
    for i, p in enumerate(fac.get("presentations", [])):
        lab = _label(p, "Presentation", i)
        errs += _entry_errors(p, lab, ())
        t = p.get("type")
        if not _known(t, cfg["pres_type_base"]):
            errs.append(f"{lab}: presentation type {t!r} is not recognised.")
            continue
        if p.get("role") is not None and not _known(p["role"], cfg["pres_role_mult"]):
            errs.append(f"{lab}: role {p['role']!r} is not recognised.")
        venue = p.get("venue")
        if t not in LOCAL_TYPES_PRES and venue is not None and not (isinstance(venue, str)
                                                                    and venue in cfg["venue_tier_mult"]):
            errs.append(f"{lab}: venue tier must be A, B, C or 0, entered as text (got {venue!r}).")
    return errs


# ----------------------------------------------------------------------------------------
# Adjustment factor
# ----------------------------------------------------------------------------------------
def adjustment_factor(f: dict, cfg: dict) -> float:
    """(assigned research effort / standard) x (months active / 12), bounded by the policy."""
    effort = f.get("research_effort", cfg["standard_research_effort"])
    months = f.get("months_active", 12)
    raw = (effort / cfg["standard_research_effort"]) * (months / 12.0)
    return max(cfg["factor_min"], min(cfg["factor_max"], raw))


def pub_benchmark_count(fac: float, first_year: bool, cfg: dict) -> int:
    b = cfg["pub_min_count"] * fac * (0.5 if first_year else 1.0)
    return max(1, math.floor(b + 0.5))


# ----------------------------------------------------------------------------------------
# Domain unit calculators
# ----------------------------------------------------------------------------------------
def _doi(item: dict, cfg: dict) -> str:
    doi = (item.get("doi") or "").strip().lower()
    if cfg["normalise_ids"]:
        for prefix in DOI_PREFIXES:
            if doi.startswith(prefix):
                doi = doi[len(prefix):]
    return doi


def _prior_year(item: dict, cfg: dict) -> bool:
    return bool(cfg["honour_prior_year_publications"] and item.get("counted_in_prior_year"))


def _expected_units(item: dict, cfg: dict) -> float:
    """Units an entry would earn on its own; used only to choose which copy of a duplicate DOI to keep."""
    if _prior_year(item, cfg):
        return -1.0
    t, peer = item.get("type", "article"), item.get("peer_reviewed", True)
    if t == "article" and peer:
        tier = 3 if item.get("tier") is None else item["tier"]
        return cfg["journal_tier_mult"][tier] * cfg["author_role_mult"][item.get("role") or "coauthor"]
    if t == "book" and peer:
        role = item.get("role") or cfg["missing_defaults"]["book_role"]
        return cfg["book_units"] * (1.0 if role == "lead" else cfg["book_coauthor_mult"])
    if t == "chapter" and peer:
        return cfg["chapter_units"]
    key = f"non_peer_reviewed_{t}" if t in ("article", "book", "chapter") else t
    return cfg["other_output_units"].get(key, 0.0)


def pub_units(fac: dict, cfg: dict) -> dict:
    count, units, chapters, other, editorial, impact, chapters_counted = 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0
    flags, lines = [], []
    kept = {}
    for i, it in enumerate(fac.get("publications", [])):
        doi = _doi(it, cfg)
        if doi and (doi not in kept or _expected_units(it, cfg) >
                    _expected_units(fac["publications"][kept[doi]], cfg)):
            kept[doi] = i

    def line(item, detail, u, minimum=0):
        lines.append({"domain": "P", "item": item, "detail": detail, "units": u, "toward_minimum": minimum})

    for i, it in enumerate(fac.get("publications", [])):
        lab = _label(it, "Publication", i)
        if _prior_year(it, cfg):
            flags.append(f"{lab} already credited in a prior year: excluded")
            line(lab, "Credited in a prior year; excluded", 0.0)
            continue
        doi = _doi(it, cfg)
        if doi and kept[doi] != i:
            if cfg["dedupe_doi"]:
                flags.append(f"{lab}: duplicate DOI {doi}; counted once")
                line(lab, "Duplicate DOI; the entry with the most credit is the one counted", 0.0)
                continue
            flags.append(f"{lab}: duplicate DOI {doi}; counted twice under this policy")
        t = it.get("type", "article")
        peer = it.get("peer_reviewed", True)
        if t == "article":
            if not peer:
                u = cfg["other_output_units"]["non_peer_reviewed_article"]
                other += u
                line(lab, "Article, not peer-reviewed (other scholarly output)", u)
                continue
            tier = it.get("tier")
            if tier is None:
                tier = 3
                flags.append(f"{lab}: journal tier missing; treated as Tier 3 pending verification")
            if tier == 0:
                line(lab, "Article in a venue classified questionable; not credited", 0.0)
                continue
            role = it.get("role")
            if role is None:
                role = "coauthor"
                flags.append(f"{lab}: author role missing; treated as coauthor pending verification")
            u = cfg["journal_tier_mult"][tier] * cfg["author_role_mult"][role]
            detail = f"Peer-reviewed article, Tier {tier}, {role} author"
            if it.get("student_first") and role == "lead":
                u += cfg["student_mentee_increment"]
                detail += ", student or mentee as first author"
            units += u
            count += 1
            line(lab, detail, u, 1)
        elif t == "book" and peer:
            role = it.get("role")
            if role is None:
                role = cfg["missing_defaults"]["book_role"]
                flags.append(f"{lab}: author role missing; treated as {role} pending verification")
            u = cfg["book_units"] * (1.0 if role == "lead" else cfg["book_coauthor_mult"])
            units += u
            count += 2
            line(lab, f"Peer-reviewed scholarly book, {role} author", u, 2)
        elif t == "chapter" and peer:
            u = cfg["chapter_units"]
            if cfg["chapter_cap"] is None:
                units += u
            else:
                chapters += u
            toward = 0
            if chapters_counted < 1:
                count += 1
                chapters_counted += 1
                toward = 1
            line(lab, "Peer-reviewed book chapter", u, toward)
        else:
            key = f"non_peer_reviewed_{t}" if t in ("book", "chapter") else t
            if key in cfg["other_output_units"]:
                u = cfg["other_output_units"][key]
                other += u
                line(lab, f"Other scholarly output: {key.replace('_', ' ')}", u)
            else:
                flags.append(f"{lab}: type '{key.replace('_', ' ')}' is not credited under this policy")
                line(lab, f"Type '{key.replace('_', ' ')}' is not credited under this policy", 0.0)
        n_imp = it.get("documented_impacts", 0)
        if n_imp:
            u = cfg["impact_units"] * n_imp
            impact += u
            line(lab, f"{n_imp} documented impact(s) on policy or practice", u)
    for e in fac.get("editorial", []):
        n = e.get("n", 1)
        u = cfg["editorial_units"][e["role"]] * n
        editorial += u
        line(f"Editorial: {e['role'].replace('_', ' ')}" + (f" x {n}" if n != 1 else ""), "Editorial and peer-review service", u)
    n0 = sum(1 for it in fac.get("publications", [])
             if it.get("type", "article") == "article" and it.get("tier") == 0)
    if n0 >= 3:
        flags.append(f"Committee review: {n0} articles in questionable venues (pattern, not credited)")

    chap_c = min(chapters, cfg["chapter_cap"]) if cfg["chapter_cap"] is not None else 0.0
    other_c = min(other, cfg["other_output_cap"])
    edit_c = min(editorial, cfg["editorial_cap"])
    impact_c = min(impact, cfg["impact_cap"])
    for name, raw, capped in (("Book chapters", chapters, chap_c), ("Other scholarly outputs", other, other_c),
                              ("Editorial service", editorial, edit_c), ("Documented impacts", impact, impact_c)):
        if capped < raw:
            line(f"Cap: {name}", f"Credit limited to {capped:g} units (earned {raw:g})", capped - raw)
    article_units = units + chap_c
    total = article_units + other_c + edit_c + impact_c
    return {"count": count, "article_units": article_units, "other": other_c, "editorial": edit_c,
            "impact": impact_c, "units": total, "flags": flags, "lines": lines}


def grant_units(fac: dict, cfg: dict) -> dict:
    sub_units, units, gate, partial, flags, lines = 0.0, 0.0, False, False, [], []
    distinction = False
    seen = set()

    def line(item, detail, u, minimum=0):
        lines.append({"domain": "G", "item": item, "detail": detail, "units": u, "toward_minimum": minimum})

    def role_of(entry, lab):
        if entry.get("role") is None:
            flags.append(f"{lab}: role missing; treated as collaborator pending verification")
        return entry.get("role") or "collaborator"

    def grant_id(entry):
        """(id, whether the entry has one). Phase 1 compared raw ids and ignored falsy ones such as 0."""
        key = entry.get("id")
        if not cfg["normalise_ids"]:
            return key, bool(key)
        key = None if key is None else str(key).strip().lower()
        return key, bool(key)

    def meets_minimum(entry, role):
        external = entry["size"] != "internal"
        return (role in SUBSTANTIVE_ROLES and entry.get("competitive", True)
                and (external or not cfg["grant_gate_requires_external"]))

    awarded_ids = {grant_id(a)[0] for a in fac.get("awards", [])
                   if grant_id(a)[1] and not a.get("counted_in_prior_year")}
    for i, s in enumerate(fac.get("submissions", [])):
        lab = _label(s, "Submission", i)
        key, has_id = grant_id(s)
        if has_id and key in seen:
            flags.append(f"Duplicate submission id {key}: counted once")
            line(lab, "Duplicate submission id; not counted again", 0.0)
            continue
        seen.add(key)
        if cfg["dedupe_submission_award"] and has_id and key in awarded_ids:
            # The proposal earns its units through the award, but submitting it still shows grant seeking.
            met = meets_minimum(s, s.get("role") or "collaborator")
            gate = gate or met
            flags.append(f"{lab}: funded in the same year; credited as an award only")
            line(lab, "Funded in the same year; credited under the award", 0.0, 1 if met else 0)
            continue
        role = role_of(s, lab)
        base = cfg["submission_base"][s["size"]]
        mult = cfg["grant_role_mult"][role]
        comp = s.get("competitive", True)
        u = base * mult * (1.0 if comp else cfg["noncompetitive_mult"])
        detail = f"Proposal submitted, {s['size']} band, {role}, {'competitive' if comp else 'noncompetitive'}"
        if s.get("scored"):
            u += cfg["scored_bonus"] * mult
            detail += ", scored"
        sub_units += u
        meets = meets_minimum(s, role)
        if meets:
            gate = True
        else:
            partial = True
        line(lab, detail, u, 1 if meets else 0)
    for i, a in enumerate(fac.get("awards", [])):
        lab = _label(a, "Award", i)
        if a.get("counted_in_prior_year"):
            flags.append(f"Award {a.get('id', '?')} already credited in a prior year: excluded")
            line(lab, "Credited in a prior year; excluded", 0.0)
            continue
        role = role_of(a, lab)
        comp = a.get("competitive", True)
        u = cfg["award_base"][a["size"]] * cfg["grant_role_mult"][role]
        if not comp:
            u *= cfg["noncompetitive_award_mult"]
        units += u
        meets = role in cfg["award_gate_roles"]
        if meets:
            gate = True
        else:
            partial = True
        if a["size"] == "large" and role in ("PI", "MPI") and comp:
            distinction = True
        line(lab, f"Award received, {a['size']} band, {role}, {'competitive' if comp else 'noncompetitive'}",
             u, 1 if meets else 0)
    if sub_units > cfg["submission_cap"]:
        flags.append(f"Submission credit capped at {cfg['submission_cap']} units")
        line("Cap: Submissions", f"Credit limited to {cfg['submission_cap']:g} units (earned {sub_units:g})",
             cfg["submission_cap"] - sub_units)
    units += min(sub_units, cfg["submission_cap"])
    impl = 0.0
    for i, p in enumerate(fac.get("active_projects", [])):
        lab = _label(p, "Active project", i)
        if p.get("role") in SUBSTANTIVE_ROLES:
            impl += cfg["implementation_units"]
            gate = True
            line(lab, f"Implementing a funded project as {p['role']}", cfg["implementation_units"], 1)
        elif p.get("role") is None:
            flags.append(f"{lab}: role missing; no credit pending verification")
            line(lab, "Role not yet verified; no credit", 0.0)
        else:
            line(lab, f"Role on the funded project is {p['role']}; no implementation credit", 0.0)
    if impl > cfg["implementation_cap"]:
        line("Cap: Active projects", f"Credit limited to {cfg['implementation_cap']:g} units (earned {impl:g})",
             cfg["implementation_cap"] - impl)
    impl = min(impl, cfg["implementation_cap"])
    review = 0.0
    for r in fac.get("grant_reviews", []):
        review += cfg["grant_review_units"][r]
        line(f"Grant review: {r.replace('_', ' ')}", "Service on a grant review panel", cfg["grant_review_units"][r])
    if review > cfg["grant_review_cap"]:
        line("Cap: Grant review", f"Credit limited to {cfg['grant_review_cap']:g} units (earned {review:g})",
             cfg["grant_review_cap"] - review)
    review = min(review, cfg["grant_review_cap"])
    n_dev = fac.get("proposals_in_development", 0) + fac.get("unfunded_projects", 0)
    dev = cfg["development_units"] * n_dev
    if n_dev:
        line("Proposal development and unfunded projects", f"{n_dev} documented", dev)
    if dev > cfg["development_cap"]:
        line("Cap: Development", f"Credit limited to {cfg['development_cap']:g} units (earned {dev:g})",
             cfg["development_cap"] - dev)
    dev = min(dev, cfg["development_cap"])
    if fac.get("proposals_in_development", 0) > 0 or review > 0:
        partial = True
    total = units + impl + review + dev
    return {"units": total, "core": units, "implementation": impl, "review": review, "development": dev,
            "gate": gate, "distinction": distinction, "partial": partial and not gate, "flags": flags,
            "lines": lines}


def pres_units(fac: dict, cfg: dict) -> dict:
    units, local, gate, partial, flags, lines = 0.0, 0.0, False, False, [], []

    def line(item, detail, u, minimum=0):
        lines.append({"domain": "R", "item": item, "detail": detail, "units": u, "toward_minimum": minimum})

    for i, p in enumerate(fac.get("presentations", [])):
        lab = _label(p, "Presentation", i)
        t = p["type"]
        base = cfg["pres_type_base"][t]
        role_name = p.get("role")
        if role_name is None:
            role_name = cfg["missing_defaults"]["pres_role"]
            flags.append(f"{lab}: role missing; treated as {role_name} pending verification")
        role = cfg["pres_role_mult"][role_name]
        if t in LOCAL_TYPES_PRES:
            local += base * role
            partial = True
            line(lab, f"{t.capitalize()} presentation, {role_name} (local dissemination)", base * role)
            continue
        venue = p.get("venue")
        if venue is None:
            venue = cfg["missing_defaults"]["venue"]
            flags.append(f"{lab}: venue tier missing; treated as Tier {venue} pending verification")
        if venue == "0":
            flags.append("Presentation at a venue classified questionable: not credited")
            line(lab, "Venue classified questionable; not credited", 0.0)
            continue
        u = base * cfg["venue_tier_mult"][venue] * role
        units += u
        meets = t in GATE_TYPES_PRES and role_name in cfg["pres_gate_roles"]
        if meets:
            gate = True
        elif t in GATE_TYPES_PRES:
            partial = True
        line(lab, f"{t.capitalize()} presentation, venue Tier {venue}, {role_name}", u, 1 if meets else 0)
    n_chair = fac.get("sessions_chaired", 0)
    chair_raw = cfg["chair_units"] * n_chair
    chair = min(chair_raw, cfg["chair_cap"])
    if n_chair:
        line("Sessions chaired or organised", f"{n_chair} session(s)", chair_raw)
    if chair < chair_raw:
        line("Cap: Sessions chaired", f"Credit limited to {cfg['chair_cap']:g} units (earned {chair_raw:g})",
             chair - chair_raw)
    if local > cfg["local_cap"]:
        line("Cap: Local dissemination", f"Credit limited to {cfg['local_cap']:g} units (earned {local:g})",
             cfg["local_cap"] - local)
    total = units + min(local, cfg["local_cap"]) + chair
    return {"units": total, "gate": gate, "partial": partial and not gate, "flags": flags, "lines": lines}


# ----------------------------------------------------------------------------------------
# Domain score
# ----------------------------------------------------------------------------------------
def domain_score(weight, anchor_fraction, units, benchmark_units, saturation, cfg):
    anchor = cfg["anchor_share"] * weight * anchor_fraction
    excess = max(0.0, units - benchmark_units)
    excel = (1 - cfg["anchor_share"]) * weight * min(1.0, excess / saturation)
    return anchor + excel, anchor, excel


def _empty_result(fac: dict, cfg: dict, cls: str, errors=None, notes=None) -> dict:
    info = fac if isinstance(fac, dict) else {}
    return {
        "name": info.get("name", ""), "faculty_id": info.get("faculty_id", ""),
        "evaluation_year": info.get("evaluation_year", ""),
        "P": 0.0, "G": 0.0, "R": 0.0, "total": 0.0, "class": cls, "class_basis": "not_scored",
        "gates": {"P": False, "G": False, "R": False}, "gate_basis": {"P": "", "G": "", "R": ""},
        "factor": 0.0, "pub_benchmark": 0, "pub_count": 0, "units": {"P": 0.0, "G": 0.0, "R": 0.0},
        "domains": {}, "breakdown": [], "approaching": False, "scored": False,
        "flags": [], "notes": notes or [], "errors": errors or [],
        "policy": {"name": cfg["policy_name"], "fingerprint": fingerprint(cfg)},
    }


# ----------------------------------------------------------------------------------------
# Main evaluation
# ----------------------------------------------------------------------------------------
def _display_scores(raw: dict, cfg: dict) -> tuple[dict, float]:
    """Round the overall score and the three domain scores for display.

    The overall score is always the rounded true total. When the policy asks for the parts to add up, a part is
    moved by 0.1 where needed, choosing the one whose own rounding was furthest in the other direction.
    """
    total = _round1(raw["P"] + raw["G"] + raw["R"], cfg)
    shown = {k: _round1(v, cfg) for k, v in raw.items()}
    if cfg["total_from_rounded_parts"]:
        gap = round((total - (shown["P"] + shown["G"] + shown["R"])) * 10)
        while gap:
            step = 1 if gap > 0 else -1
            k = max(raw, key=lambda d: (raw[d] - shown[d]) * step)
            shown[k] = round(shown[k] + 0.1 * step, 1)
            gap -= step
    return shown, total


def evaluate(fac: dict, cfg: dict = PROVISIONAL) -> dict:
    if any(not isinstance(k, int) for k in cfg["journal_tier_mult"]):
        cfg = normalise(cfg)
    errors = validate(fac, cfg)
    if errors:
        return _empty_result(fac, cfg, INCOMPLETE, errors=errors)
    effort = fac.get("research_effort", cfg["standard_research_effort"])
    months = fac.get("months_active", 12)
    if not cfg["evaluate_zero_assignment"] and (effort == 0 or months == 0):
        why = "no assigned research effort" if effort == 0 else "no active months in the evaluation period"
        return _empty_result(fac, cfg, NOT_EVALUATED,
                             notes=[f"Not evaluated on research: {why}. Refer to the committee."])

    W = cfg["weights"]
    fct = adjustment_factor(fac, cfg)
    first_year = fac.get("first_year", False)
    sat_scale = max(fct, 0.5)
    flags, notes = [], []
    roll = fac.get("rolling", {})
    rolling_left = cfg["rolling_max_domains"]
    documented_rule = cfg["reduced_assignment_rule"] == "documented_activity"
    reduced = fct <= cfg["reduced_assignment_factor"]
    waived = (not documented_rule) and fct < cfg["reduced_assignment_factor"]
    basis = {"P": "", "G": "", "R": ""}

    # ---------- Publications ----------
    pu = pub_units(fac, cfg)
    flags += pu["flags"]
    B_count = pub_benchmark_count(fct, first_year, cfg)
    B_units = cfg["benchmark_units"]["P"] * B_count / cfg["pub_min_count"]
    pub_gate_annual = pu["count"] >= B_count
    pub_gate_roll = False
    if pub_gate_annual:
        basis["P"] = f"{pu['count']} counted toward a minimum of {B_count}"
    elif roll.get("pubs_prior2") is not None and rolling_left > 0:
        three = pu["count"] + roll["pubs_prior2"]
        need = 3 * B_count if cfg["rolling_benchmark"] == "current_year" else B_count + 2 * cfg["pub_min_count"]
        if three >= need and fac.get("manuscripts_under_review", 0) >= 1:
            pub_gate_roll = True
            rolling_left -= 1
            basis["P"] = f"three-year rolling window ({three} of {need} required)"
            notes.append(f"Publication minimum met on the 3-year rolling window ({three} articles) "
                         f"with manuscripts under review")
    pub_frac = 1.0 if (pub_gate_annual or pub_gate_roll) else min(1.0, pu["count"] / B_count)
    P, P_anc, P_exc = domain_score(W["P"], pub_frac, pu["units"], B_units,
                                   cfg["saturation"]["P"] * sat_scale, cfg)
    pub_gate = pub_gate_annual or pub_gate_roll

    # ---------- Grants ----------
    gu = grant_units(fac, cfg)
    flags += gu["flags"]
    grant_gate = gu["gate"]
    if grant_gate:
        basis["G"] = "qualifying submission, award or active funded project"
    elif waived:
        grant_gate = True
        basis["G"] = "waived: reduced research assignment"
        notes.append(f"Grant minimum waived for a reduced research assignment (adjustment factor {fct:.2f})")
    if not grant_gate and reduced and gu["partial"]:
        grant_gate = True
        basis["G"] = "reduced assignment: documented grant engagement"
        notes.append("Reduced research assignment: grant minimum met by documented grant engagement")
    if first_year and not gu["gate"] and fac.get("proposals_in_development", 0) > 0:
        grant_gate = True
        basis["G"] = "first-year faculty: documented proposal development"
        notes.append("First-year faculty: grant minimum met by documented proposal development")
    if not grant_gate and roll.get("grant_active_years_prior2") is not None and rolling_left > 0:
        if roll["grant_active_years_prior2"] >= 2 and fac.get("proposals_in_development", 0) >= 1:
            grant_gate = True
            rolling_left -= 1
            basis["G"] = "three-year rolling window"
            notes.append("Grant minimum met on the 3-year rolling window with a proposal in development")
    g_frac = 1.0 if grant_gate else (0.5 if gu["partial"] else 0.0)
    G, G_anc, G_exc = domain_score(W["G"], g_frac, gu["units"], cfg["benchmark_units"]["G"],
                                   cfg["saturation"]["G"] * sat_scale, cfg)

    # ---------- Presentations ----------
    ru = pres_units(fac, cfg)
    flags += ru["flags"]
    pres_gate = ru["gate"]
    if pres_gate:
        basis["R"] = "qualifying conference presentation"
    elif waived:
        pres_gate = True
        basis["R"] = "waived: reduced research assignment"
        notes.append(f"Presentation minimum waived for a reduced research assignment (adjustment factor {fct:.2f})")
    elif documented_rule and reduced and ru["partial"]:
        pres_gate = True
        basis["R"] = "reduced assignment: documented dissemination activity"
        notes.append("Reduced research assignment: presentation minimum met by documented dissemination activity")
    if not pres_gate and roll.get("pres_prior2") is not None and rolling_left > 0:
        if roll["pres_prior2"] >= 2 and fac.get("abstracts_submitted", 0) >= 1:
            pres_gate = True
            rolling_left -= 1
            basis["R"] = "three-year rolling window"
            notes.append("Presentation minimum met on the 3-year rolling window with an abstract submitted")
    r_frac = 1.0 if pres_gate else (0.5 if ru["partial"] else 0.0)
    R, R_anc, R_exc = domain_score(W["R"], r_frac, ru["units"], cfg["benchmark_units"]["R"],
                                   cfg["saturation"]["R"] * sat_scale, cfg)

    shown, total = _display_scores({"P": P, "G": G, "R": R}, cfg)
    Pr, Gr, Rr = shown["P"], shown["G"], shown["R"]
    gates = {"P": pub_gate, "G": grant_gate, "R": pres_gate}
    shares = {k: (v / W[k] if W[k] else 0.0) for k, v in (("P", P), ("G", G), ("R", R))}

    # ---------- Classification ----------
    approaching = False
    if all(gates.values()):
        rule = cfg["exceeds_rule"]
        by_total = total >= cfg["exceeds_threshold"]
        broad = sum(v >= cfg["breadth_level"] for v in shares.values()) >= 2
        distinct = gu["distinction"] and total >= cfg["distinction_min_total"]
        needs_breadth = rule in ("breadth", "breadth_or_distinction")
        on_score = by_total and (broad or not needs_breadth)
        on_award = distinct and rule in ("total_or_distinction", "breadth_or_distinction")
        exceeds = on_score or on_award
        if cfg["enforce_meets_threshold"] and total < cfg["meets_threshold"]:
            cls, class_basis = DOES_NOT_MEET, "below_meets_threshold"
            flags.append(f"All minimums met but the score is below the Meets threshold of "
                         f"{cfg['meets_threshold']:g}")
        elif on_score:
            cls, class_basis = EXCEEDS, "exceeds_on_score"
        elif on_award:
            cls, class_basis = EXCEEDS, "exceeds_on_award"
            notes.append("Exceeds Expectations through a new competitive large award as PI or MPI")
        elif by_total and needs_breadth:
            cls, class_basis = MEETS, "meets_lacks_breadth"
            notes.append(f"Score is {total} but Exceeds Expectations also requires at least two domains at "
                         f"{cfg['breadth_level']:.0%} of their points")
        else:
            cls, class_basis = MEETS, "meets"
    else:
        cls, class_basis = DOES_NOT_MEET, "minimum_unmet"
        approaching = sum(not v for v in gates.values()) == 1 and total >= cfg["approaching_threshold"]
        if total >= cfg["meets_threshold"]:
            flags.append("Committee review: score >= 70 but a required minimum is unmet"
                         if cfg["meets_threshold"] == 70 else
                         f"Committee review: score >= {cfg['meets_threshold']:g} but a required minimum is unmet")
        elif any(shares[k] >= cfg["distinguished_level"] for k in shares):
            flags.append("Committee review: distinguished performance in one domain with a required minimum unmet")
        elif approaching:
            flags.append(f"Committee review: one required minimum is unmet and the score is at or above "
                         f"{cfg['approaching_threshold']:g} (approaching expectations)")
    if first_year:
        notes.append(f"First-year faculty: publication benchmark {B_count}")
    elif fct < 1.0:
        notes.append(f"Expectations prorated (adjustment factor {fct:.2f}; publication benchmark {B_count})")
    if fct > 1.0:
        notes.append(f"Expectations scaled up for research-intensive assignment "
                     f"(factor {fct:.2f}; publication benchmark {B_count})")

    def status(k, frac):
        if gates[k]:
            return "Exceeds" if shares[k] >= cfg["domain_exceeds_level"] else "Meets"
        return "Approaching" if frac > 0 else "Not met"

    parts = {"P": (Pr, P_anc, P_exc, pu["units"], B_units, pub_frac),
             "G": (Gr, G_anc, G_exc, gu["units"], cfg["benchmark_units"]["G"], g_frac),
             "R": (Rr, R_anc, R_exc, ru["units"], cfg["benchmark_units"]["R"], r_frac)}
    domains = {k: {"name": DOMAIN_NAMES[k], "score": sc, "max": W[k], "share": shares[k],
                   "anchor": anc, "excellence": exc, "units": un, "benchmark_units": bench,
                   "saturation": cfg["saturation"][k] * sat_scale, "minimum_met": gates[k],
                   "minimum_basis": basis[k], "anchor_fraction": frac, "status": status(k, frac)}
               for k, (sc, anc, exc, un, bench, frac) in parts.items()}

    return {
        "name": fac.get("name", ""), "faculty_id": fac.get("faculty_id", ""),
        "evaluation_year": fac.get("evaluation_year", ""),
        "P": Pr, "G": Gr, "R": Rr, "total": total,
        "class": cls, "class_basis": class_basis, "gates": gates, "gate_basis": basis, "factor": round(fct, 2),
        "pub_benchmark": B_count,
        "pub_count": pu["count"],
        "units": {"P": round(pu["units"], 2), "G": round(gu["units"], 2), "R": round(ru["units"], 2)},
        "domains": domains, "breakdown": pu["lines"] + gu["lines"] + ru["lines"],
        "approaching": approaching, "scored": True,
        "flags": _unique(flags), "notes": _unique(notes), "errors": [],
        "policy": {"name": cfg["policy_name"], "fingerprint": fingerprint(cfg)},
    }


def report(res: dict, cfg: dict = PROVISIONAL) -> str:
    head = f"Faculty research evaluation: {res['name']}"
    if not res["scored"]:
        return "\n".join([head, f"Research evaluation: {res['class']}"] +
                         ["- " + m for m in res["errors"] + res["notes"]])
    lines = [head, "| Component | Score |", "|---|---:|",
             *(f"| {d['name']} | {d['score']}/{d['max']:g} |" for d in res["domains"].values()),
             f"| Overall research score | {res['total']}/100 |",
             f"| Research evaluation | {res['class']} |"]
    names = {"P": "Publications", "G": "Grants", "R": "Presentations"}
    met = [k for k, v in res["gates"].items() if v]
    lines.append("Minimums met: " + (", ".join(names[k] for k in met) or "none"))
    exc = [names[k] for k, d in res["domains"].items() if d["status"] == "Exceeds"]
    if exc:
        lines.append("Exceeded expectations in: " + ", ".join(exc))
    unmet = [names[k] for k, v in res["gates"].items() if not v]
    if unmet:
        lines.append("Needs improvement: " + ", ".join(unmet))
    for n in res["notes"] + res["flags"]:
        lines.append("- " + n)
    lines.append(f"Policy: {res['policy']['name']} [{res['policy']['fingerprint']}]")
    return "\n".join(lines)
