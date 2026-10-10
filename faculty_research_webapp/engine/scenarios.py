"""22 hypothetical faculty profiles for testing the algorithm."""

A = lambda tier, role="lead", **k: {"type": "article", "tier": tier, "role": role, **k}

SCENARIOS = [
 {"name": "S1 Exactly the minimum",
  "publications": [A(3), A(3, "coauthor")],
  "submissions": [{"size": "major", "role": "Co-I"}],
  "presentations": [{"type": "poster", "venue": "B"}]},

 {"name": "S2 High publications, limited grants",
  "publications": [A(1), A(1), A(2), A(2), A(3, "coauthor")],
  "submissions": [{"size": "internal", "role": "PI"}],
  "presentations": [{"type": "oral", "venue": "B"}, {"type": "oral", "venue": "B"}]},

 {"name": "S3 Two high-impact publications",
  "publications": [A(1), A(1)],
  "submissions": [{"size": "major", "role": "Co-PI"}],
  "presentations": [{"type": "oral", "venue": "A"}]},

 {"name": "S4 Five moderate-impact publications",
  "publications": [A(2), A(2), A(2), A(2, "coauthor"), A(2, "coauthor")],
  "submissions": [{"size": "major", "role": "PI"}],
  "presentations": [{"type": "poster", "venue": "B"}, {"type": "poster", "venue": "B"}]},

 {"name": "S5 Many publications, questionable venues",
  "publications": [A(0)] * 5 + [A(3, "coauthor"), A(3, "coauthor")],
  "submissions": [{"size": "major", "role": "Co-I"}],
  "presentations": [{"type": "oral", "venue": "0"}, {"type": "poster", "venue": "C"}]},

 {"name": "S6 No publications, substantial grants",
  "publications": [],
  "submissions": [{"size": "large", "role": "PI", "scored": True}, {"size": "major", "role": "PI"}],
  "awards": [{"size": "large", "role": "PI"}, {"size": "major", "role": "Co-PI"}],
  "presentations": [{"type": "invited", "venue": "A"}, {"type": "invited", "venue": "B"}]},

 {"name": "S7 Two publications, several unfunded proposals",
  "publications": [A(2), A(2)],
  "submissions": [{"size": "large", "role": "PI", "scored": True},
                  {"size": "large", "role": "PI", "scored": True},   # resubmission
                  {"size": "major", "role": "PI"},
                  {"size": "major", "role": "Co-I"}],
  "presentations": [{"type": "oral", "venue": "B"}]},

 {"name": "S8 Major federal grant as PI",
  "publications": [A(2), A(2), A(3, "coauthor")],
  "submissions": [{"size": "major", "role": "Co-I"}],
  "awards": [{"size": "large", "role": "PI"}],
  "presentations": [{"type": "oral", "venue": "A"}, {"type": "oral", "venue": "A"}]},

 {"name": "S9 Co-I on several large grants",
  "publications": [A(3, "coauthor"), A(3, "coauthor"), A(2, "coauthor")],
  "awards": [{"size": "large", "role": "Co-I"}] * 3,
  "presentations": [{"type": "poster", "venue": "B", "role": "coauthor"}]},

 {"name": "S10 Many presentations, one publication",
  "publications": [A(2)],
  "submissions": [{"size": "major", "role": "PI"}],
  "presentations": [{"type": "oral", "venue": "B"}] * 2 + [{"type": "poster", "venue": "B"}] * 3 +
                   [{"type": "invited", "venue": "B"}]},

 {"name": "S11 Prestigious international conferences",
  "publications": [A(2), A(2)],
  "submissions": [{"size": "major", "role": "Co-PI"}],
  "presentations": [{"type": "keynote", "venue": "A"}, {"type": "oral", "venue": "A"},
                    {"type": "oral", "venue": "A"}],
  "sessions_chaired": 1},

 {"name": "S12 Strong research mentorship",
  "publications": [A(2, student_first=True)] * 3 + [A(3, student_first=True)],
  "submissions": [{"size": "internal", "role": "PI"}, {"size": "major", "role": "Co-I"}],
  "presentations": [{"type": "poster", "venue": "A", "role": "mentor"}] * 3 + [{"type": "oral", "venue": "B"}]},

 {"name": "S13 Interdisciplinary team science",
  "publications": [A(1, "coauthor")] * 2 + [A(2, "coauthor")] * 2 + [A(3, "coauthor")] * 2,
  "submissions": [{"size": "major", "role": "Co-I"}] * 2,
  "active_projects": [{"role": "Co-I"}],
  "presentations": [{"type": "oral", "venue": "A", "role": "coauthor"}, {"type": "poster", "venue": "B"}]},

 {"name": "S14 Policy-impact research",
  "publications": [A(1, documented_impacts=2), A(2), A(2),
                   {"type": "policy_brief"}, {"type": "policy_brief"}, {"type": "technical_report"}],
  "awards": [{"size": "major", "role": "PI"}],
  "presentations": [{"type": "oral", "venue": "B"}, {"type": "outreach"}]},

 {"name": "S15 Minimal research activity",
  "publications": [],
  "presentations": [{"type": "poster", "venue": "C", "role": "coauthor"}]},

 {"name": "S16 First-year faculty",
  "first_year": True,
  "publications": [A(2)],
  "proposals_in_development": 1,
  "submissions": [{"size": "internal", "role": "PI"}],
  "presentations": [{"type": "poster", "venue": "B"}]},

 {"name": "S17 Returning from 6-month approved leave",
  "months_active": 6,
  "publications": [A(1)],
  "submissions": [{"size": "major", "role": "PI"}],
  "presentations": [{"type": "oral", "venue": "B"}]},

 {"name": "S18 Strong 3-year record, low-output year",
  "publications": [A(2)],
  "manuscripts_under_review": 2,
  "rolling": {"pubs_prior2": 7},
  "active_projects": [{"role": "PI"}],
  "presentations": [{"type": "oral", "venue": "B"}]},

 {"name": "S19 Exceptional across all domains",
  "publications": [A(1), A(1), A(1), A(2), A(1, "coauthor")],
  "editorial": [{"role": "editorial_board"}, {"role": "manuscript_review", "n": 6}],
  "submissions": [{"size": "major", "role": "PI", "scored": True}, {"size": "major", "role": "PI"}],
  "awards": [{"size": "large", "role": "PI"}],
  "presentations": [{"type": "keynote", "venue": "A"}, {"type": "oral", "venue": "A"},
                    {"type": "oral", "venue": "A"}, {"type": "poster", "venue": "A", "role": "mentor"}]},

 {"name": "S20 High score, missing a required minimum",
  "publications": [A(1)] * 3 + [A(2)] * 3,
  "submissions": [{"size": "large", "role": "Co-PI"}],
  "awards": [{"size": "large", "role": "Co-PI"}],
  "presentations": []},

 {"name": "S21 Research-intensive appointment (60%)",
  "research_effort": 60,
  "publications": [A(2), A(2), A(3, "coauthor")],
  "submissions": [{"size": "large", "role": "PI"}],
  "presentations": [{"type": "oral", "venue": "B"}]},

 {"name": "S22 Teaching-intensive appointment (20%)",
  "research_effort": 20,
  "publications": [A(3)],
  "proposals_in_development": 1,
  "presentations": [{"type": "poster", "venue": "B"}]},
]

# Phase 1 relied on a missing presentation role meaning "presenter". The role is stated
# explicitly here so the profiles mean the same thing under every policy.
for _fac in SCENARIOS:
    for _p in _fac.get("presentations", []):
        _p.setdefault("role", "presenter")
