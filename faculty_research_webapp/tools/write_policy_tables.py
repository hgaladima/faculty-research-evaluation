"""Regenerate section 8 of PROVISIONAL_POLICY.md from the shipped policy presets.

Run from faculty_research_webapp/ after changing a default:  python -m tools.write_policy_tables
"""
from pathlib import Path

from engine.policy import LEGACY, PROVISIONAL, fingerprint
from policy_labels import OPTION_LABELS, POLICY_GROUPS, POLICY_TABLES

NOTE = Path(__file__).resolve().parents[2] / "PROVISIONAL_POLICY.md"
MARKER = "Generated from the shipped provisional policy."


def _get(policy: dict, path: str):
    for part in path.split("."):
        policy = policy[part]
    return policy


def _show(value) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if value is None:
        return "none"
    if isinstance(value, list):
        return ", ".join(value)
    if isinstance(value, float):
        return f"{value:g}"
    return OPTION_LABELS.get(value, str(value))


def tables() -> str:
    out = [f"Policy: {PROVISIONAL['policy_name']}. Fingerprint `{fingerprint(PROVISIONAL)}`. "
           f"Phase 1 fingerprint `{fingerprint(LEGACY)}`.", ""]
    for title, _, fields in POLICY_GROUPS:
        out += [f"### {title}", "", "| Setting | Provisional | Phase 1 |", "|---|---|---|"]
        for path, label, _ in fields:
            new, old = _show(_get(PROVISIONAL, path)), _show(_get(LEGACY, path))
            out.append(f"| {label} | {new} | {'same' if old == new else old} |")
        out.append("")
    for name, label in POLICY_TABLES:
        out += [f"### {label}", "", "| Item | Value | Phase 1 |", "|---|---:|---|"]
        for key, value in PROVISIONAL[name].items():
            old = LEGACY[name].get(key)
            was = "same" if old == value else "not credited" if old is None else f"{old:g}"
            out.append(f"| {str(key).replace('_', ' ')} | {value:g} | {was} |")
        out.append("")
    return "\n".join(out)


def main() -> None:
    text = NOTE.read_text(encoding="utf-8")
    head, _, _ = text.partition(MARKER)
    intro = f"{MARKER} Units are converted to points as described in the app's Guide tab.\n\n"
    NOTE.write_text(head + intro + tables(), encoding="utf-8", newline="\n")
    print(f"Rewrote section 8 of {NOTE.name}")


if __name__ == "__main__":
    main()
