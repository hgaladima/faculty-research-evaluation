"""Translate between the data-entry tables shown in the app and the engine's faculty record."""
from __future__ import annotations

import math

PUB_TYPES = {
    "Journal article": "article", "Scholarly book": "book", "Book chapter": "chapter",
    "Edited book": "edited_book", "Technical report": "technical_report", "Policy brief": "policy_brief",
    "Software or analytical tool": "software", "Research dataset": "dataset",
    "Editorial or commentary": "editorial", "Book review": "book_review",
    "Published abstract": "published_abstract",
}
JOURNAL_TIERS = {"Tier 1": 1, "Tier 2": 2, "Tier 3": 3, "Questionable venue (not credited)": 0,
                 "Not yet verified": None}
AUTHORSHIP = {"Sole or first author": "lead", "Senior (last) author": "lead", "Corresponding author": "lead",
              "Second author": "second", "Other coauthor": "coauthor", "Not yet verified": None}
QUARTILES = ["Q1", "Q2", "Q3", "Q4", "Not ranked"]

GRANT_SOURCES = ["External", "Internal"]
GRANT_ROLES = {"PI": "PI", "MPI": "MPI", "Co-PI": "Co-PI", "Co-I": "Co-I",
               "Collaborator": "collaborator", "Consultant": "consultant", "Not yet verified": None}
SUBMITTED, AWARDED, ACTIVE = ("Submitted (pending or not funded)", "Awarded this year",
                              "Active (awarded in a prior year)")
GRANT_STATUSES = [SUBMITTED, AWARDED, ACTIVE]

PRES_TYPES = {
    "Keynote": "keynote", "Plenary": "plenary", "Invited talk": "invited", "Oral (peer-reviewed)": "oral",
    "Panel": "panel", "Workshop": "workshop", "Poster": "poster",
    "Institutional symposium": "institutional", "Community or practitioner outreach": "outreach",
    "Research seminar or journal club": "seminar",
}
VENUE_TIERS = {"Tier A": "A", "Tier B": "B", "Tier C": "C", "Questionable (not credited)": "0",
               "Not yet verified": None}
PRES_ROLES = {"Presenter": "presenter", "Mentor of student presenter": "mentor",
              "Coauthor (not presenting)": "coauthor", "Not yet verified": None}
PRES_SCOPES = ["International", "National", "Regional", "State or local", "Institutional"]
LOCAL_PRES = {"institutional", "outreach", "seminar"}

EDITORIAL_ROLES = {"Journal editor": "editor", "Associate editor": "associate_editor",
                   "Guest editor": "guest_editor", "Editorial board member": "editorial_board",
                   "Manuscript reviews (count)": "manuscript_review"}
REVIEW_TYPES = {"Federal review panel": "federal_panel", "Other review panel": "other_panel"}

PUB_COLUMNS = ["Title", "Journal or publisher", "Type", "Peer reviewed", "Journal tier", "Authorship",
               "Student or mentee first author", "Documented impacts", "DOI", "Quartile (info)",
               "Impact factor (info)", "Credited in a prior year"]
GRANT_COLUMNS = ["Title", "Funder", "Source", "Total amount ($)", "Role", "Competitive", "Status",
                 "Also submitted this year", "Scored or discussed", "Credited in a prior year"]
PRES_COLUMNS = ["Title", "Meeting", "Location (info)", "Scope (info)", "Type", "Venue tier", "Role",
                "Peer-reviewed abstract (info)"]
EDITORIAL_COLUMNS = ["Role", "Count"]
REVIEW_COLUMNS = ["Panel type", "Count"]

REPRESENTATIVE_AMOUNT = {"minor": 5_000, "major": 100_000, "large": 500_000}


def _blank(v) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return isinstance(v, str) and not v.strip()


def _text(v) -> str:
    return "" if _blank(v) else str(v).strip()


def _flag(v, default=False) -> bool:
    return default if _blank(v) else bool(v)


def _whole(v) -> int:
    return 0 if _blank(v) else int(v)


def _reverse(mapping: dict, value):
    return next(label for label, v in mapping.items() if v == value)


def size_band(source: str, amount, bands: dict) -> str | None:
    if source == "Internal":
        return "internal"
    if _blank(amount):
        return None
    if amount < bands["minor_max"]:
        return "minor"
    return "major" if amount < bands["large_min"] else "large"


