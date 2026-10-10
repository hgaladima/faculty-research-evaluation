"""Visual layer: the stylesheet and the hand-built HTML pieces (masthead, policy card, result instrument)."""
from __future__ import annotations

from html import escape

from engine.research_eval import DOES_NOT_MEET, EXCEEDS, MEETS

CSS = """
<style>
:root {
  --ink: #14202B; --muted: #5A6A79; --line: #D5DCE4; --paper: #F3F5F8; --surface: #FFFFFF;
  --harbor: #1D4E89; --harbor-soft: #E4ECF6;
  --good: #1F7A55; --good-soft: #E3F1EA; --warn: #A9690A; --warn-soft: #F8EDD8;
  --bad: #B0362D; --bad-soft: #F7E4E1;
}
.block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1180px; }
h1, h2, h3, h4 { letter-spacing: -0.01em; }
h3 { font-size: 1.45rem !important; padding-top: 0.6rem !important; }
h4 { font-size: 1.15rem !important; }

/* Tabs read as the steps of one review */
.stTabs [data-baseweb="tab-list"] { gap: 0.25rem; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] { padding: 0.55rem 0.7rem; border-radius: 0.5rem 0.5rem 0 0; color: var(--muted); }
.stTabs [data-baseweb="tab"] p { font-size: 0.95rem; font-weight: 550; }
.stTabs [data-baseweb="tab"][aria-selected="true"] { background: var(--surface); color: var(--harbor); }
.stTabs [data-baseweb="tab"]:focus-visible { outline: 2px solid var(--harbor); outline-offset: -2px; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.1rem; }

[data-testid="stExpander"] details { background: var(--surface); }
[data-testid="stCaptionContainer"] p { color: var(--muted); max-width: 78ch; }

/* Masthead */
.fre-mast { display: flex; justify-content: space-between; align-items: flex-end; gap: 1.5rem;
  flex-wrap: wrap; padding-bottom: 1.1rem; margin-bottom: 0.4rem; }
.fre-mast h1 { font-family: Newsreader, Georgia, serif; font-weight: 500; font-size: 2.3rem; line-height: 1.05;
  margin: 0; padding: 0; color: var(--ink); }
.fre-mast p { margin: 0.35rem 0 0; color: var(--muted); font-size: 0.95rem; }
.fre-mast .fre-case { text-align: right; margin-left: auto; }
.fre-mast .fre-case strong { display: block; font-size: 1.02rem; color: var(--ink); font-weight: 600; }
.fre-mast .fre-case span { color: var(--muted); font-size: 0.9rem; }

/* Sidebar policy card */
.fre-policy { border: 1px solid #31465A; border-radius: 0.6rem; padding: 0.85rem 0.95rem; background: #182938; }
.fre-policy .name { font-weight: 600; color: #F2F6FA; line-height: 1.3; }
.fre-policy dl { display: grid; grid-template-columns: auto 1fr; gap: 0.15rem 0.7rem; margin: 0.6rem 0 0.7rem;
  font-size: 0.85rem; }
.fre-policy dt { color: #9FB1C2; }
.fre-policy dd { margin: 0; color: #E6ECF2; font-variant-numeric: tabular-nums; }
.fre-policy .state { font-size: 0.85rem; padding: 0.4rem 0.55rem; border-radius: 0.4rem; line-height: 1.35; }
.fre-policy .state.locked { background: #17392E; color: #BFE6D2; }
.fre-policy .state.open { background: #3C3013; color: #F1DDA9; }
.fre-brand { font-family: Newsreader, Georgia, serif; font-size: 1.35rem; line-height: 1.15; color: #F2F6FA;
  margin: 0 0 0.25rem; }
.fre-brand-sub { color: #9FB1C2; font-size: 0.86rem; margin: 0 0 1.1rem; line-height: 1.4; }

/* Result instrument */
.fre-result { background: var(--surface); border: 1px solid var(--line); border-radius: 0.9rem;
  padding: 1.6rem 1.8rem 1.5rem; border-top: 5px solid var(--tone); margin-bottom: 1.2rem; }
.fre-result.good { --tone: var(--good); --tone-soft: var(--good-soft); }
.fre-result.warn { --tone: var(--warn); --tone-soft: var(--warn-soft); }
.fre-result.bad { --tone: var(--bad); --tone-soft: var(--bad-soft); }
.fre-result .head { display: flex; justify-content: space-between; align-items: flex-start; gap: 2rem; }
.fre-result .head > div:first-child { min-width: 0; }
.fre-result .who { color: var(--muted); margin: 0 0 0.3rem; font-size: 0.95rem; }
.fre-result .class { font-family: Newsreader, Georgia, serif; font-weight: 500; font-size: 2.35rem; line-height: 1.08;
  margin: 0; color: var(--tone); }
.fre-result .why { margin: 0.55rem 0 0; max-width: 58ch; color: var(--ink); }
.fre-result .score { text-align: right; line-height: 1; flex: none; }
.fre-result .score .num { font-family: Newsreader, Georgia, serif; font-size: 4.6rem; font-weight: 400;
  font-variant-numeric: lining-nums tabular-nums; color: var(--ink); letter-spacing: -0.02em; }
.fre-result .score .of { display: block; color: var(--muted); font-size: 0.9rem; margin-top: 0.35rem; white-space: nowrap; }

.fre-scale { position: relative; margin: 2.3rem 0 2.4rem; }
.fre-scale .track { display: flex; height: 12px; border-radius: 6px; overflow: hidden; background: #E9EDF2; }
.fre-scale .zone.below { background: #E3E8EE; }
.fre-scale .zone.meets { background: #BFDDCD; }
.fre-scale .zone.exceeds { background: #7FBF9F; }
.fre-scale .marker { position: absolute; top: -9px; width: 4px; height: 30px; margin-left: -2px; border-radius: 2px;
  background: var(--ink); left: var(--at); animation: fre-arrive 0.9s cubic-bezier(.2,.7,.2,1) both; }
.fre-scale .marker::after { content: attr(data-score); position: absolute; bottom: 100%; left: 50%;
  transform: translateX(-50%); font-weight: 650; font-size: 0.85rem; padding-bottom: 2px; white-space: nowrap;
  font-variant-numeric: tabular-nums; }
.fre-scale .tick { position: absolute; top: 12px; left: var(--at); transform: translateX(-50%);
  padding-top: 9px; font-size: 0.8rem; color: var(--muted); white-space: nowrap; }
.fre-scale .tick::before { content: ""; position: absolute; top: 0; left: 50%; width: 1px; height: 7px; background: #9AA8B5; }
.fre-scale .tick.start { transform: none; } .fre-scale .tick.start::before { left: 0; }
.fre-scale .tick.end { transform: translateX(-100%); } .fre-scale .tick.end::before { left: 100%; }
@keyframes fre-arrive { from { left: 0; opacity: 0; } to { left: var(--at); opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .fre-scale .marker { animation: none; } }

.fre-domains { display: grid; gap: 1.05rem; }
.fre-domain { display: grid; grid-template-columns: minmax(11rem, 1.1fr) 3fr auto; gap: 0.2rem 1.2rem; align-items: center; }
.fre-domain .name { font-weight: 600; }
.fre-domain .status { display: inline-block; margin-left: 0.5rem; font-size: 0.78rem; font-weight: 600;
  padding: 0.1rem 0.5rem; border-radius: 1rem; }
.fre-domain .status.good { background: var(--good-soft); color: var(--good); }
.fre-domain .status.warn { background: var(--warn-soft); color: var(--warn); }
.fre-domain .status.bad { background: var(--bad-soft); color: var(--bad); }
.fre-domain .bar { position: relative; height: 14px; border-radius: 7px; background: #E9EDF2; }
.fre-domain .fill { height: 100%; border-radius: 7px; background: var(--harbor); width: var(--w); }
.fre-domain .fill.warn { background: var(--warn); } .fre-domain .fill.bad { background: var(--bad); }
.fre-domain .minline { position: absolute; top: -4px; bottom: -4px; left: var(--min); width: 2px; background: var(--ink); }
.fre-domain .pts { font-family: Newsreader, Georgia, serif; font-size: 1.45rem; font-variant-numeric: lining-nums tabular-nums;
  text-align: right; min-width: 5.5rem; }
.fre-domain .pts span { font-family: "Public Sans", sans-serif; font-size: 0.85rem; color: var(--muted); }
.fre-domain .basis { grid-column: 2 / 4; font-size: 0.86rem; color: var(--muted); }
.fre-legend { font-size: 0.82rem; color: var(--muted); margin: 1.1rem 0 0; display: flex; align-items: center; gap: 0.5rem; }
.fre-legend i { display: inline-block; width: 2px; height: 14px; background: var(--ink); }

.fre-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
.fre-note { background: var(--surface); border: 1px solid var(--line); border-radius: 0.7rem; padding: 1rem 1.2rem; }
.fre-note h5 { margin: 0 0 0.4rem; font-family: "Public Sans", sans-serif; font-size: 0.92rem; font-weight: 650; color: var(--ink); }
.fre-note p, .fre-note li { margin: 0; color: var(--ink); font-size: 0.95rem; line-height: 1.5; }
.fre-note ul { margin: 0; padding-left: 1.1rem; }
.fre-note.attention { border-left: 4px solid var(--warn); }

.fre-empty { background: var(--surface); border: 1px dashed #B9C4D0; border-radius: 0.9rem; padding: 2.4rem 2rem;
  text-align: center; }
.fre-empty h4 { font-family: Newsreader, Georgia, serif; font-weight: 500; font-size: 1.6rem !important; margin: 0 0 0.4rem; padding: 0; }
.fre-empty p { color: var(--muted); margin: 0 auto; max-width: 52ch; }

@media (max-width: 760px) {
  .fre-domain { grid-template-columns: 1fr auto; }
  .fre-domain .bar { grid-column: 1 / 3; grid-row: 2; }
  .fre-domain .basis { grid-column: 1 / 3; }
  .fre-pair { grid-template-columns: 1fr; }
  .fre-result .head { flex-wrap: wrap; }
  .fre-result .score { text-align: left; }
  .fre-result .score .num { font-size: 3.4rem; }
}
</style>
"""

