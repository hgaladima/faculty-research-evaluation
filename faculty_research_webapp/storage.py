"""Local file storage for the active scoring policy, its change log, and saved evaluations."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

from engine.policy import PROVISIONAL, check_policy, diff, fingerprint, normalise

DATA_DIR = Path(__file__).parent / "data"
POLICY_FILE = DATA_DIR / "policy.json"
LOG_FILE = DATA_DIR / "policy_log.jsonl"
EVAL_DIR = DATA_DIR / "evaluations"

META_DEFAULTS = {"version": 1, "locked": False, "approved_by": "", "saved_by": "", "evaluation_year": "",
                 "saved_at": "", "note": ""}
MAX_NAME_LENGTH = 80


class PolicyConflict(Exception):
    """The policy on disk is not the one this session was editing."""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _write_text(path: Path, text: str) -> None:
    """Write through a temporary file so an interrupted save cannot leave a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def default_policy_state(problem: str | None = None) -> dict:
    meta = dict(META_DEFAULTS, note="Shipped provisional defaults; not yet approved.")
    return {"policy": normalise(PROVISIONAL), "meta": meta, "problem": problem}


def load_policy_state() -> dict:
    """Return {"policy", "meta", "problem"}. An unusable file yields the shipped defaults and a problem message."""
    if not POLICY_FILE.exists():
        return default_policy_state()
    try:
        raw = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("the file does not contain a policy")
        if "policy" not in raw and "weights" in raw:
            raw = {"policy": raw, "meta": {"note": "Loaded from a downloaded policy file."}}
        policy = normalise(raw["policy"])
        errors, _ = check_policy(policy)
        if errors:
            raise ValueError(errors[0])
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        reason = "it is not valid JSON" if isinstance(exc, json.JSONDecodeError) else str(exc)
        return default_policy_state(f"The saved policy file could not be used: {reason}. The shipped provisional "
                                    f"policy is in use instead. The file was left untouched at {POLICY_FILE}.")
    meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
    return {"policy": policy, "meta": {**META_DEFAULTS, **meta}, "problem": None}


def state_key(state: dict) -> tuple:
    """Identifies one saved state of the policy; differs after any save, lock or unlock."""
    meta = state["meta"]
    return fingerprint(state["policy"]), meta["version"], meta["locked"], meta["saved_at"]


def _current_for_write(expected: dict) -> dict:
    current = load_policy_state()
    if current["problem"]:
        if POLICY_FILE.exists():
            os.replace(POLICY_FILE, POLICY_FILE.with_name(f"policy.unusable-{datetime.now():%Y%m%d-%H%M%S}.json"))
        return expected
    if state_key(current) != state_key(expected):
        raise PolicyConflict("The scoring policy was changed in another window since this page loaded. "
                             "Nothing was saved; the page now shows the current policy.")
    return current


def _append_log(entry: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def save_policy(expected: dict, policy: dict, *, who: str, year: str, note: str, lock: bool) -> dict:
    """Save a policy over the state this session loaded, bump the version on a change, and log it."""
    current = _current_for_write(expected)
    if current["meta"]["locked"]:
        raise PolicyConflict("The scoring policy is locked. Unlock it before saving changes.")
    errors, _ = check_policy(policy)
    if errors:
        raise ValueError(errors[0])
    changes = diff(current["policy"], policy)
    version = current["meta"]["version"] + (1 if changes else 0)
    meta = dict(META_DEFAULTS, version=version, locked=lock, approved_by=who if lock else "", saved_by=who,
                evaluation_year=year, saved_at=_now(), note=note)
    state = {"policy": normalise(policy), "meta": meta}
    _write_text(POLICY_FILE, json.dumps(state, indent=2, default=str))
    _append_log({"when": _now(), "who": who, "action": "approved and locked" if lock else "saved as working draft",
                 "version": version, "fingerprint": fingerprint(policy), "note": note,
                 "changes": [{"setting": k, "from": a, "to": b} for k, a, b in changes]})
    return dict(state, problem=None)


def unlock_policy(expected: dict, *, who: str, reason: str) -> dict:
    """Reopen a locked policy. The earlier approval no longer applies, so it is cleared."""
    current = _current_for_write(expected)
    meta = dict(current["meta"], locked=False, approved_by="", saved_by=who, saved_at=_now(),
                note=f"Unlocked: {reason}")
    state = {"policy": current["policy"], "meta": meta}
    _write_text(POLICY_FILE, json.dumps(state, indent=2, default=str))
    _append_log({"when": _now(), "who": who, "action": "unlocked", "version": meta["version"],
                 "fingerprint": fingerprint(state["policy"]), "note": reason, "changes": []})
    return dict(state, problem=None)


def read_log() -> list[dict]:
    """Newest first. Lines that cannot be read are skipped."""
    if not LOG_FILE.exists():
        return []
    entries = []
    for line in LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries[::-1]


def slug(text: str) -> str:
    """A safe file-name part that keeps letters and digits of any script."""
    return re.sub(r"[^\w]+", "_", text, flags=re.UNICODE).strip("_")[:MAX_NAME_LENGTH] or "unnamed"


def evaluation_name(info: dict) -> str:
    who = slug(info.get("faculty_id") or info.get("name") or "")
    return f"{who}_{slug(str(info.get('evaluation_year') or ''))}"


def save_evaluation(record: dict) -> str:
    name = evaluation_name(record["form"]["info"])
    record["saved_at"] = _now()
    _write_text(EVAL_DIR / f"{name}.json", json.dumps(record, indent=2, default=str))
    return name


def list_evaluations() -> list[str]:
    if not EVAL_DIR.exists():
        return []
    return sorted(p.stem for p in EVAL_DIR.glob("*.json"))


def load_evaluation(name: str) -> dict | None:
    """The saved record, or None when the file is missing, damaged or not an evaluation."""
    try:
        record = json.loads((EVAL_DIR / f"{name}.json").read_text(encoding="utf-8"))
        if not isinstance(record["form"]["info"], dict):
            return None
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return record


def saved_subject(name: str) -> str | None:
    """Who a saved evaluation is for, or None when no file has that name."""
    if not (EVAL_DIR / f"{name}.json").exists():
        return None
    record = load_evaluation(name)
    if record is None:
        return "a file that cannot be read"
    info = record["form"]["info"]
    return ", ".join(x for x in (info.get("name"), info.get("faculty_id"), str(info.get("evaluation_year") or "")) if x)
