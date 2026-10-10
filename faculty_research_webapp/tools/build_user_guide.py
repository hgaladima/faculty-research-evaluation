"""Build user_guide.pdf for faculty members and academic administrators.

Run from faculty_research_webapp/:  python -m tools.build_user_guide

Numbers quoted in the guide (weights, thresholds, minimums) are read from the provisional policy, and the worked
example is scored by the engine, so the guide cannot drift from the tool. The screenshots in guide_images/ are
captured by hand from the running app and need re-capturing when the screens change.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import exports
from engine import PROVISIONAL, evaluate, fingerprint
from engine.scenarios import SCENARIOS
from tools.build_excel_calculator import ROWS

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "user_guide.pdf"
IMAGES = Path(__file__).resolve().parents[1] / "guide_images"
NAVY, INK, MUTED = colors.HexColor("#1D4E89"), colors.HexColor("#14202B"), colors.HexColor("#5A6A79")
WIDTH = letter[0] - 1.7 * inch


def build() -> Path:
    p = PROVISIONAL
    regular, bold = exports.pdf_fonts()
    body = ParagraphStyle("body", fontName=regular, fontSize=10.5, leading=15, textColor=INK, spaceAfter=7)
    small = ParagraphStyle("small", parent=body, fontSize=9, leading=12.5, textColor=MUTED)
    cell = ParagraphStyle("cell", parent=body, fontSize=9.5, leading=13, spaceAfter=0)
    head = ParagraphStyle("head", parent=cell, fontName=bold, textColor=colors.white)
    h1 = ParagraphStyle("h1", fontName=bold, fontSize=17, leading=21, textColor=NAVY, spaceBefore=6, spaceAfter=9, keepWithNext=1)
    h2 = ParagraphStyle("h2", fontName=bold, fontSize=12.5, leading=16, textColor=INK, spaceBefore=9, spaceAfter=5, keepWithNext=1)
    title = ParagraphStyle("title", fontName=bold, fontSize=26, leading=31, textColor=NAVY, spaceAfter=10)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=2, spaceAfter=3)

    def para(text: str, style=body) -> Paragraph:
        return Paragraph(text, style)

    def bullets(items: list[str]) -> list:
        return [Paragraph(text, bullet, bulletText="•") for text in items] + [Spacer(1, 4)]

    def steps(items: list[str]) -> list:
        return [Paragraph(text, bullet, bulletText=f"{i}.") for i, text in enumerate(items, 1)] + [Spacer(1, 4)]

    def table(rows: list[list[str]], widths: list[float]) -> Table:
        data = [[Paragraph(str(v), head if i == 0 else cell) for v in row] for i, row in enumerate(rows)]
        t = Table(data, colWidths=[w * WIDTH for w in widths], repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D1DA")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        return t

    def picture(name: str, caption: str) -> list:
        path = IMAGES / name
        if not path.exists():
            return []
        w, h = ImageReader(str(path)).getSize()
        return [KeepTogether([Image(str(path), width=WIDTH, height=WIDTH * h / w), Spacer(1, 3), para(caption, small)]),
                Spacer(1, 6)]

    w, anchor = p["weights"], p["anchor_share"]
    floor = anchor * 100
    example = next(s for s in SCENARIOS if s["name"].startswith("S14"))
    r = evaluate(example, p)
    example_rows = [["Domain", "Units earned", "Points at the minimum", "Excellence points", "Domain score", "Maximum"]]
    for d in r["domains"].values():
        example_rows.append([d["name"], f"{d['units']:.2f}", f"{d['anchor']:.1f}", f"{d['excellence']:.2f}", f"{d['score']:g}",
                             f"{d['max']:g}"])
    example_rows.append(["Overall", "", "", "", f"{r['total']:g}", "100"])

    story = [
        Spacer(1, 1.6 * inch),
        para("Faculty Research Evaluation", title),
        para("User guide for faculty members, department chairs and review committees", h2),
        Spacer(1, 0.3 * inch),
        para(f"Version of {date.today():%d %B %Y}. Describes the web application and the Excel calculator under the "
             f"provisional scoring policy (fingerprint {fingerprint(p)})."),
        Spacer(1, 0.25 * inch),
        table([["Please read first"],
               ["<b>This tool is a decision aid.</b> It organises a year of research activity and applies one set of rules "
                "to everyone. It does not replace the chair's written evaluation or the faculty member's narrative on "
                "quality, impact and value."],
               ["<b>The scoring policy is provisional.</b> Its thresholds and criteria are interim defaults. They become "
                "School policy only when the annual review committee adopts them."]], [1.0]),
        PageBreak(),

        para("1. What the tool does", h1),
        para("You enter a faculty member's publications, grants and presentations for one evaluation year. The tool returns:"),
        *bullets(["a research score from 0 to 100;",
                  "a classification: <b>Exceeds Expectations</b>, <b>Meets Expectations</b> or <b>Does Not Meet Expectations</b>;",
                  "which minimum expectations were met, and on what basis;",
                  "a line-by-line account of how every point was earned;",
                  "a printable report."]),
        para("There are two versions. They apply the same rules and give the same result for the same entries."),
        table([["", "Web application", "Excel calculator"],
               ["Best for", "Chairs and committees reviewing several faculty members", "A faculty member preparing their own review, or anyone without the web app installed"],
               ["Saves evaluations", "Yes, in a list you can reopen", "One workbook per person; save a copy"],
               ["Scoring policy", "Edited, previewed, approved and locked on the Scoring policy tab", "On a protected Settings sheet"],
               ["Report", "PDF or Excel download", "Printable Report sheet"]], [0.2, 0.4, 0.4]),

        para("2. Before you start", h1),
        para("Gather the following for the evaluation year:"),
        *bullets(["the assigned research effort (percent) and the months active, after approved leave;",
                  "each publication, with its journal, the faculty member's authorship position and its DOI;",
                  "each grant proposal submitted, each new award, and each continuing funded project, with role and total amount;",
                  "each presentation, with the meeting and the faculty member's role;",
                  "editorial roles, manuscript reviews, grant review panels and sessions chaired."]),

        para("3. How the score works", h1),
        para(f"Research is scored in three domains: publications ({w['P']:g} points), grants and contracts ({w['G']:g}) "
             f"and presentations ({w['R']:g})."),
        para(f"<b>Minimums come first.</b> Each domain has a minimum expectation. Meeting it earns {anchor:.0%} of that domain's "
             f"points. Work above the minimum earns the remaining {1 - anchor:.0%}, in proportion to its quantity and quality. "
             f"A faculty member who meets all three minimums and nothing more scores exactly {floor:g}."),
        table([["Domain", "Minimum expectation under the provisional policy"],
               ["Publications", f"{p['pub_min_count']} peer-reviewed publications in the year, in journals that are not questionable. "
                                "A scholarly book counts as two; one book chapter may count as one."],
               ["Grants and contracts", "One qualifying grant activity: a competitive proposal submitted as PI, MPI, Co-PI or Co-I "
                                        "(internal proposals count), a new award in one of those roles, or a continuing funded project in one of those roles."],
               ["Presentations", "One conference presentation at a credible venue, as presenter or as mentor of a student presenter. "
                                 "Institutional talks, outreach and seminars earn credit but do not meet the minimum."]], [0.24, 0.76]),
        Spacer(1, 6),
        para("<b>Classification.</b>"),
        *bullets(["<b>Does Not Meet Expectations</b>: any minimum is unmet, whatever the score.",
                  f"<b>Meets Expectations</b>: all three minimums are met (which means a score of at least {p['meets_threshold']:g}).",
                  f"<b>Exceeds Expectations</b>: all minimums are met, the score is at least {p['exceeds_threshold']:g}, and at least two "
                  f"domains are at {p['breadth_level']:.0%} or more of their points. A new competitive award in the largest size band "
                  f"as PI or MPI also qualifies, provided the score is at least {p['distinction_min_total']:g}."]),
        para(f"<b>Approaching.</b> When exactly one minimum is unmet and the score is at least {p['approaching_threshold']:g}, the result is "
             f"still Does Not Meet Expectations, but it is shown in amber and flagged for the committee."),
        para("Worked example", h2),
        para(f"The example profile “{escape(example['name'][4:])}” has three lead-author articles, two policy briefs, a technical "
             f"report, a major award as PI, an oral presentation and an outreach talk."),
        table(example_rows, [0.26, 0.14, 0.17, 0.15, 0.14, 0.14]),
        Spacer(1, 4),
        para(f"Result: <b>{r['class']}</b>, {r['total']:g} of 100. {escape(r['notes'][0]) if r['notes'] else ''}"),

        para("4. Using the web application", h1),
        para("Start it by double-clicking <b>run_app.bat</b> in the <i>faculty_research_webapp</i> folder. It opens in your browser. "
             "It runs on your computer only; other computers on the network cannot reach it."),
        *steps(["<b>Faculty</b> tab: name, Faculty ID, evaluation year, assigned research effort, months active, and whether this is the first year.",
                "<b>Publications</b>, <b>Grants</b> and <b>Presentations</b> tabs: one row per item. Click a cell and choose from the list. "
                "Add a row by typing in the empty row at the bottom.",
                "<b>Other activity</b> tab: editorial work, grant review panels, counts for the year, and the three-year rolling window if needed.",
                "<b>Results</b> tab: the classification, the score and the explanation. Press <b>Save evaluation</b>, or download the report.",
                "To try it first, choose one of the 22 example profiles in the left panel and press <b>Load example profile</b>."]),
        *picture("publications.png", "The Publications tab with an example profile loaded. The left panel shows the scoring policy in force."),
        *picture("results.png", "The Results tab. The vertical line on each bar marks the points earned by meeting the minimum."),
        para("If an entry is incomplete, the Results tab lists what is missing and does not show a score until it is fixed."),

        para("5. Using the Excel calculator", h1),
        para("Open <b>faculty_research_calculator.xlsx</b>. It contains no macros. Save a copy for each faculty member."),
        *steps(["<b>Faculty</b> sheet: the same information as the Faculty tab of the web application.",
                "<b>Publications</b>, <b>Grants</b> and <b>Presentations</b> sheets: one row per item, in the yellow cells. "
                f"There is room for {ROWS['pubs']} publications, {ROWS['grants']} grants and {ROWS['pres']} presentations.",
                "<b>Other</b> sheet: editorial work, review panels, counts and the rolling window.",
                "<b>Dashboard</b> sheet: the result. It updates as you type.",
                "<b>Report</b> sheet: a one-page summary. Use File &gt; Print, or File &gt; Save As &gt; PDF."]),
        *bullets(["Yellow cells are for entry. Grey cells are calculated and locked.",
                  "If a row is started but not finished, the grey <b>Check this row</b> column says what is missing, and the Dashboard shows "
                  "<b>Incomplete</b> until it is completed.",
                  "The <b>Note</b> column explains anything unusual about a row, such as a duplicate DOI or an entry not yet verified."]),

        para("6. Choosing the right values", h1),
        para("Journal tier", h2),
        para("The tier is a proxy for the standing of the journal, not a measure of the article. The committee may reassign a tier with a stated reason."),
        table([["Tier", "Definition", "Effect on an article's credit"],
               ["Tier 1", "Top quartile (Q1) of its subject category in Journal Citation Reports or Scimago, or the flagship journal of a major society in the field", f"× {p['journal_tier_mult'][1]:g}"],
               ["Tier 2", "Second quartile (Q2)", f"× {p['journal_tier_mult'][2]:g}"],
               ["Tier 3", "Any other peer-reviewed journal indexed in MEDLINE, Scopus or Web of Science", f"× {p['journal_tier_mult'][3]:g}"],
               ["Questionable", "No verifiable peer review, or on a list the committee treats as predatory", "No credit; does not count toward the minimum"],
               ["Not yet verified", "Use when the tier has not been checked", "Treated as Tier 3 and flagged"]], [0.2, 0.52, 0.28]),
        para("Authorship", h2),
        para(f"Sole, first, senior (last) and corresponding authors receive full credit. A second author receives "
             f"{p['author_role_mult']['second']:g} of it, and any other coauthor {p['author_role_mult']['coauthor']:g}."),
        para("Venue tier for presentations", h2),
        table([["Tier", "Definition"],
               ["Tier A", "Major national or international meeting of a recognised society, with competitive peer-reviewed abstract selection"],
               ["Tier B", "Regional or state meeting of a recognised society, or a national meeting with light review"],
               ["Tier C", "Local meeting, or limited review"],
               ["Questionable", "Doubtful academic credibility. No credit"]], [0.2, 0.8]),
        Spacer(1, 4),
        para("Quality and selectivity count more than geography: a strong national meeting can rank above a weak international one."),
        para("Grants", h2),
        *bullets([f"<b>Total amount</b> is the total for the full project period. Under ${p['amount_bands']['minor_max']:,.0f} is minor; "
                  f"${p['amount_bands']['large_min']:,.0f} or more is large; in between is major.",
                  "<b>Status.</b> “Submitted” for a proposal that is pending or was not funded. “Awarded this year” for a new award. "
                  "“Active” for a project awarded in an earlier year.",
                  "A proposal submitted <b>and</b> funded in the same year is one row: “Awarded this year”, with “Also submitted this year” set to Yes. "
                  "It earns credit once, as an award.",
                  "<b>Competitive</b>: answer No for sole-source contracts."]),
        para("Months active and leave", h2),
        para("Subtract approved medical, parental and other non-research leave. Count sabbatical and research leave as active months."),

        para("7. Special circumstances", h1),
        table([["Situation", "What the tool does"],
               ["First-year faculty", "The publication minimum is halved. A documented proposal in development meets the grant minimum."],
               ["Reduced research assignment or part-year", f"Expectations are prorated from the standard research assignment of {p['standard_research_effort']:g}%. "
                                                            f"At half the standard expectation or less, documented activity (for example a seminar, or a proposal in development) "
                                                            "meets the grant and presentation minimums."],
               ["No research assignment, or absent all year", "The result is Not Evaluated, and the case is referred to the committee."],
               ["A strong record but a thin year", f"The three-year rolling window can meet one minimum, if the two prior years were strong and there is work "
                                                   "in the pipeline (a manuscript under review, a proposal in development, or an abstract submitted). "
                                                   "Enter the prior-year figures on the Other activity tab."],
               ["An item credited last year", "Mark it “Credited in a prior year”. It is listed but earns nothing."],
               ["Something not yet checked", "Choose “Not yet verified”. The entry is scored the least generous way and flagged."]], [0.3, 0.7]),

        para("8. Reading the result", h1),
        *bullets(["<b>Green</b>: a minimum met, or the domain at a high level. <b>Amber</b>: approaching. <b>Red</b>: not met.",
                  "<b>How the outcome was reached</b> lists every allowance or proration that was applied.",
                  "<b>For committee attention</b> lists things a person should look at: an unmet minimum alongside a strong score, "
                  "entries not yet verified, duplicate entries, or several articles in questionable venues.",
                  "<b>How the points were earned</b> shows each entry, how it was credited and its units. Caps appear as their own lines."]),
        para("The tool does not judge the research itself. Research awards, mentoring, community-engaged work and evaluator notes can be "
             "recorded and are printed on the report, but they do not change the score."),

        para("9. The scoring policy", h1),
        para("Every threshold and criterion is a setting. In the web application they are on the <b>Scoring policy</b> tab; in Excel, on the "
             "<b>Settings</b> sheet. The full list, with the source of each value, is in the document <i>PROVISIONAL_POLICY.md</i>."),
        *bullets(["The policy belongs to the annual review committee. It is meant to be set once for the year, approved and locked, "
                  "so that everyone is rated under the same rules.",
                  "Before a change is saved, the web application shows how the 22 example profiles and any saved evaluations would be reclassified.",
                  "Every report carries the policy name, its version and a short fingerprint of its settings. Two reports with the same fingerprint were scored under identical rules.",
                  "The Excel Dashboard states whether its settings still match the shipped policy."]),
        *picture("policy.png", "The Scoring policy tab. Settings are editable until the policy is approved and locked."),

        para("10. Saving, reports and privacy", h1),
        *bullets(["The web application saves evaluations on the computer it runs on, in the <i>data</i> folder beside the application. "
                  "These are personnel records. There is no login, so use it only on a computer authorised evaluators use.",
                  "Saving over a different evaluation with the same name asks for confirmation.",
                  "The Excel calculator stores nothing outside the workbook you save."]),

        para("11. Questions and answers", h1),
        table([["Question", "Answer"],
               ["Why is the result Does Not Meet when the score is high?", "A minimum is unmet. The classification never lets a strong domain hide an unmet minimum in another; the case is flagged for the committee instead."],
               [f"Why is a score of {p['exceeds_threshold']:g} or more only Meets?", f"Exceeds also needs two domains at {p['breadth_level']:.0%} or more of their points."],
               ["Why does one domain score look 0.1 off?", "The overall score is the rounded true total. Where the three rounded domain scores would not add up to it, one is shown 0.1 higher or lower."],
               ["A coauthored poster did not meet the presentation minimum.", "The minimum requires presenting, or mentoring a student presenter. The poster still earns credit."],
               ["The same paper appears twice.", "Enter its DOI on both rows. It is counted once, and the row is noted."],
               ["Do the web application and Excel always agree?", "They were checked against each other on the 22 example profiles and on several hundred generated cases; see <i>faculty_evaluation_validation.xlsx</i>. Excel always rounds half up."]], [0.36, 0.64]),

        para("12. Limits", h1),
        *bullets(["The thresholds were set using hypothetical profiles. They have not yet been tested against real past reviews.",
                  "Journal and venue tiers depend on who assigns them. The committee should keep a list.",
                  "Counts such as proposals in development are entered by the user; the tool cannot verify them.",
                  "Rank, discipline differences in funding, and a change of research area are not modelled. They are for the committee and the narrative."]),
    ]

    def footer(canvas, doc) -> None:
        canvas.setFont(regular, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(0.85 * inch, 0.5 * inch, "Faculty Research Evaluation: user guide")
        canvas.drawRightString(letter[0] - 0.85 * inch, 0.5 * inch, f"Page {doc.page}")

    doc = SimpleDocTemplate(str(OUTPUT), pagesize=letter, leftMargin=0.85 * inch, rightMargin=0.85 * inch,
                            topMargin=0.8 * inch, bottomMargin=0.8 * inch, title="Faculty Research Evaluation: user guide",
                            author="Faculty Research Evaluation project")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUTPUT


if __name__ == "__main__":
    print(f"Wrote {build()}")
