# Faculty Research Evaluation Tool: Review Findings and Open Questions

Reviewed 10 October 2026. Sources: `prompt0..md` (the Phase 1 brief), `docs/Research Expectation.pdf`, `docs/Scholarship Working Group June 2013-final.pdf`, and the engine (`research_eval.py.txt`, `scenarios.py.txt`, `sensitivity.py.txt`).

Every number quoted as a result below was produced by running the unmodified engine with its default configuration. Nothing in the engine was changed.

## How to read this

Each finding has an ID, what was found, the evidence, and the decision or question it raises. Findings are grouped by kind:

| Section | Kind | Who decides |
|---|---|---|
| 1 | Gaps in the source material | You / the School |
| 2 | How classification really works | Committee (policy) |
| 3 | Adjustments for effort, leave and career stage | Committee (policy) |
| 4 | Counting rules and double counting | Committee, then engine |
| 5 | Activities named in the sources but not scored | Committee (policy) |
| 6 | Engine defects | No policy decision needed; fix |
| 7 | Workflow and governance | You / the School |
| 8 | Suggested order of work | |

## The ten findings that matter most

1. **The score does not decide Meets versus Does Not Meet.** Three yes/no minimums decide it. The 0-100 score only separates Meets from Exceeds. (2.1)
2. **The bar for Meets is very low.** Two coauthored articles in the lowest journal tier, one internal grant submission as Co-I, and being a non-presenting coauthor on one poster earns exactly 70 and Meets. (2.2)
3. **Exceeds can be reached on publication volume alone.** Six lead-author articles in the lowest tier, with the bare minimum elsewhere, scores 85.0 and Exceeds. (2.5)
4. **One large award gives Exceeds at 75.2**, while a faculty member at 84.9 with no such award is Meets. (2.6)
5. **There is a cliff at 50% of standard expectations.** At 19% research effort, grant and presentation minimums are waived completely and silently; at 20% nothing is waived. The same cliff sits between 5 and 6 months of leave. (3.1)
6. **A faculty member with nothing this year can be classed Meets** through the three-year rolling window on all three domains at once. (3.6)
7. **The same grant can be credited twice in one year**, once as a submission and once as an award. (4.1)
8. **The "two publications a year" minimum is not in either institutional document**, and the grant and presentation minimums are not quantified anywhere. (1.1)
9. **Journal and venue tiers drive most of the score and are not defined anywhere.** (1.4)
10. **Thresholds were tuned on 22 invented profiles**, not on real past reviews. (1.7)

---

## 1. Gaps in the source material

**1.1 The minimums have no documentary source.**
The Phase 1 brief states "a minimum of two peer-reviewed publications annually" and says Document 2 contains the School's expectations. `Research Expectation.pdf` is a guide to the two-page narrative and contains no numbers. Neither document says how many grant submissions or presentations are expected; the brief says only "active engagement" and "participate". The engine's grant and presentation minimums (one qualifying item each) are its own invention.
*Question:* Is there a School document that states these minimums? If not, who will adopt them?

**1.2 Faculty Handbook items 4-11 are missing.**
The narrative guide says the narrative must address items 1-3 and "items 4-11 of the faculty handbook as applicable". Those items are not in `docs/`, so the engine cannot have been checked against them.
*Question:* Can you add that handbook section?

**1.3 The status of the 2013 Working Group document is unclear.**
It is a set of recommendations from a working group of the School of Community and Environmental Health. The brief refers to a School of Public Health. Nothing shows the recommendations were adopted.
*Question:* Is this document current policy, guidance, or history? Does it apply to the present School?

**1.4 Journal tiers and venue tiers are undefined.**
Journal tier (1, 2, 3, or 0 for questionable) multiplies every article's credit by 1.5, 1.25, 1.0 or 0. Venue tier (A, B, C, 0) multiplies every presentation by 1.25, 1.0, 0.6 or 0. Neither the code nor any document here says what puts a journal or conference in a tier. Without definitions the tool is not reproducible between evaluators.
*Question:* Where are the tier definitions (presumably the Phase 1 report)? Who assigns a tier: the faculty member, the chair, or a maintained list?

**1.5 The standard research effort of 40% is a placeholder.**
The code labels it so. Every prorated expectation is computed from it.
*Question:* What is the School's actual standard research assignment?