def build_faculty(info: dict, pubs: list[dict], grants: list[dict], pres: list[dict],
                  editorial: list[dict], reviews: list[dict], policy: dict) -> tuple[dict, list[str]]:
    """Return (faculty record for the engine, list of data-entry problems)."""
    problems = []
    fac = {
        "name": _text(info.get("name")), "faculty_id": _text(info.get("faculty_id")),
        "evaluation_year": _text(info.get("evaluation_year")),
        "research_effort": policy["standard_research_effort"] if _blank(info.get("research_effort"))
        else info["research_effort"],
        "months_active": 12 if _blank(info.get("months_active")) else info["months_active"],
        "first_year": bool(info.get("first_year", False)),
        "publications": [], "submissions": [], "awards": [], "active_projects": [], "presentations": [],
        "editorial": [], "grant_reviews": [], "entry_notes": [],
    }
    for key in ("sessions_chaired", "proposals_in_development", "unfunded_projects",
                "manuscripts_under_review", "abstracts_submitted"):
        fac[key] = _whole(info.get(key))
    rolling = {k: _whole(info.get(k)) for k in ("pubs_prior2", "grant_active_years_prior2", "pres_prior2")
               if info.get(f"use_{k}")}
    if rolling:
        fac["rolling"] = rolling

    for i, row in enumerate(pubs, 1):
        if all(_blank(row.get(c)) for c in ("Title", "Type", "Journal or publisher")):
            continue
        where = f"Publications row {i}"
        if _blank(row.get("Type")):
            problems.append(f"{where}: choose a publication type.")
            continue
        t = PUB_TYPES[row["Type"]]
        item = {"type": t, "title": _text(row.get("Title")), "peer_reviewed": _flag(row.get("Peer reviewed"), True)}
        if t == "article" and item["peer_reviewed"]:
            if _blank(row.get("Journal tier")):
                problems.append(f"{where}: choose a journal tier (or 'Not yet verified').")
                continue
            tier = JOURNAL_TIERS[row["Journal tier"]]
            if tier is not None:
                item["tier"] = tier
        if t in ("article", "book"):
            if _blank(row.get("Authorship")):
                problems.append(f"{where}: choose the authorship role.")
                continue
            role = AUTHORSHIP[row["Authorship"]]
            if role is not None:
                item["role"] = role if role in policy["author_role_mult"] else "coauthor"
        if _flag(row.get("Student or mentee first author")):
            item["student_first"] = True
        if _whole(row.get("Documented impacts")):
            item["documented_impacts"] = _whole(row.get("Documented impacts"))
        if _text(row.get("DOI")):
            item["doi"] = _text(row.get("DOI"))
        if _flag(row.get("Credited in a prior year")):
            item["counted_in_prior_year"] = True
        fac["publications"].append(item)

    for i, row in enumerate(grants, 1):
        if all(_blank(row.get(c)) for c in ("Title", "Status", "Funder")):
            continue
        where = f"Grants row {i}"
        status, role_label = row.get("Status"), row.get("Role")
        if _blank(status) or _blank(role_label):
            problems.append(f"{where}: choose a status and a role.")
            continue
        role, title = GRANT_ROLES[role_label], _text(row.get("Title"))
        also_submitted = _flag(row.get("Also submitted this year"))
        prior_year = _flag(row.get("Credited in a prior year"))
        if status == ACTIVE:
            if also_submitted:
                problems.append(f"{where}: a project awarded in a prior year cannot also be 'submitted this year'. "
                                f"Untick the box, or add a separate row for the new submission.")
                continue
            fac["active_projects"].append({"role": role, "title": title})
            continue
        source = "External" if _blank(row.get("Source")) else row["Source"]
        amount = None if _blank(row.get("Total amount ($)")) else float(row["Total amount ($)"])
        size = size_band(source, amount, policy["amount_bands"])
        if size is None:
            problems.append(f"{where}: enter the total amount (needed to set the size band of an external grant).")
            continue
        entry = {"id": f"G{i}", "title": title, "size": size, "role": role,
                 "competitive": _flag(row.get("Competitive"), True)}
        if amount is not None and size != "internal":
            entry["amount"] = amount
        if prior_year:
            fac["entry_notes"].append(f"{where}{f' ({title})' if title else ''}: marked as credited in a prior "
                                      f"year, so it earns no credit this year.")
            if status == AWARDED:
                fac["awards"].append(dict(entry, counted_in_prior_year=True))
            continue
        if status == SUBMITTED or also_submitted:
            fac["submissions"].append(dict(entry, scored=_flag(row.get("Scored or discussed"))))
        if status == AWARDED:
            fac["awards"].append(dict(entry))

    for i, row in enumerate(pres, 1):
        if all(_blank(row.get(c)) for c in ("Title", "Type", "Meeting")):
            continue
        where = f"Presentations row {i}"
        if _blank(row.get("Type")) or _blank(row.get("Role")):
            problems.append(f"{where}: choose a presentation type and a role.")
            continue
        t = PRES_TYPES[row["Type"]]
        item = {"type": t, "title": _text(row.get("Title"))}
        if PRES_ROLES[row["Role"]] is not None:
            item["role"] = PRES_ROLES[row["Role"]]
        if t not in LOCAL_PRES:
            if _blank(row.get("Venue tier")):
                problems.append(f"{where}: choose a venue tier (or 'Not yet verified').")
                continue
            venue = VENUE_TIERS[row["Venue tier"]]
            if venue is not None:
                item["venue"] = venue
        fac["presentations"].append(item)

    for i, row in enumerate(editorial, 1):
        if _blank(row.get("Role")):
            continue
        fac["editorial"].append({"role": EDITORIAL_ROLES[row["Role"]], "n": max(_whole(row.get("Count")), 1)})
    for row in reviews:
        if _blank(row.get("Panel type")):
            continue
        fac["grant_reviews"] += [REVIEW_TYPES[row["Panel type"]]] * max(_whole(row.get("Count")), 1)
    return fac, problems


