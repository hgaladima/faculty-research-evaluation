"""Visual layer: the stylesheet and the hand-built HTML pieces (masthead, policy card, result instrument)."""
from __future__ import annotations

from html import escape

from engine.research_eval import DOES_NOT_MEET, EXCEEDS, MEETS

STATUS_COLOURS = """
  --good: #1F7A55; --good-soft: #E3F1EA; --warn: #A9690A; --warn-soft: #F8EDD8;
  --bad: #B0362D; --bad-soft: #F7E4E1;"""
THEME_VARS = {"--ink": "theme.textColor", "--line": "theme.borderColor", "--paper": "theme.backgroundColor",
              "--surface": "theme.secondaryBackgroundColor", "--harbor": "theme.primaryColor",
              "--side-surface": "theme.sidebar.secondaryBackgroundColor", "--side-line": "theme.sidebar.borderColor",
              "--side-text": "theme.sidebar.textColor"}
FALLBACKS = {"--ink": "#14202B", "--line": "#D5DCE4", "--paper": "#F3F5F8", "--surface": "#FFFFFF",
             "--harbor": "#1D4E89", "--side-surface": "#1C2E3E", "--side-line": "#31465A", "--side-text": "#E6ECF2"}


def stylesheet(get_option) -> str:
    """Build the stylesheet, taking base colours from the Streamlit theme (.streamlit/config.toml)."""
    base = "".join(f"{var}: {get_option(key) or FALLBACKS[var]}; " for var, key in THEME_VARS.items())
    return "<style>:root { " + base + STATUS_COLOURS + " }" + RULES + "</style>"


RULES = """
:root { --muted: color-mix(in srgb, var(--ink) 68%, var(--paper));
  --track: color-mix(in srgb, var(--ink) 9%, var(--surface));
  --side-muted: color-mix(in srgb, var(--side-text) 65%, var(--side-surface)); }
.block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1180px; }
/* A hosted deployment fills the header with an opaque toolbar; clear it */
.stApp:has([data-testid="stHeader"]:not(:empty)) .block-container { padding-top: 4.75rem; }
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
.fre-policy { border: 1px solid var(--side-line); border-radius: 0.6rem; padding: 0.85rem 0.95rem;
  background: var(--side-surface); }
.fre-policy .name { font-weight: 600; color: var(--side-text); line-height: 1.3; }
.fre-policy dl { display: grid; grid-template-columns: auto 1fr; gap: 0.15rem 0.7rem; margin: 0.6rem 0 0.7rem;
  font-size: 0.85rem; }
.fre-policy dt { color: var(--side-muted); }
.fre-policy dd { margin: 0; color: var(--side-text); font-variant-numeric: tabular-nums; }
.fre-policy .state { font-size: 0.85rem; padding: 0.4rem 0.55rem; border-radius: 0.4rem; line-height: 1.35; }
.fre-policy .state.locked { background: color-mix(in srgb, var(--good) 40%, var(--side-surface)); color: var(--side-text); }
.fre-policy .state.open { background: color-mix(in srgb, var(--warn) 40%, var(--side-surface)); color: var(--side-text); }
.fre-brand { font-family: Newsreader, Georgia, serif; font-size: 1.35rem; line-height: 1.15; color: var(--side-text);
  margin: 0 0 0.25rem; }
.fre-brand-sub { color: var(--side-muted); font-size: 0.86rem; margin: 0 0 1.1rem; line-height: 1.4; }

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
.fre-scale .track { position: relative; height: 12px; border-radius: 6px; background: var(--track); overflow: hidden; }
.fre-scale .reached { height: 100%; width: var(--at); background: var(--tone); opacity: 0.32; }
.fre-scale .marker { position: absolute; top: -9px; width: 4px; height: 30px; margin-left: -2px; border-radius: 2px;
  background: var(--ink); left: var(--at); animation: fre-arrive 0.9s cubic-bezier(.2,.7,.2,1) both; }
.fre-scale .marker::after { content: attr(data-score); position: absolute; bottom: 100%; left: 50%;
  transform: translateX(-50%); font-weight: 650; font-size: 0.85rem; padding-bottom: 2px; white-space: nowrap;
  font-variant-numeric: tabular-nums; }
.fre-scale .tick { position: absolute; top: 12px; left: var(--at); transform: translateX(-50%);
  padding-top: 9px; font-size: 0.8rem; color: var(--muted); white-space: nowrap; }
.fre-scale .tick::before { content: ""; position: absolute; top: 0; left: 50%; width: 1px; height: 7px; background: var(--muted); }
.fre-scale .tick.low { padding-top: 26px; } .fre-scale .tick.low::before { height: 24px; }
.fre-scale .tick.threshold::after { content: ""; position: absolute; top: -12px; left: 50%; width: 2px; height: 12px;
  margin-left: -1px; background: var(--surface); }
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
.fre-domain .bar { position: relative; height: 14px; border-radius: 7px; background: var(--track); }
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

.fre-empty { background: var(--surface); border: 1px dashed var(--muted); border-radius: 0.9rem; padding: 2.4rem 2rem;
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
  .fre-scale { margin-bottom: 3.4rem; }
  .fre-scale .tick.exceeds { padding-top: 26px; }
  .fre-scale .tick.exceeds::before { height: 24px; }
}
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
    """One or two sentences saying why the engine assigned this class."""
    basis, total = result["class_basis"], result["total"]
    exceeds, meets = policy["exceeds_threshold"], policy["meets_threshold"]
    met = "All three minimum expectations are met."
    if basis == "minimum_unmet":
        unmet = [d["name"].lower() for d in result["domains"].values() if not d["minimum_met"]]
        text = f"Minimum expectation not met in {' and '.join(unmet)}."
        if result["approaching"]:
            text += (f" Only one minimum is unmet and the score is at least {policy['approaching_threshold']:g}, "
                     f"so this is flagged for committee review.")
        return text
    if basis == "below_meets_threshold":
        return f"{met} The score of {total:g} is still below the Meets threshold of {meets:g}."
    if basis == "exceeds_on_score":
        return f"{met} The score is at or above the Exceeds threshold of {exceeds:g}."
    if basis == "exceeds_on_award":
        return (f"{met} Exceeds Expectations is awarded for a new competitive large award as PI or MPI; "
                f"the score itself is below the Exceeds threshold of {exceeds:g}.")
    if basis == "meets_lacks_breadth":
        return (f"{met} The score reaches the Exceeds threshold of {exceeds:g}, but Exceeds also needs two domains "
                f"at {policy['breadth_level']:.0%} of their points.")
    return f"{met} Exceeds Expectations starts at {exceeds:g}, {exceeds - total:.1f} points away."


def scale_ticks(meets: float, exceeds: float) -> str:
    """Threshold labels for the 0-100 scale, dropped to a second row or omitted where they would collide."""
    low = " low" if exceeds - meets < 14 else ""
    ticks = "" if meets < 8 else '<div class="tick start" style="--at:0%">0</div>'
    ticks += f'<div class="tick threshold" style="--at:{meets}%">Meets {meets:g}</div>'
    ticks += f'<div class="tick threshold exceeds{low}" style="--at:{exceeds}%">Exceeds {exceeds:g}</div>'
    if exceeds <= 88:
        ticks += '<div class="tick end" style="--at:100%">100</div>'
    return ticks


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
        f'<div class="track"><div class="reached" style="--at:{at}%"></div></div>'
        f'<div class="marker" style="--at:{at}%" data-score="{total:g}"></div>'
        f'{scale_ticks(meets, exceeds)}</div>'
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
