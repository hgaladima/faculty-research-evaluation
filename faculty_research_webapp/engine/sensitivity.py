"""Compare how a set of faculty profiles is classified under two policies."""
from __future__ import annotations

from .research_eval import evaluate
from .scenarios import SCENARIOS

SHORT = {"Exceeds Expectations": "E", "Meets Expectations": "M", "Does Not Meet Expectations": "D",
         "Not Evaluated": "N", "Incomplete: input errors": "!"}


def class_counts(results: list[dict]) -> dict:
    counts = {}
    for r in results:
        counts[r["class"]] = counts.get(r["class"], 0) + 1
    return counts


def compare(old_policy: dict, new_policy: dict, profiles: list[dict] | None = None) -> dict:
    """Evaluate each profile under both policies and report what changes."""
    profiles = SCENARIOS if profiles is None else profiles
    before = [evaluate(p, old_policy) for p in profiles]
    after = [evaluate(p, new_policy) for p in profiles]
    rows = [{"Profile": b["name"], "Score before": b["total"], "Score after": a["total"],
             "Class before": b["class"], "Class after": a["class"],
             "Reclassified": b["class"] != a["class"]}
            for b, a in zip(before, after)]
    return {"rows": rows, "before": class_counts(before), "after": class_counts(after),
            "reclassified": sum(r["Reclassified"] for r in rows)}


if __name__ == "__main__":
    from .policy import LEGACY, PROVISIONAL

    out = compare(LEGACY, PROVISIONAL)
    print("Phase 1 original:", out["before"])
    print("Provisional     :", out["after"])
    for r in out["rows"]:
        mark = "  <-- reclassified" if r["Reclassified"] else ""
        print(f"{r['Profile'][:48]:48s} {r['Score before']:5} -> {r['Score after']:5}  "
              f"{SHORT[r['Class before']]} -> {SHORT[r['Class after']]}{mark}")
