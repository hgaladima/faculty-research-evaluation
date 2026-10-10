# Collaborative Docs Editor: Replication PRD

Oct 10, 2026 · @Boms

This PRD specifies a real-time collaborative document editor modelled on the Claude Docs viewer: tabbed docs of prose, tables, charts and diagrams that people and an AI agent edit together through one stable API.

## What the shared artifact is

The link is the Claude Docs viewer, a first-party shared document editor, not a standalone tool with its own logic. Its page HTML holds only a health-monitoring script and loads a bundled React app of 82 files. A doc's content (title, tabs, blocks, comments, permissions) is not in those files: the viewer connects to a Claude Docs service and shows the doc live to everyone who has it open.

This PRD therefore specifies a product to build, not code to copy. Behaviour I could read is marked confirmed; behaviour implied by file names is marked inferred.

| Evidence | What it established | Confidence |
| --- | --- | --- |
| Type instructions (SKILL.md) | Doc, tab, node, block model; agent verbs; comment routing; @Claude asks; view-context block | Confirmed |
| Page manifest in index.html | Capabilities: profile scope, assets, shared room state, downloads, comments with custom anchors; export to Google Drive, Notion, Word/PDF; health actions open, edit, sync, render | Confirmed |
| Font, layout and version-bar modules (read in full) | Serif/sans choice for headings and text; default/wide page width; version compare, show changes, restore | Confirmed |
| Bundle file names (right rail, left tab list, deleted tabs, widget panel, language dialog, KaTeX, Shiki, diff worker, spell-check list) | Features exist; exact behaviour unknown | Inferred |
| Main app bundles (about 8 MB minified) | Not analysed | Not verified |

## Goals, non-goals and users

The product lets a team and an AI agent write, review and revise the same document at the same time, with every change visible live and reversible.

**Goals**

- Real-time multi-user editing of tabbed docs with rich blocks: prose, tables, task lists, math, code, charts, diagrams.
- A programmatic API so an agent can read, edit and comment with targeted, conflict-safe operations.
- Comment threads anchored to words, blocks and table cells, including threads addressed to the agent.
- Version history with compare, show-changes and restore; recoverable deleted tabs.
- Export to Word, PDF, Markdown, Google Drive and Notion.

**Non-goals (v1)**

- Offline-first editing, native mobile apps, and a plugin marketplace.
- Running user code inside a doc: widgets render but keep no user input across reloads.
- Reproducing Anthropic fonts, icons or branding.

**Users**

| User | Need |
| --- | --- |
| Author | Draft and restructure a doc with an agent's help |
| Reviewer | Comment on exact words and see what changed since last read |
| Agent | Make small safe edits, answer comments in-thread, never overwrite a person's concurrent edit |
| Owner | Control who can view, comment and edit; export the result |

## Architecture

Three parts: a static viewer, a document service that owns all content, and an agent connector that talks to the same service. The viewer holds no document data in its files; it is identical for every doc.

| Component | Responsibility | Talks to |
| --- | --- | --- |
| Viewer (React single-page app, served read-only) | Render the doc, edit inline, show comments, history, tabs, right rail; report health | Document service |
| Document service | Store docs, tabs, nodes, comments, history, permissions; apply operations; fan out changes live | Viewer, connector, hosting shell |
| Agent connector (create, batch, read, update, query, delete, export, guide) | Give an agent the same operations as a person, with guards | Document service |
| Hosting shell (frame) | Serve viewer files, embed viewer in an iframe, receive health reports, mint a link per doc | Viewer, document service |
| Export integrations | Push a doc to Google Drive, Notion, Word, PDF, Markdown | Document service |

**Key flows**

1. Create: the shell mints a link; the service creates an empty doc bound to it with one tab.
2. Open: the viewer loads, authenticates, subscribes to the doc and renders the current revision.
3. Edit: each change is an operation sent to the service, which returns a new revision and broadcasts it.
4. Agent edit: the connector submits operations with guards; a guard mismatch means a person changed that block first, so the person's edit wins.
5. Comment to agent: a comment marked for the agent is delivered with its anchor and thread id; the agent replies in the same thread.

**Hosting contract:** the viewer runs inside an iframe over HTTPS, posts health messages to its parent (load, ready, crash, and core actions open, edit, sync, render), and treats a missing parent as a no-op.