**1.6 The sources pull in different directions.**
- The Working Group stars "impact factor > 2.5" as a quality marker and also says scholarship "does not have only one path and one formula".
- The brief asks for alignment with DORA, the Leiden Manifesto and CoARA, which discourage journal-level metrics as measures of an individual.
- The handbook requires a narrative on quality, impact and value read at each level of review.

*Question:* Is the tool a decision aid alongside the narrative, or does it produce the rating? This changes how every flag and override should work.

**1.7 The model has not been tested on real cases.**
The weights, the 85 threshold and the caps were tuned so that 22 hypothetical profiles, written alongside the algorithm, classify sensibly. That is circular.
*Recommendation:* Before adoption, score a set of past, anonymised annual reviews whose committee outcomes are known, and compare.

**1.8 The Phase 1 report is not in the project.**
The Phase 2 brief says the Python files "reproduce the numerical results presented in the research evaluation report". Without the report I cannot confirm that, or recover the reasoning behind each unit value.

---

## 2. How classification really works

**2.1 The score plays no part in Meets versus Does Not Meet.**
If all three minimums are met, the result is Meets or Exceeds. If any is unmet, it is Does Not Meet. The `meets_threshold` of 70 is never used to classify; it only triggers a flag. Meeting all three minimums always yields at least 70 by construction, so the two agree under the default settings, but only by arithmetic. With the anchor share set to 0.6 (a variant the sensitivity script runs), profile S1 scores 60.0 and is still Meets.
*Question:* Is that intended? If so, the report should say plainly that minimums decide Meets and the score measures how far above them. If not, the threshold needs to be enforced.

**2.2 The lowest profile that earns Meets.**

| Domain | Activity | Result |
|---|---|---|
| Publications | 2 coauthored articles, Tier 3 | Minimum met, 35.0 |
| Grants | 1 internal submission as Co-I | Minimum met, 24.5 |
| Presentations | Non-presenting coauthor on 1 poster, lowest venue tier | Minimum met, 10.5 |
| **Total** | | **70.0, Meets** |

*Question:* Is this the standard the School means by "meets expectations"?

**2.3 The presentation minimum does not require presenting.**
Any role on any conference presentation at a non-questionable venue meets it, including coauthor and mentor. Institutional talks, outreach and seminars never meet it, however many.
*Question:* Must the faculty member be the presenter at least once?

**2.4 The grant minimum can be met without seeking funding, and blocked while seeking it.**

| Activity | Meets grant minimum? |
|---|---|
| Internal seed-grant submission as PI, Co-PI or Co-I | Yes |
| Consultant on a noncompetitive contract that was awarded | Yes |
| Named on an existing funded project, no submissions this year | Yes |
| Award entered with no role recorded | Yes (role defaults to collaborator) |
| Collaborator on a large external submission | No (half credit) |
| PI on a noncompetitive submission | No (half credit) |

A switch exists to require an external submission; it is off by default.
*Question:* The brief says faculty must show "active engagement in pursuing research funding". Should holding existing funding count? Should an internal submission count?

**2.5 Exceeds on publication volume alone.**
With the bare minimum in grants and presentations (35.0 of 50 available points between them):

| Publications | Score | Class |
|---|---:|---|
| 5 lead articles, Tier 3 | 81.2 | Meets |
| 6 lead articles, Tier 3 | 85.0 | Exceeds |
| 4 lead articles, Tier 1 | 85.0 | Exceeds |

The brief asked "Can someone exceed expectations through publication quantity alone?" The answer is yes, in the lowest tier. The reverse does not hold: maximum grants with the minimum elsewhere reaches 80.5. An alternative rule requiring strength in two domains exists in the code (`breadth`) and is off.
*Question:* Should Exceeds require strength in more than one domain?

**2.6 The large-award shortcut.**
A competitive award in the top size band as PI or MPI gives Exceeds whatever the score, provided the minimums are met. Bare minimum plus one such award scores 75.2 and is Exceeds. A faculty member at 84.9 across the board is Meets. The shortcut applies only in the year the award is first counted.
*Question:* Keep the shortcut? If so, should it need a floor score?