def rows_from_faculty(fac: dict) -> dict:
    """Turn an engine faculty record (such as a test scenario) into data-entry tables."""
    pubs = []
    for p in fac.get("publications", []):
        t = p.get("type", "article")
        role = p.get("role")
        tier = p.get("tier")
        pubs.append({
            "Title": p.get("title", ""), "Journal or publisher": "", "Type": _reverse(PUB_TYPES, t),
            "Peer reviewed": p.get("peer_reviewed", True),
            "Journal tier": _reverse(JOURNAL_TIERS, tier) if t == "article" else None,
            "Authorship": _reverse(AUTHORSHIP, role) if t in ("article", "book") else None,
            "Student or mentee first author": bool(p.get("student_first", False)),
            "Documented impacts": p.get("documented_impacts", 0), "DOI": p.get("doi", ""),
            "Quartile (info)": None, "Impact factor (info)": None,
            "Credited in a prior year": bool(p.get("counted_in_prior_year", False)),
        })

    def grant_row(g, status, also_submitted=False, scored=False):
        size = g.get("size")
        return {"Title": g.get("title", ""), "Funder": "",
                "Source": "Internal" if size == "internal" else "External",
                "Total amount ($)": g.get("amount", REPRESENTATIVE_AMOUNT.get(size)),
                "Role": _reverse(GRANT_ROLES, g.get("role")),
                "Competitive": g.get("competitive", True), "Status": status,
                "Also submitted this year": also_submitted,
                "Scored or discussed": bool(g.get("scored", False)) or scored,
                "Credited in a prior year": bool(g.get("counted_in_prior_year", False))}

    awards = fac.get("awards", [])
    funded = {a["id"]: s for a in awards if a.get("id") and not a.get("counted_in_prior_year")
              for s in fac.get("submissions", []) if s.get("id") == a["id"]}
    grants = ([grant_row(s, SUBMITTED) for s in fac.get("submissions", []) if s.get("id") not in funded] +
              [grant_row(a, AWARDED, a.get("id") in funded, bool(funded.get(a.get("id"), {}).get("scored")))
               for a in awards] +
              [grant_row(p, ACTIVE) for p in fac.get("active_projects", [])])
    pres = [{"Title": p.get("title", ""), "Meeting": "", "Location (info)": "", "Scope (info)": None,
             "Type": _reverse(PRES_TYPES, p["type"]),
             "Venue tier": None if p["type"] in LOCAL_PRES else _reverse(VENUE_TIERS, p.get("venue")),
             "Role": _reverse(PRES_ROLES, p.get("role")),
             "Peer-reviewed abstract (info)": False}
            for p in fac.get("presentations", [])]
    editorial = [{"Role": _reverse(EDITORIAL_ROLES, e["role"]), "Count": e.get("n", 1)}
                 for e in fac.get("editorial", [])]
    reviews = [{"Panel type": _reverse(REVIEW_TYPES, r), "Count": 1} for r in fac.get("grant_reviews", [])]
    roll = fac.get("rolling", {})
    info = {"name": fac.get("name", ""), "faculty_id": fac.get("faculty_id", ""),
            "evaluation_year": fac.get("evaluation_year", ""),
            "research_effort": fac.get("research_effort"), "months_active": fac.get("months_active", 12),
            "first_year": bool(fac.get("first_year", False))}
    for key in ("sessions_chaired", "proposals_in_development", "unfunded_projects",
                "manuscripts_under_review", "abstracts_submitted"):
        info[key] = fac.get(key, 0)
    for key in ("pubs_prior2", "grant_active_years_prior2", "pres_prior2"):
        info[f"use_{key}"] = roll.get(key) is not None
        info[key] = roll.get(key) or 0
    return {"info": info, "pubs": pubs, "grants": grants, "pres": pres, "editorial": editorial,
            "reviews": reviews}
