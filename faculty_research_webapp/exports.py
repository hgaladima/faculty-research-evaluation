"""Build the downloadable evaluation report as an Excel workbook or a PDF."""
from __future__ import annotations

import io
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INFO_LABELS = [("name", "Faculty member"), ("faculty_id", "Faculty ID"), ("rank", "Academic rank"),
               ("department", "Department"), ("appointment", "Appointment type"),
               ("evaluation_year", "Evaluation year"), ("research_effort", "Assigned research effort (%)"),
               ("months_active", "Months active")]
DISCLAIMER = ("Decision aid only. The scoring policy is provisional until adopted by the annual review "
              "committee; the chair's written evaluation and the faculty narrative remain the record.")


def policy_stamp(result: dict, meta: dict) -> str:
    status = "locked" if meta.get("locked") else "not locked"
    who = f", approved by {meta['approved_by']}" if meta.get("approved_by") else ""
    return (f"{result['policy']['name']} | version {meta.get('version', 1)} | "
            f"fingerprint {result['policy']['fingerprint']} | {status}{who}")


def summary_rows(result: dict) -> list[list]:
    rows = [["Research domain", "Points earned", "Maximum points", "Minimum met", "Performance"]]
    for d in result["domains"].values():
        rows.append([d["name"], d["score"], d["max"], "Yes" if d["minimum_met"] else "No", d["status"]])
    rows.append(["Overall research score", result["total"], 100, "", result["class"]])
    return rows


def breakdown_rows(result: dict) -> list[list]:
    rows = [["Domain", "Item", "How it was credited", "Units", "Counts toward minimum"]]
    for line in result["breakdown"]:
        rows.append([result["domains"][line["domain"]]["name"], line["item"], line["detail"],
                     round(line["units"], 3), line["toward_minimum"] or ""])
    return rows


def conversion_rows(result: dict) -> list[list]:
    rows = [["Domain", "Units earned", "Benchmark units", "Units for full excellence", "Points at the minimum",
             "Excellence points", "Domain points", "Basis for the minimum"]]
    for d in result["domains"].values():
        rows.append([d["name"], round(d["units"], 3), round(d["benchmark_units"], 3), round(d["saturation"], 3),
                     round(d["anchor"], 2), round(d["excellence"], 2), d["score"], d["minimum_basis"] or "not met"])
    return rows