TONE = {"Exceeds": "good", "Meets": "good", "Approaching": "warn", "Not met": "bad"}


def masthead(name: str, faculty_id: str, year: str) -> str:
    who = escape(name or faculty_id) if (name or faculty_id) else "New evaluation"
    detail = ", ".join(escape(x) for x in ((faculty_id if name else ""), f"review year {year}" if year else "") if x)
    return (f'<div class="fre-mast"><div><h1>Faculty Research Evaluation</h1>'
            f'<p>Annual review of research and scholarship</p></div>'
            f'<div class="fre-case"><strong>{who}</strong><span>{detail}</span></div></div>')


def sidebar_brand() -> str:
    return ('<p class="fre-brand">Research evaluation</p>'
            '<p class="fre-brand-sub">A decision aid for the annual review. It informs the chair\'s written '
            'evaluation; it does not replace it.</p>')


def policy_card(name: str, version: int, stamp: str, locked: bool, approved_by: str) -> str:
    if locked:
        state = f'<div class="state locked">Locked. Approved by {escape(approved_by or "not recorded")}.</div>'
    else:
        state = '<div class="state open">Not locked. Provisional until approved on the Scoring policy tab.</div>'
    return (f'<div class="fre-policy"><div class="name">{escape(name)}</div>'
            f'<dl><dt>Version</dt><dd>{version}</dd><dt>Fingerprint</dt><dd>{escape(stamp)}</dd></dl>{state}</div>')