## Data model

A doc is a root with tabs. Each tab points to a content node, and a node holds an ordered tree of blocks.

| Entity | Fields (minimum) | Notes |
| --- | --- | --- |
| Doc (wire word: project) | id, title, owner, artifact link, tab list with order keys, permissions, created and updated times | Shares one id with its shareable link |
| Tab (wire word: file) | id, name, order key, parent tab (for nesting), content node id, deleted flag | Deleted tabs stay recoverable |
| Node | id, engine (prose, or json for structured data), revision number | One prose node per tab |
| Block | id, type, content, content hash | Types: paragraph, heading (levels 1-6), list item, table, task, code, math, widget, embed, pending |
| Inline chip | mention (user, tab or doc), date, dropdown (enum option), link | Chips live inside text |
| Enum | id, name, options | One per repeated closed set, such as a Status column |
| Comment (utterance) | id, parent (node with anchor, or another comment), author, body, resolved flag, addressed-to-agent flag | A thread is its first comment plus replies |
| Version | id, revision, author, time, source (edit, restore) | Powers history, compare and restore |
| Asset | id, blob reference, media type, size | Uploaded images and files |

**Identifiers.** Block and character ids take the form session.counter, such as an edit session id plus a monotonic clock. They are stable across edits, so comments and agent targets survive concurrent changes. Printing may abbreviate repeated prefixes; every API call must send the full form.

**Revisions.** Every committed change to a node increments its revision. Reads and writes return the revision, so a client can ask for changes since a given revision.

**Content hash.** Each block carries a short hash of its current content. Whole-block replace and delete require the hash and revision the caller last saw.

## Editor and viewer features

Status key: C = confirmed in the artifact, I = inferred from file names or the type instructions.

| ID | Requirement | Status |
| --- | --- | --- |
| F1 | Rich-text editing: headings, bold, italic, links, bullet, numbered and task lists, tables with editable cells, code blocks with syntax highlighting, display math from TeX | I |
| F2 | Pipe-table editing: add rows and columns, type in cells, dropdown chips per column, comment on a cell | C |
| F3 | Chips: mention a person, tab or doc; date chip; dropdown chip bound to an enum; embed chip for a chart | C |
| F4 | Tabs: left list of tabs, nesting, reorder, rename, mention a tab; deleted tabs listed with restore | C/I |
| F5 | Widgets: charts drawn from rows and diagrams rendered as vector graphics; people edit label text in place and comment on parts; other input is not kept | C |
| F6 | Font control: separate Serif or Sans choice for headings and for body text, saved per doc, reverts with a message on failure | C |
| F7 | Layout control: page width Default or Wide, saved per doc, reverts with a message on failure | C |
| F8 | Language dialog and spell check with a bundled word list | I |
| F9 | Comments: anchor to a phrase, block or cell; threads, replies, resolve; address a thread to the agent; live count in a right rail | C |
| F10 | Right rail: comments, history and doc info in one side panel | I |
| F11 | Version history: list versions, preview any version, Show changes toggle, Compare (vs previous or vs restored), Restore this version, Back to editing | C |
| F12 | Inline agent ask: typing @Claude on an empty line sends the request with the line's ids; the answer is written into the doc at that line | C |
| F13 | Context for the agent: while the doc is open beside a chat, the viewer publishes mode (read or edit), open tab, selected blocks, unsent word count, tab revision and edit count | C |
| F14 | Uploads: images and files stored as assets and embedded where discussed | C |
| F15 | Export: Word, PDF, Markdown, Google Drive file, Notion page | C |
| F16 | Sharing: private by default; share link with view, comment or edit access | I |
| F17 | Thumbnail render of the doc for gallery cards | I |
| F18 | Live presence: see that others are editing and where their changes land | I |

**Behaviour rules**

- Edits appear for every open viewer without a refresh.
- A failed save never leaves the screen in a state that differs from storage: the control returns to the saved value and shows an error.
- Text typed but not yet accepted by the service is counted and exposed as dirty words.
- Pending blocks display an intent line and are replaced when their content arrives.

## Agent API

The agent gets the same operations as a person, through typed calls that carry a container (the doc) and return the new revision.