def excel_bytes(info: dict, result: dict, policy: dict, meta: dict, context: dict) -> bytes:
    wb = Workbook()
    head_font, head_fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3864")

    def table(ws, rows, start):
        for r, row in enumerate(rows, start):
            for c, value in enumerate(row, 1):
                cell = ws.cell(row=r, column=c, value=value)
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                if r == start:
                    cell.font, cell.fill = head_font, head_fill
        return start + len(rows) + 1

    ws = wb.active
    ws.title = "Summary"
    ws["A1"] = "Faculty Research Evaluation Report"
    ws["A1"].font = Font(bold=True, size=14)
    r = 3
    for key, label in INFO_LABELS:
        ws.cell(row=r, column=1, value=label).font = Font(bold=True)
        ws.cell(row=r, column=2, value=info.get(key, ""))
        r += 1
    r = table(ws, summary_rows(result), r + 1)
    for title, items in (("Explanation", result["notes"]), ("For committee attention", result["flags"]),
                         ("Input errors", result["errors"])):
        if items:
            ws.cell(row=r, column=1, value=title).font = Font(bold=True)
            for item in items:
                r += 1
                ws.cell(row=r, column=1, value=item)
            r += 2
    for label, text in context.items():
        if text:
            ws.cell(row=r, column=1, value=f"{label} (recorded, not scored)").font = Font(bold=True)
            ws.cell(row=r + 1, column=1, value=text)
            r += 3
    ws.cell(row=r, column=1, value="Scoring policy").font = Font(bold=True)
    ws.cell(row=r + 1, column=1, value=policy_stamp(result, meta))
    ws.cell(row=r + 2, column=1, value=DISCLAIMER)
    for col, width in zip("ABCDE", (34, 16, 16, 14, 28)):
        ws.column_dimensions[col].width = width

    if result["scored"]:
        ws2 = wb.create_sheet("Points breakdown")
        nxt = table(ws2, conversion_rows(result), 1)
        table(ws2, breakdown_rows(result), nxt + 1)
        for i, width in enumerate((24, 34, 52, 16, 20, 16, 14, 40), 1):
            ws2.column_dimensions[get_column_letter(i)].width = width

    ws3 = wb.create_sheet("Policy")
    rows = [["Setting", "Value"]]
    for key in sorted(policy):
        value = policy[key]
        if isinstance(value, dict):
            rows += [[f"{key}.{k}", v] for k, v in value.items()]
        else:
            rows.append([key, ", ".join(value) if isinstance(value, list) else value])
    table(ws3, rows, 1)
    ws3.column_dimensions["A"].width, ws3.column_dimensions["B"].width = 44, 40

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def pdf_bytes(info: dict, result: dict, meta: dict, context: dict) -> bytes:
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9.5, leading=12.5)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10, textColor=colors.grey)
    cell = ParagraphStyle("cell", parent=body, fontSize=8, leading=10)
    grid = TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                       ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")),
                       ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                       ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "TOP")])
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            title="Faculty Research Evaluation Report")
    story = [Paragraph("Faculty Research Evaluation Report", styles["Title"])]
    info_rows = [[label, str(info.get(key, "") or "")] for key, label in INFO_LABELS]
    t = Table(info_rows, colWidths=[2.3 * inch, 4.6 * inch])
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold")]))
    story += [t, Spacer(1, 10)]
    story.append(Paragraph(f"<b>Research evaluation: {result['class']}</b>"
                           + (f" &nbsp; Overall research score: {result['total']} / 100" if result["scored"] else ""),
                           styles["Heading3"]))
    if result["scored"]:
        t = Table(summary_rows(result), colWidths=[2.3 * inch, 1.1 * inch, 1.2 * inch, 1.0 * inch, 1.5 * inch])
        t.setStyle(grid)
        story += [t, Spacer(1, 8)]
    for title, items in (("Explanation of the outcome", result["notes"]),
                         ("For committee attention", result["flags"]), ("Input errors", result["errors"])):
        if items:
            story.append(Paragraph(f"<b>{title}</b>", body))
            story += [Paragraph(f"&bull; {escape(item)}", body) for item in items]
            story.append(Spacer(1, 6))
    if result["scored"]:
        story.append(Paragraph("<b>How the points were earned</b>", body))
        rows = [[Paragraph(escape(str(v)), cell) for v in row] for row in conversion_rows(result)]
        t = Table(rows, colWidths=[1.1 * inch, 0.6 * inch, 0.75 * inch, 0.8 * inch, 0.7 * inch, 0.75 * inch,
                                   0.6 * inch, 1.8 * inch], repeatRows=1)
        t.setStyle(grid)
        story += [t, Spacer(1, 6)]
        rows = [[Paragraph(escape(str(v)), cell) for v in row[:4]] for row in breakdown_rows(result)]
        t = Table(rows, colWidths=[1.25 * inch, 1.9 * inch, 3.35 * inch, 0.6 * inch], repeatRows=1)
        t.setStyle(grid)
        story += [t, Spacer(1, 8)]
    for label, text in context.items():
        if text:
            story += [Paragraph(f"<b>{label}</b> (recorded, not scored)", body), Paragraph(escape(text), body),
                      Spacer(1, 6)]
    story += [Spacer(1, 10), Paragraph(f"Scoring policy: {escape(policy_stamp(result, meta))}", small),
              Paragraph(DISCLAIMER, small), Spacer(1, 22),
              Paragraph("Evaluator signature: ______________________________ &nbsp;&nbsp; Date: ______________", body)]
    doc.build(story)
    return buf.getvalue()