def result_reason(result: dict, policy: dict) -> str:
    unmet = [d["name"] for d in result["domains"].values() if not d["minimum_met"]]
    if unmet:
        text = f"Minimum expectation not met in {' and '.join(unmet).lower()}."
        if result["approaching"]:
            text += " One minimum short, with a strong score otherwise: flagged for committee attention."
        return text
    if result["class"] == EXCEEDS:
        return "All three minimum expectations are met, and the year stands well above them."
    gap = policy["exceeds_threshold"] - result["total"]
    if gap > 0:
        return (f"All three minimum expectations are met. Exceeds Expectations starts at "
                f"{policy['exceeds_threshold']:g}, {gap:.1f} points away.")
    return ("All three minimum expectations are met. The score is above the Exceeds threshold, but Exceeds also "
            "needs two strong domains.")


def result_instrument(result: dict, policy: dict, who: str) -> str:
    cls, total = result["class"], result["total"]
    tone = "good" if cls in (EXCEEDS, MEETS) else "warn" if result["approaching"] else "bad"
    meets, exceeds = policy["meets_threshold"], policy["exceeds_threshold"]
    at = max(0.0, min(100.0, total))
    rows = []
    for d in result["domains"].values():
        t = TONE[d["status"]]
        basis = f"Minimum met: {d['minimum_basis']}" if d["minimum_met"] else "Minimum not met"
        fill = "" if d["minimum_met"] else f" {t}"
        rows.append(
            f'<div class="fre-domain"><div class="name">{escape(d["name"])}'
            f'<span class="status {t}">{d["status"]}</span></div>'
            f'<div class="bar"><div class="fill{fill}" style="--w:{min(100.0, d["share"] * 100):.1f}%"></div>'
            f'<div class="minline" style="--min:{policy["anchor_share"] * 100:.1f}%"></div></div>'
            f'<div class="pts">{d["score"]:g} <span>/ {d["max"]:g}</span></div>'
            f'<div class="basis">{escape(basis)}</div></div>')
    return (
        f'<div class="fre-result {tone}"><div class="head"><div><p class="who">{escape(who)}</p>'
        f'<p class="class">{cls}</p><p class="why">{escape(result_reason(result, policy))}</p></div>'
        f'<div class="score"><span class="num">{total:g}</span><span class="of">overall score, of 100</span></div></div>'
        f'<div class="fre-scale" role="img" aria-label="Overall score {total:g} of 100. Meets threshold {meets:g}, '
        f'Exceeds threshold {exceeds:g}.">'
        f'<div class="track"><div class="zone below" style="width:{meets}%"></div>'
        f'<div class="zone meets" style="width:{exceeds - meets}%"></div>'
        f'<div class="zone exceeds" style="width:{100 - exceeds}%"></div></div>'
        f'<div class="marker" style="--at:{at}%" data-score="{total:g}"></div>'
        f'<div class="tick start" style="--at:0%">0</div>'
        f'<div class="tick" style="--at:{meets}%">Meets {meets:g}</div>'
        f'<div class="tick" style="--at:{exceeds}%">Exceeds {exceeds:g}</div>'
        f'<div class="tick end" style="--at:100%">100</div></div>'
        f'<div class="fre-domains">{"".join(rows)}</div>'
        f'<p class="fre-legend"><i></i>Points earned by meeting the minimum expectation '
        f'({policy["anchor_share"]:.0%} of each domain). Work above the minimum fills the rest.</p></div>')


def notes_block(strengths: list[str], needs: list[str], notes: list[str], flags: list[str], level: float) -> str:
    strong = ", ".join(strengths) if strengths else f"No domain above {level:.0%} of its points this year."
    weak = ", ".join(needs) if needs else "All minimum expectations are met."
    html = (f'<div class="fre-pair"><div class="fre-note"><h5>Areas of strength</h5><p>{escape(strong)}</p></div>'
            f'<div class="fre-note"><h5>Areas requiring improvement</h5><p>{escape(weak)}</p></div></div>')
    if notes:
        items = "".join(f"<li>{escape(n)}</li>" for n in notes)
        html += f'<div class="fre-note" style="margin-bottom:1rem"><h5>How the outcome was reached</h5><ul>{items}</ul></div>'
    if flags:
        items = "".join(f"<li>{escape(f)}</li>" for f in flags)
        html += f'<div class="fre-note attention" style="margin-bottom:1rem"><h5>For committee attention</h5><ul>{items}</ul></div>'
    return html


def empty_state(title: str, text: str) -> str:
    return f'<div class="fre-empty"><h4>{escape(title)}</h4><p>{escape(text)}</p></div>'
