"""Local file storage for the active scoring policy, its change log, and saved evaluations."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from engine.policy import PROVISIONAL, diff, fingerprint, normalise

DATA_DIR = Path(__file__).parent / "data"
POLICY_FILE = DATA_DIR / "policy.json"
LOG_FILE = DATA_DIR / "policy_log.jsonl"
EVAL_DIR = DATA_DIR / "evaluations"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def default_policy_state() -> dict:
    return {"policy": normalise(PROVISIONAL),
            "meta": {"version": 1, "locked": False, "approved_by": "", "evaluation_year": "",
                     "saved_at": "", "note": "Shipped provisional defaults; not yet approved."}}


def load_policy_state() -> dict:
    if not POLICY_FILE.exists():
        return default_policy_state()
    state = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
    state["policy"] = normalise(state["policy"])
    return state


def _append_log(entry: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def save_policy(previous: dict, policy: dict, *, who: str, year: str, note: str, lock: bool) -> dict:
    """Save a policy, bumping the version when a setting changed, and log the change."""
    changes = diff(previous["policy"], policy)
    version = previous["meta"]["version"] + (1 if changes else 0)
    state = {"policy": normalise(policy),
             "meta": {"version": version, "locked": lock, "approved_by": who, "evaluation_year": year,
                      "saved_at": _now(), "note": note}}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    POLICY_FILE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
    _append_log({"when": _now(), "who": who, "action": "saved and locked" if lock else "saved",
                 "version": version, "fingerprint": fingerprint(policy), "note": note,
                 "changes": [{"setting": k, "from": a, "to": b} for k, a, b in changes]})
    return state


def unlock_policy(state: dict, *, who: str, reason: str) -> dict:
    state = {"policy": state["policy"], "meta": dict(state["meta"], locked=False)}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    POLICY_FILE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
    _append_log({"when": _now(), "who": who, "action": "unlocked", "version": state["meta"]["version"],
                 "fingerprint": fingerprint(state["policy"]), "note": reason, "changes": []})
    return state


def read_log() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()][::-1]


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_") or "unnamed"


def evaluation_name(info: dict) -> str:
    who = slug(info.get("faculty_id") or info.get("name") or "")
    return f"{who}_{slug(str(info.get('evaluation_year') or ''))}"


def save_evaluation(record: dict) -> str:
    name = evaluation_name(record["form"]["info"])
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    record["saved_at"] = _now()
    (EVAL_DIR / f"{name}.json").write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
    return name


def saved_subject(name: str) -> str | None:
    """Who a saved evaluation is for, or None when no file has that name."""
    if not (EVAL_DIR / f"{name}.json").exists():
        return None
    info = load_evaluation(name)["form"]["info"]
    return ", ".join(x for x in (info.get("name"), info.get("faculty_id"), str(info.get("evaluation_year") or "")) if x)


def list_evaluations() -> list[str]:
    if not EVAL_DIR.exists():
        return []
    return sorted(p.stem for p in EVAL_DIR.glob("*.json"))


def load_evaluation(name: str) -> dict:
    return json.loads((EVAL_DIR / f"{name}.json").read_text(encoding="utf-8"))