**2.7 Does Not Meet has no gradation and no defined review route.**
Profile S20 (six articles in Tiers 1-2, a large award as Co-PI, no presentation) is Does Not Meet, the same class as a faculty member with no activity. The engine adds a "Committee review" flag in such cases, but nothing defines what the committee may do, or how an override is recorded.
*Question:* Is there an "approaching" category, or a defined override? (The Phase 2 brief asks for a yellow "approaching expectations" indicator that the engine cannot currently produce.)

**2.8 Unfunded effort versus funded results.**

| Grant activity | Units |
|---|---:|
| Unfunded large submission as PI, scored | 1.75 |
| Funded major award as Co-I | 1.00 |
| Funded minor award as PI | 1.00 |
| Funded internal award as PI | 0.75 |

A faculty member with no award ever can reach 32.4 of 35 grant points through submissions, panel service and proposals in development, and 35 of 35 if also named on two active projects. The brief says a successful competitive external grant should "generally" outscore an unsuccessful proposal.
*Question:* Are these orderings acceptable?

---

## 3. Adjustments for effort, leave and career stage

The adjustment factor is (assigned research effort ÷ 40%) × (months active ÷ 12), limited to the range 0.25-1.5.

**3.1 A cliff at factor 0.5.**
Below 0.5 the grant and presentation minimums are waived outright, with nothing required. At 0.5 and above, nothing is waived. The same person, with one coauthored Tier 3 article and nothing else:

| Situation | Factor | Score | Class |
|---|---:|---:|---|
| 19% research effort | 0.47 | 70.0 | Meets |
| 20% research effort | 0.50 | 35.0 | Does Not Meet |
| 5 months active | 0.42 | 70.0 | Meets |
| 6 months active | 0.50 | 35.0 | Does Not Meet |

Two further problems:
- The report does not say a minimum was waived. It lists Grants and Presentations under "Minimums met".
- The code has a softer rule ("reduced assignment: grant minimum met by documented grant engagement"), but it can only fire at a factor of exactly 0.5, because anything lower is already waived. This looks like a slip. Presentations have no softer rule at all.

*Question:* What should a reduced assignment require: nothing, some documented activity, or the full minimum? At what level?

**3.2 Zero research effort still produces a rating.**
At 0% effort, or 0 months active, the factor is held at 0.25. One coauthored article then gives Meets; no activity gives 35.0 and Does Not Meet.
*Question:* Should faculty with no research assignment, or absent all year, be evaluated at all?

**3.3 Research-intensive appointments.**
- 60%, 80% and 100% effort are treated identically (factor capped at 1.5).
- Only the publication minimum rises (2 to 3). Grant and presentation minimums stay at one item.
- Excellence becomes harder to earn in every domain.

*Question:* Is that the intended treatment?

**3.4 The publication minimum moves in steps.**
It is 2 × factor, rounded. At 29% effort the minimum is 1; at 30% it is 2.

**3.5 Circumstances the brief lists that the engine does not handle.**

| Circumstance in the brief | Engine |
|---|---|
| Rank (assistant, associate, full) | Not used |
| Tenure-track versus tenured | Not used |
| Early career beyond year one | Only a first-year yes/no |
| Sabbatical or research leave versus medical or parental leave | All reduce months active alike, though sabbatical is research time |
| Joint appointments | Only through the effort percentage |
| Discipline differences in funding | Not modelled |
| Transition between research areas | Not handled |
| Differences in infrastructure and support | Not handled |

*Question:* Which of these should the tool handle, and which should be left to the committee?

**3.6 The three-year rolling window.**
- It can meet all three minimums at once. A profile with no publications, submissions or presentations this year, but a prior record, one manuscript under review, one proposal in development and one abstract submitted, scores 70.0 and is Meets.
- It only ever helps. A weak three-year record never counts against a good year.
- Nothing limits using it in consecutive years.
- It applies this year's (possibly prorated) minimum to the prior two years. In a six-month leave year, three articles over three years is enough.
- The prior-year figures are typed in as totals. What counts toward them is undefined and nothing checks them.

*Question:* Should the window be able to rescue more than one domain, or more than one year running? Where do prior-year figures come from?

---

## 4. Counting rules and double counting

**4.1 The same grant counted twice in one year.**
Submissions and awards are separate lists with no link. A major award as PI scores 72.6 overall; entering the same grant under both lists scores 75.2.
*Decision:* When a proposal is submitted and funded in the same year, credit the award only?

