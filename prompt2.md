# Phase 2: Develop Excel and Web-Based Faculty Research Evaluation Tools

## Background

We have completed the initial development of a comprehensive faculty research evaluation algorithm for a School of Public Health.

The algorithm evaluates faculty research productivity, including publications, grants and contracts, scientific presentations, and other recognized scholarly activities.

Three Python files have been developed:

1. **research_eval.py** — Contains the complete research evaluation scoring engine.
2. **scenarios.py** — Contains 22 hypothetical faculty profiles used to test the algorithm.
3. **sensitivity.py** — Performs sensitivity analyses under alternative scoring assumptions.

These files reproduce the numerical results presented in the research evaluation report.

## Objective

I would now like to move from algorithm development to practical implementation.

Your task is to convert the existing Python algorithm into:

1. **A scoring policy (settings) page** where the thresholds and criteria are set, approved and locked.
2. **A professional, user-friendly Excel calculator** with a faculty data-entry form and automated scoring.
3. **A prototype web application** with an intuitive interface for entering faculty research information and generating evaluation results.

Conversion to SAS is out of scope for this phase.

The goal is to create tools that faculty members, department chairs, and evaluation committees can use without programming experience.

**Important: Do not change the scoring rules, weights, thresholds, or evaluation classifications without explicitly identifying and justifying the proposed modification.**

**Provisional defaults.** Most open items in `REVIEW_FINDINGS.md` need a decision from the annual review committee. Until the committee decides, apply defaults based on the Old Dominion University Faculty Handbook and on practice typical of American universities. Record every threshold and criterion applied, with its source and the review finding it answers, in `PROVISIONAL_POLICY.md`. The original Phase 1 rules must remain available as a selectable policy so that the Phase 1 results can still be reproduced exactly.

---

## PART 1: Scoring Policy (Settings) Page

Provide a settings page in the web application, and a protected Settings sheet in the Excel workbook, where the thresholds and criteria used by the scoring engine are entered.

The policy belongs to the committee, not to the individual evaluator. Two evaluators must not be able to rate the same faculty member under different rules.

### Requirements

**A. Contents**

Expose every value the engine uses, grouped in plain language:

- Domain weights and the share of points earned at the minimum.
- Classification thresholds and the rule for Exceeds Expectations.
- Minimum expectations for publications, grants and presentations, and who or what satisfies each.
- Adjustments for research effort, leave, first-year faculty and the three-year rolling window.
- Unit values, multipliers and caps for every activity type.
- Counting rules (duplicates, prior-year credit, award size bands, rounding).

**B. Control**

- The policy is set once per evaluation year by an authorised person, then locked.
- A locked policy is read-only. Unlocking requires a recorded reason.
- Every change is logged with who made it, when, and what changed.
- Settings are checked on save (for example, weights sum to 100 and thresholds are in order).

**C. Traceability**

- Every evaluation report shows the policy name, version and a fingerprint of the settings that produced it.
- Opening a saved evaluation made under a different policy shows a notice.

**D. Preview before saving**

Before a change is saved, show how the 22 test scenarios, and any saved evaluations, would be reclassified under the new settings.

**E. Presets**

Ship two presets: the provisional policy (the default) and the original Phase 1 policy.

---

## PART 2: Develop a User-Friendly Excel Faculty Research Evaluation Calculator

Create a professional Excel workbook that allows users to enter faculty research information and automatically generate evaluation scores.

**The workbook should be fully functional, not simply a template or mock-up.**

### A. Faculty Information

Include fields for:

- Faculty ID or name.
- Academic rank.
- Department.
- Evaluation year.
- Faculty appointment type.
- Assigned research effort.
- Applicable evaluation adjustments.

### B. Research Data Entry

Organize the input form into clearly labeled sections.

**Section 1: Publications**

Allow users to enter individual publications, including:

- Publication title.
- Journal name.
- Publication year.
- Publication type.
- Peer-reviewed status.
- Journal impact factor, if applicable.
- Journal quartile ranking.
- Faculty authorship position.
- Faculty contribution.
- Other relevant variables required by the scoring algorithm.

The system should automatically calculate publication points and subtotals.

**Section 2: Grants and Contracts**

Allow users to enter individual grant applications and awards.

Fields should include:

- Grant title.
- Funding agency.
- Funding category.
- Application date.
- Award status.
- Total award amount.
- Faculty-specific award amount.
- Faculty role (PI, Co-PI, Co-I, collaborator).
- Competitive versus noncompetitive funding.
- Internal versus external funding.
- Other scoring variables required by the algorithm.

Automatically calculate grant application and award points.

**Section 3: Scientific Presentations**

Allow users to enter individual presentations.

Include:

- Presentation title.
- Conference name.
- Conference location.
- Conference level (international, national, regional, etc.).
- Presentation type.
- Peer-reviewed abstract status.
- Invited versus submitted presentation.
- Faculty role.
- Conference prestige or quality indicators, when supported by the algorithm.

Automatically calculate presentation points.

**Section 4: Other Scholarly Activities**

Include additional scholarly activities recognized by the evaluation framework.

### C. Automated Scoring Dashboard

Create a separate worksheet displaying:

| Research Domain | Points Earned | Maximum Points | Performance |
|---|---:|---:|---|
| Publications | XX | 50 | Meets Expectations |
| Grants and Contracts | XX | 35 | Exceeds Expectations |
| Presentations | XX | 15 | Meets Expectations |
| **Overall Research Score** | **XX** | **100** | **Meets Expectations** |

Use the actual weights and thresholds from the Python scoring engine rather than assuming the illustrative values above.

The dashboard should include:

- Overall research score.
- Evaluation classification.
- Visual progress indicators.
- Domain-level scores.
- Minimum expectation indicators.
- Explanation of points earned.
- Areas of strength.
- Areas requiring improvement.

Use clear visual indicators such as:

- Green: Meets or exceeds expectations.
- Yellow: Approaching expectations.
- Red: Does not meet expectations.

### D. User-Friendly Design

The workbook should:

- Use a clean, professional design.
- Clearly distinguish input cells from calculated cells.
- Include dropdown menus where appropriate.
- Automatically calculate results when data are entered.
- Prevent invalid entries.
- Provide instructions and definitions.
- Protect formula cells from accidental modification.
- Allow users to add multiple publications, grants, and presentations.
- Avoid requiring users to understand formulas or programming.

Prefer standard Excel formulas, tables, and data validation over VBA whenever feasible.

### E. Faculty Evaluation Report

Create a printable report that summarizes the faculty member's research performance.

The report should include:

1. Faculty information.
2. Evaluation period.
3. Publication productivity.
4. Grant activity and awards.
5. Scientific presentations.
6. Additional scholarly contributions.
7. Domain-level scores.
8. Overall research score.
9. Final evaluation classification.
10. Explanation of the evaluation outcome.

The report should be suitable for saving as a PDF.

---

## PART 3: Develop a Web-Based Faculty Research Evaluation Calculator

I would also like a prototype web application with an attractive, modern, and intuitive user interface.

The application should allow faculty members or administrators to enter research activities without programming knowledge.

### A. Application Interface

Create a simple interface with the following sections:

**Tab 1: Faculty Information**

Basic faculty and evaluation information.

**Tab 2: Publications**

A dynamic data-entry table where users can add or remove publications.

**Tab 3: Grants and Contracts**

A dynamic form for entering grant applications and awards.

**Tab 4: Presentations**

A dynamic form for entering scientific presentations.

**Tab 5: Other Scholarly Activities**

Additional recognized research contributions.

**Tab 6: Evaluation Results**

An automatically generated scoring dashboard.

**Tab 7: Scoring Policy**

The settings page described in Part 1.

### B. Essential Features

The application should support:

- Adding multiple publications.
- Adding multiple grants.
- Adding multiple presentations.
- Dropdown selections.
- Automatic scoring.
- Real-time or on-demand score updates.
- Clear explanations of awarded points.
- Visual score summaries.
- Automatic evaluation classification.
- Data validation.
- Exporting results to Excel or PDF.
- Saving and reopening faculty evaluations, with appropriate access controls.

### C. Technology Recommendation

Evaluate the suitability of:

- Streamlit (Python).
- Flask.
- Other appropriate lightweight web frameworks.

Recommend the platform that offers the best balance of simplicity, maintainability, usability, and compatibility with the existing Python scoring engine.

Since the algorithm is already implemented in Python, prioritize a solution that can reuse the existing scoring engine rather than duplicating the scoring logic unnecessarily.

The application should initially be designed as a prototype that can run locally.

If persistent storage or institutional deployment is proposed, explain the authentication, authorization, data protection, and institutional IT requirements before implementing those features.

---

## PART 4: Ensure Consistency Across All Platforms

This is a critical requirement.

The Python engine, Excel calculator, and web application must use the same underlying scoring rules, under the same locked policy.

For identical faculty data and the same policy, all implementations should produce:

- The same publication score.
- The same grant score.
- The same presentation score.
- The same additional scholarship score.
- The same overall research score.
- The same evaluation classification.

Use the existing 22 faculty scenarios as validation cases.

Create a comparison report identifying any discrepancies.

Account for rounding differences and ensure that evaluation classifications remain consistent.

---

## PART 5: Deliverables

Please provide the following downloadable files:

1. **faculty_research_webapp/** — Complete web application source code, including the scoring policy page, installation instructions and required dependencies.
2. **PROVISIONAL_POLICY.md** — Every threshold and criterion applied, with its source and the review finding it answers.
3. **faculty_research_calculator.xlsx** — Functional Excel evaluation calculator.
4. **faculty_evaluation_validation.xlsx** — Comparison of the original Python results with the Excel and web application results.
5. **user_guide.pdf** — Instructions for entering faculty information, calculating scores, and interpreting results.

The web application and the policy note come first, so that a working tool can be shown to the Head of Department.

The user guide should explain the evaluation system in language suitable for faculty members and academic administrators.

## PART 6: Implementation Strategy

Please complete the project in the following order:

**Phase A:** Review the three existing Python files and identify all input variables, scoring formulas, thresholds, and dependencies.

**Phase B:** Fix the engine defects listed in `REVIEW_FINDINGS.md`, apply the provisional defaults as policy settings, and write `PROVISIONAL_POLICY.md`.

**Phase C:** Develop and validate the web application, including the scoring policy page.

**Phase D:** Develop and validate the Excel calculator.

**Phase E:** Test all implementations against the 22 faculty scenarios.

**Phase F:** Deliver the final tools and user documentation.

Do not replace the existing scoring model with a simplified version merely to make implementation easier.

If any scoring rule is difficult to reproduce in Excel, explain the issue and propose a technically sound solution that preserves the original model's behavior.

## Final Goal

I want to transform the existing faculty research evaluation algorithm into a practical, transparent, reliable, and easy-to-use evaluation system.

The final product should allow a faculty member or department chair to:

1. Open the calculator or application.
2. Enter the faculty member's research activities.
3. Click **Calculate Evaluation** (or have the score update automatically).
4. Immediately view the research score and evaluation classification.
5. Review a detailed explanation of how the score was calculated.
6. Generate a professional evaluation report.

**The system must be functional, validated against the original Python algorithm, and accessible to users without programming experience.**