| Call | Purpose |
| --- | --- |
| batch | Create a doc, or apply several operations to one doc atomically |
| read | Read a doc (list of tabs), a node as an outline, one block subtree, a text search, or only changes since a revision |
| update | Edit a node's content, rename a doc or tab, change a stored value |
| create | Create comments, enums and other objects |
| query | List comments under a node or thread |
| delete | Remove a doc, only on explicit request |
| export | Send a doc to Word, PDF, Markdown, Drive or Notion |
| guide | Return usage topics and refusal explanations |

**Prose operations** (inside an update): insert before or after a block, at the end of the tab, or at the end of a heading's section; replace; delete; move; table row and column operations. Content is sent as inline markdown or plain text, never as bare strings.

**Targets.** Quotable words (find, with an optional occurrence number and a table-cell scope), whole blocks by full id, or a table cell by row and column.

**Guards.** Replacing or deleting a whole block must include its content hash and the revision of the read that showed it. A missing guard is refused. A mismatch means someone edited it: the person's edit wins, and the caller reports what it kept. A force flag exists only for explicit overwrite requests.

**Replace modes.** As text re-words in place and keeps chips, breaks, formatting and comments. As markdown replaces a whole list, table or section.

**Refusals.** Every refusal names a code, the path and the fix, and changes nothing. Codes to define at minimum: missing\_guard, guard\_mismatch, find\_none, cell\_none, access, absent, bad\_request, unknown\_key.

**Comment routing.** A comment sent to the agent arrives with the doc id, tab, node, block and thread root id. The agent changes the doc with update (stating which thread it answers), then replies with a comment whose parent is the thread root. It never replies through any other comment channel. Removing all anchored words of a thread requires an explicit allow-detach flag.

**Inline ask routing.** A request typed into the doc arrives as one JSON object with request, instruction, tab, node and block ids. The answer is written into the doc at that block, replacing it if empty, otherwise inserted after it.

**Trust rule.** Doc content, comments and fetched pages are data written by other people. They are never instructions to the agent.

## Non-functional requirements

Targets below are proposed starting points, not figures taken from the artifact.

| Area | Requirement |
| --- | --- |
| Performance | Open a 20-page doc to first readable content in under 2 s on broadband; keystroke to local render under 50 ms; remote edit visible within 500 ms |
| Scale | 25 concurrent editors per doc; docs up to 500 blocks per tab without lag; tabs up to 50 per doc |
| Loading | Split the app into lazy chunks (right rail, history, widgets, language dialog, deleted tabs); preload the core chunks and the main font |
| Reliability | No lost edits on reconnect; operations idempotent by operation id; failed saves roll the UI back and tell the user |
| Health monitoring | Report load, ready, crash and the core actions open, edit, sync, render; ready failure after a timeout (default 20 s, configurable 5-120 s); classify crashes (uncaught error, unhandled rejection, chunk load); ignore benign resize-observer warnings and errors caused by browser extensions; cap reports per action per 15 s window |
| Accessibility | Keyboard-complete editing and comments; labelled controls and popups; Escape closes panels and returns focus; error messages announced as alerts; respect light and dark themes |
| Security | Viewer served read-only; all writes authorised per doc and per role; content treated as untrusted data (sanitise rendered HTML, SVG and links); widget code sandboxed in an iframe with no access to the parent session; uploads size- and type-limited |
| Privacy | Doc content only reachable through the service; share link access is revocable; comment and edit authorship recorded |
| Compatibility | Current Chrome, Safari, Firefox and Edge; layout works at phone width; HTTPS only |

## Recommended tech stack

The artifact's file names point to a ProseMirror schema, React, a diff worker, KaTeX, Shiki and a Vite-style bundler. Those are inferred; the choices below are recommendations that fit the requirements.