**4.2 Duplicates are noticed but still credited.**
Two entries with the same DOI raise a validation message and are both scored in full. Duplicate submissions are caught only if an ID is typed in. A resubmission entered with a new ID earns full credit again; the Working Group does list resubmission as creditable, so this may be intended.
*Question:* Full, partial or no credit for a resubmission?

**4.3 Publications have no guard across years.**
Awards can be marked as already credited in a prior year. Publications cannot, so an article could count when it appears online and again in print. "Published" is not defined: accepted, in press, online first, or in an issue.
*Question:* Which date decides the evaluation year?

**4.4 Multi-year awards.**
An award earns full credit in its first year. In later years it earns nothing, and does not meet the grant minimum, unless someone re-enters it as an active project (0.5 units).
*Question:* Is that the intended treatment of continuing awards and renewals?

**4.5 Award size is ambiguous.**
- It is not stated whether the amount is the total award, annual costs, or the faculty member's share. A five-year $300,000 award and a $3 million award are both "large".
- The Working Group defines only minor (< $10,000) and major (> $10,000). The "large" band at $250,000 is the engine's addition, and it carries the Exceeds shortcut in 2.6.
- "Internal" is treated as a size, so an internal award earns the same whatever its amount, and internal/external is mixed up with size.
- Funder type (federal, foundation, state) is not captured.

**4.6 Books, chapters and unrecognised types.**
- One peer-reviewed book counts as two publications and meets the minimum alone.
- Only one chapter counts toward the minimum, but chapter credit is uncapped: six chapters earn 4.5 units, more than four Tier 3 lead articles.
- Books and chapters carry no quality tier.
- A book or chapter marked not peer-reviewed earns zero, with no message.
- Any type the engine does not recognise earns zero, with no message. That includes published abstracts, which the Working Group lists.

**4.7 Authorship has two values.**
Lead (1.0) or coauthor (0.7). The brief asks for first, corresponding and senior authorship to be recognised; the Working Group stars "primary, second, or senior". Which of these count as "lead" is not defined. The student-mentee increment applies only when the faculty member is also marked lead.

**4.8 Presentation type mixes format and setting.**
One field holds both the format (keynote, oral, poster) and the setting (institutional, outreach, seminar). An invited talk at another university's seminar could be entered as "invited" (1.25 units) or "seminar" (0.2). There is no rule for the same talk given at several meetings. Poster credit is uncapped.

**4.9 Self-reported counts that cannot be checked.**
Proposals in development, unfunded projects, manuscripts under review, abstracts submitted and documented impacts are entered as bare numbers. Three of them can turn an unmet minimum into a met one (3.6, and the first-year and reduced-assignment allowances).
*Question:* What evidence is required for each?

---

## 5. Activities named in the sources but not scored

| Activity | Source | Engine |
|---|---|---|
| Published abstracts | Working Group | Zero credit, silently |
| Citation record | Working Group (starred), brief | No input |
| Expert panels and boards | Working Group | No input (grant review panels only) |
| Research appointment | Working Group (starred) | No input |
| Expert consulting and collaborations | Working Group (starred) | No input |
| Research awards and recognition | Brief | No input |
| Mentoring and dissertation supervision | Brief | Only student-first articles and mentored presentations |
| Community-engaged research | Brief | No input |
| Contributions to guidelines | Brief | Only as a "documented impact", capped at 1 unit |
| Grant duration, renewals, faculty share | Brief | Not used |
| Conference scope (regional, national, international) | Brief, handbook | Folded into the undefined venue tier |
| Type of peer review, research theme, funding availability, agency award rates, support for students and postdocs | Handbook narrative | Not captured |

*Question:* For each row: score it, record it without scoring, or leave it to the narrative? Each scored addition changes the algorithm and should be approved as such.

---

## 6. Engine defects

These need fixing whatever the policy answers are. None requires a committee decision.

**6.1 Validation does not protect scoring.** The validation function is separate and optional. Its errors do not stop a profile from being scored.

**6.2 Bad input crashes the engine.** Confirmed: an award with an amount but no size band (this also crashes validation itself), a venue tier entered as the number 0 instead of the text "0", a journal tier entered as text, and any misspelt role.

**6.3 Inputs nobody checks.** Negative counts produce negative units. Also unchecked: publication type, venue tier, presentation role, editorial role, grant review type, active project role, and all rolling-window figures.