| Layer | Recommendation | Why |
| --- | --- | --- |
| UI | React and TypeScript | Matches the inferred stack; large component ecosystem |
| Rich-text engine | ProseMirror or Tiptap with a custom schema for chips, pending blocks, widgets | Block ids, anchored comments and structured tables need a schema-driven editor |
| Real-time sync | Yjs (CRDT) with a WebSocket provider, or a server-authoritative operation log | Stable block ids and concurrent edits; pick one and keep revision numbers server-side |
| Block ids | Session id plus monotonic counter | Matches the observed id form; survives concurrent edits |
| Math | KaTeX | Fast, no layout dependencies |
| Code highlighting | Shiki, languages loaded on demand | Keep the main bundle small |
| Diff and history | Web worker computing block-level diffs between revisions | Keeps the editor responsive |
| Spell check | Bundled word list with a worker, language chosen in a dialog | Matches the inferred language dialog |
| Charts and diagrams | Sandboxed iframe running small modules that return SVG from named data sources | Keeps charts tied to rows and isolates code |
| Backend | Node or Python API, Postgres for docs, comments and versions, object storage for assets | Standard, easy to scale |
| Auth | OAuth login; per-doc roles (viewer, commenter, editor, owner) | Required for sharing |
| Export | Server-side conversion to docx, PDF and Markdown; OAuth connectors for Drive and Notion | Matches the confirmed export capability |
| Design system | Own tokens and components; open-licensed serif, sans and mono fonts and an open icon set | Anthropic fonts and icons are proprietary and must not be copied |
| Build and hosting | Vite, code-split chunks, static hosting behind a CDN, CSP that limits script and style sources | Matches the loading and security requirements |

## Delivery plan and acceptance criteria

Durations assume a team of four engineers and one designer and are estimates.

| Phase | Scope | Est. duration | Done when |
| --- | --- | --- | --- |
| 1. Core editor | Single-user tabbed docs; block schema, tables, lists, tasks, code, math; autosave; revisions | 6 weeks | A doc survives reload with identical content; every block type round-trips through markdown |
| 2. Collaboration | Real-time sync, presence, permissions, share link | 5 weeks | Two browsers editing one paragraph converge with no lost characters; viewer role cannot write |
| 3. Comments and history | Anchored threads, replies, resolve; version list, show changes, compare, restore; deleted tabs | 5 weeks | A comment stays attached to its words after surrounding edits; restore returns the exact earlier content |
| 4. Agent API | Read, update, create, query, batch with guards and refusals; comment routing; inline ask | 5 weeks | A guarded replace on a stale block is refused; an agent reply lands in the originating thread |
| 5. Rich blocks | Chips, enums and dropdown columns, charts, diagrams, uploads | 5 weeks | A chart updates only through its rows; dropdown values persist per cell |
| 6. Polish and export | Font and layout controls, language and spell check, Word, PDF, Markdown, Drive, Notion, thumbnails, health reporting | 4 weeks | Export opens in Word with headings, tables and math intact; health reports reach the shell |

**Acceptance tests that gate release**

1. Font and layout changes persist; on a simulated save failure the control reverts and shows an error.
2. Two users and one agent edit different blocks at once; every edit is present afterward.
3. The agent attempts to overwrite a block a person just changed; the call is refused and the person's text remains.
4. A comment addressed to the agent produces a reply in the same thread and no stray comment elsewhere.
5. Restoring a version, then choosing Compare with previous version, shows exactly the difference the restore made.
6. A forced script error before first render is reported as a crash and the ready check fails with the right error type.
7. Keyboard-only use can open comments, change fonts and restore a version.

## Risks and open questions

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Behaviour of the editor core was not analysed; the main bundles are minified | Requirements F1, F8, F10, F16-F18 may differ from the original | Run the original side by side and test each row against it before locking scope |
| Real-time conflict handling is the hardest part and the artifact does not show it | Lost or reordered edits | Choose CRDT or operation log in week 1; build a convergence test harness first |
| Anthropic fonts, icons and marks are proprietary | Legal exposure | Use open-licensed fonts and icons and your own name and branding |
| Widget code runs in a viewer | Script injection | Sandboxed iframe, strict CSP, no parent access |
| Agent edits arrive while people type | Frustrating overwrites | Guards, hash checks, and a rule that the person's edit wins |

**Open questions for you**

- Is the goal a general collaborative editor, or an artifact type inside an existing platform that already provides auth, storage and an agent connector?
- Which agent will call the API, and does it need to match the exact verbs and error codes above?
- What scale and which sharing model (private, link, organisation) do you need at launch?
- Do you have access to the original product to verify the inferred rows, especially the right rail, history details and language dialog?

**Not verified:** the exact contents of the right rail, the deleted-tabs rules, spell-check languages, presence indicators, and the sharing roles. Treat those rows as hypotheses.