**6.4 Validation and scoring disagree.** Validation rejects a grant with no role; scoring accepts it as a collaborator, and for an award that meets the grant minimum.

**6.5 Missing data is treated inconsistently.**

| Missing item | Treatment | Flagged? |
|---|---|---|
| Journal tier | Lowest tier | Yes |
| Venue tier | Middle tier, full credit | No |
| Presentation role | Presenter (most generous) | No |
| Article author role | Coauthor (least generous) | No |
| Book author role | Lead (most generous) | No |
| Grant role | Collaborator (least generous) | No |

**6.6 Displayed scores do not always add up.** Each domain score and the total are rounded separately. In three of the 22 scenarios the printed parts do not sum to the printed total:

| Scenario | Publications | Grants | Presentations | Sum of parts | Printed total |
|---|---:|---:|---:|---:|---:|
| S3 | 38.8 | 24.5 | 10.8 | 74.1 | 74.0 |
| S12 | 49.1 | 24.5 | 11.8 | 85.4 | 85.3 |
| S14 | 50.0 | 27.1 | 10.8 | 87.9 | 88.0 |

Exceeds is decided on the rounded total. Python and Excel round halves differently, so the Excel calculator needs an explicit rounding rule to match.

**6.7 The report is thinner than both briefs require.**
- It shows no point-by-point breakdown; the engine computes one and discards it.
- "Exceeded expectations in" uses 85% of a domain's points, written into the code and not in the configuration.
- Waived minimums are not explained (3.1).
- The same flag can print several times.
- There is no faculty ID, evaluation year, or record of which configuration produced the result.

**6.8 No automated tests.** The 22 scenarios are the only check, and they do not cover: books and chapters, waived minimums, the rolling window for grants or presentations, noncompetitive funding, duplicates, prior-year awards, or any invalid input.

**6.9 The files cannot run as named.** They are saved as `.py.txt` but import each other as `.py` modules.

---

## 7. Workflow and governance

None of the following is defined in the briefs, the documents or the code.

| # | Question |
|---|---|
| 7.1 | Who enters the data: the faculty member, the chair, or staff? |
| 7.2 | Who verifies entries, and against what evidence? |
| 7.3 | Who assigns and maintains journal and venue tiers? Is there a master list? |
| 7.4 | What may the committee do with a "Committee review" flag? Can it override a class, and how is that recorded? |
| 7.5 | How does a faculty member correct or appeal a result? |
| 7.6 | What is the evaluation period: calendar year, academic year, or fiscal year? |
| 7.7 | Who approves changes to the configuration? Is it frozen per evaluation year, and is the version recorded on each report? |
| 7.8 | The rolling window and the prior-year guards need earlier years' records. Where are they kept? This conflicts with a prototype that only runs locally, and these are personnel records. |
| 7.9 | What is the result used for: annual review only, or also merit pay, third-year review, tenure and promotion? |
| 7.10 | Who is in scope? The handbook guide covers tenured and tenure-track faculty. What about lecturers, research faculty and clinical faculty? |
| 7.11 | How does the score relate to the required two-page narrative? |

**7.12 Incentives the current rules create.** Many low-tier articles in place of fewer strong ones (2.5); self-assigned tiers (1.4); an internal submission to tick the grant minimum (2.4); a coauthored poster to tick the presentation minimum (2.3); inflated counts of proposals in development (4.9); entering a resubmission as a new proposal (4.2).

---

## 8. Suggested order of work

1. **Supply the missing sources:** the Phase 1 report, handbook items 4-11, and any document stating the minimums (1.1, 1.2, 1.4, 1.8).
2. **Settle what the tool is for** (1.6, 7.9, 7.10), because the answers shape everything after.
3. **Decide the classification rules** in section 2 and the waiver rule in 3.1. These change who gets which rating.
4. **Decide the counting rules** in section 4 and which rows of section 5 to score.
5. **Fix the engine defects** in section 6 and add tests, so the agreed rules are locked in.
6. **Back-test on real past reviews** (1.7).
7. **Then build** the Excel calculator and the web application on the corrected engine.

Steps 3 and 4 change the scoring model. The Phase 2 brief requires every such change to be identified and justified; this document is the list of candidates.
