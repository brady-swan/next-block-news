"""Build the dated owner-facing PDF; documentation-only dependency: ReportLab.

Run with a documentation Python environment, not the production worker. Render the
result with pdftoppm and inspect every page before releasing a changed guide.
"""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/pdf/nbn-system-guide.pdf"
W, H = 1000, 700
INK = colors.HexColor("#11232e")
MUTED = colors.HexColor("#536672")
BG = colors.HexColor("#f4f3ee")
LINE = colors.HexColor("#d5ddd9")
ORANGE = colors.HexColor("#e58a20")
BLUE = colors.HexColor("#356a91")
GREEN = colors.HexColor("#367a62")
PAGE = 0


def text(c, x, top, width, value, size=14, color=INK, bold=False, max_height=None):
    style = ParagraphStyle("body", fontName="Helvetica-Bold" if bold else "Helvetica",
                           fontSize=size, leading=size * 1.42, textColor=color,
                           spaceAfter=0, splitLongWords=True)
    p = Paragraph(value, style)
    _, height = p.wrap(width, H)
    if max_height is not None and height > max_height:
        raise ValueError(f"Text overflows allocated box ({height}>{max_height}): {value[:60]}")
    if top < H - 48 and top + height > H - 49:
        raise ValueError(f"Text runs into footer: {value[:60]}")
    p.drawOn(c, x, H - top - height)
    return height


def rect(c, x, y, w, h, fill=colors.white, stroke=LINE, radius=10):
    c.setFillColor(fill); c.setStrokeColor(stroke)
    c.roundRect(x, H - y - h, w, h, radius, fill=1, stroke=1)


def card(c, x, y, w, h, label, title, body, accent=BLUE, size=14):
    rect(c, x, y, w, h)
    c.setFillColor(accent); c.rect(x + 16, H - y - 25, 22, 4, fill=1, stroke=0)
    text(c, x + 16, y + 36, w - 32, escape(label.upper()), 10, accent, True)
    height = text(c, x + 16, y + 60, w - 32, title, 19, INK, True)
    text(c, x + 16, y + 72 + height, w - 32, body, size, max_height=h - 88 - height)


def arrow(c, x1, y1, x2, y2, color=ORANGE):
    from math import atan2, cos, sin
    c.setStrokeColor(color); c.setFillColor(color); c.setLineWidth(2)
    c.line(x1, H - y1, x2, H - y2)
    a = atan2(y2 - y1, x2 - x1)
    p = c.beginPath(); p.moveTo(x2, H - y2)
    p.lineTo(x2 - 7 * cos(a - .5), H - (y2 - 7 * sin(a - .5)))
    p.lineTo(x2 - 7 * cos(a + .5), H - (y2 - 7 * sin(a + .5)))
    p.close(); c.drawPath(p, fill=1, stroke=0)


def page(c, chapter, title, subtitle, source):
    global PAGE
    if PAGE:
        c.showPage()
    PAGE += 1
    c.setFillColor(BG); c.rect(0, 0, W, H, fill=1, stroke=0)
    text(c, 48, 26, 700, "NEXT BLOCK NEWS  /  SYSTEM FIELD GUIDE", 10, MUTED, True)
    text(c, 48, 61, 904, title, 31, INK, True)
    text(c, 48, 110, 900, subtitle, 13, MUTED)
    c.setStrokeColor(LINE); c.line(48, 48, W - 48, 48)
    text(c, 48, 659, 830, f"Snapshot 2026-09-06  |  {escape(chapter)}  |  {escape(source)}", 9, MUTED)
    text(c, 925, 657, 28, f"{PAGE:02d}", 11, INK, True)


def note(c, y, title, body, accent=ORANGE, height=86):
    rect(c, 48, y, 904, height, colors.HexColor("#e9eeea"), LINE)
    text(c, 66, y + 13, 220, title, 14, accent, True)
    text(c, 296, y + 13, 636, body, 13, max_height=height - 24)


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUTPUT), pagesize=(W, H), pageCompression=1)
    c.setTitle("Next Block News - System Field Guide")
    c.setAuthor("Next Block News")
    c.setSubject("Production architecture, timing, evidence, delivery and Desk observability; 2026-09-06")

    page(c, "01 / The whole machine", "One wire. A fresh newsroom each run.",
         "Useful, timely Bitcoin news - with accountable sources and an independent edit. Autopost is OFF in this snapshot.", "SYSTEM.md + live runtime settings")
    stages = [
        ("01 / Intake", "Watch", "Official feeds, reporting, X guides, Perception and Node tips.<br/><br/>Persist and deduplicate URLs."),
        ("02 / Preparation", "Organize", "Haiku filters RSS/EDGAR noise. Luna prepares the batch and relevant storyline context."),
        ("03 / Newsroom", "Report & write", "Grok 4.3 medium chooses stories, researches selectively and writes one run dossier."),
        ("04 / Editor", "Independent edit", "Grok 4.5 medium can approve, revise, stage for review or drop each story."),
        ("05 / Delivery", "Typefully", "Clean lead + Source reply.<br/><br/>Human draft now; eligible scheduling only with autopost on."),
    ]
    for i, (label, title, body) in enumerate(stages):
        x = 48 + 184 * i
        card(c, x, 166, 168, 279, label, title, body, ORANGE if i in (2, 4) else BLUE, 13)
        if i < 4:
            arrow(c, x + 170, 298, x + 181, 298)
    note(c, 468, "Continuity underneath", "SQLite holds exact event identity, prior outputs, unresolved reporting work and NBN-native storylines. A fresh model context does not mean starting from zero.", GREEN)
    note(c, 566, "Judgment, not quotas", "The models decide importance, freshness, source sufficiency and framing. Code protects mechanical delivery integrity. Five to eight stories is an estimate, not a target to fill.", BLUE, 72)

    page(c, "02 / Discovery", "Many inputs. Different clocks.",
         "The single worker sleeps 60 seconds after each cycle. Long network or model work can delay the next poll.", "INBOUND-NEWS-FLOW.md + sources.py + config.py")
    rows = [
        ("RSS + EDGAR", "Each worker cycle", "12 RSS outlets; Bitcoin-bearing 8-K filings. Haiku mailroom first."),
        ("X watches + guide accounts", "180-second throttle", "since_id recent search. Public list membership refreshes hourly."),
        ("Direct Perception", "15-minute throttle", "Broad Bitcoin discovery. Separate from the Node's provider usage."),
        ("Node wire API", "5-minute consumer throttle", "Supplemental versioned candidates. Valid pulse age: at most 3 hours."),
        ("Fresh EIC citations", "Weekdays 14:40 / 21:15 UTC", "Up to 12 cited reads per window; date and provenance checked."),
        ("Editorial desk", "Normal 15-minute deadline", "Nonempty eligible batches; priority, operator and backlog exceptions."),
    ]
    y = 163
    for i, (lane, cadence, detail) in enumerate(rows):
        rect(c, 48, y, 904, 64, colors.white if i % 2 == 0 else colors.HexColor("#ecefe9"), LINE, 5)
        text(c, 62, y + 11, 218, escape(lane), 14, INK, True)
        text(c, 298, y + 11, 215, escape(cadence), 13, BLUE, True)
        text(c, 528, y + 9, 405, escape(detail), 12, MUTED, max_height=48)
        y += 72
    text(c, 48, 602, 904, "Node's last-known upstream pulse: hourly 05:00-20:00 Central. That scheduler lives elsewhere; NBN verifies payload age, not the scheduler itself. Scheduled Block threads are disabled.", 12, MUTED)

    page(c, "03 / A clean desk", "Give the writer the right context.",
         "No permanent conversation. One prepared batch, stable IDs, retrievable context and selective research.", "newsroom.py + desk_prep.py + PROMPTS.md")
    card(c, 48, 167, 276, 340, "Before the writer", "Prepare, don't pre-decide", "<b>Haiku mailroom</b><br/>RSS/EDGAR: priority, candidate or background.<br/><br/><b>Luna low assignment</b><br/>Distill the event, relevance, freshness question and research objective. Select relevant NBN storylines.<br/><br/>Protected work and failures advance. Background remains reviewable.", BLUE, 13)
    card(c, 362, 167, 276, 340, "Writer payload", "A well-organized desk", "Orientation and audience brief.<br/><br/>Stable candidate cards + likely receipts.<br/><br/>Separate pointers, inspected evidence, recent coverage and open drafts.<br/><br/>Compact 48-hour feed and continuity indexes; retrieve fuller context when useful.", ORANGE, 13)
    card(c, 676, 167, 276, 340, "Grok 4.3 / medium", "Choose the next move", "Write from usable receipts.<br/><br/>Search SerpAPI and fetch public pages.<br/><br/>Retrieve saved context.<br/><br/>Assign one bounded native web/X research job.<br/><br/>Submit dispositions and story copy.", GREEN, 13)
    arrow(c, 328, 326, 357, 326); arrow(c, 642, 326, 671, 326)
    note(c, 535, "Do not overread the tools", "Native web/X research is available, not guaranteed to be selected. The latest nine-run routing experiment did not establish reliable delegation, and its experimental prompt did not ship.", ORANGE, 99)

    page(c, "04 / Event journey", "From guide tip to reader-visible post.",
         "Illustrative lifecycle, not a claim that any specific current story was published.", "main.py + store.py + publisher.py")
    events = [
        ("A guide posts a lead", "Persist its URL, source, first-seen time and attention context. It is a tip, not proof."),
        ("The due desk considers it", "Protected guide context survives preparation. Other reports may join the same event."),
        ("The writer researches and writes", "Choose useful source material and a narrow claim. Defer with a precise objective if needed."),
        ("The editor makes its call", "Approve or revise useful work; stage uncertainty; drop weak or redundant coverage."),
        ("The publisher checks event state", "Existing draft? Eligible replacement only. Already visible? A repeat cannot create anew."),
        ("Typefully returns a result", "Read back ordered content. Draft now; publication only under the master switch and policy."),
    ]
    for i, (title, body) in enumerate(events):
        y = 166 + i * 72
        c.setFillColor(ORANGE); c.circle(66, H - y - 18, 15, stroke=0, fill=1)
        text(c, 60, y + 9, 14, str(i + 1), 11, INK, True)
        if i < 5:
            arrow(c, 66, y + 37, 66, y + 67, LINE)
        text(c, 100, y, 297, escape(title), 15, INK, True)
        text(c, 412, y, 524, escape(body), 13, MUTED, max_height=61)
    text(c, 100, 606, 832, "A future run can continue held work. A saved workbench is context, not a publishing command or a guaranteed retry clock.", 12, GREEN, True)

    page(c, "05 / Evidence & memory", "What counts as proof? What is just context?",
         "Source capability stays visible. A model's confident summary is not silently promoted to a captured source.", "SYSTEM.md / practical evidence standard")
    card(c, 48, 164, 438, 265, "Evidence", "Inspect and attribute", "<b>Direct fetch:</b> usable public source text, URL and fingerprint.<br/><br/><b>Native extract:</b> source-specific, provider-reported paraphrase tied to an observed citation URL. Not verbatim page capture.<br/><br/>One credible report may support routine narrow news. Higher-stakes claims normally need stronger support or narrower attribution.", BLUE, 13)
    card(c, 514, 164, 438, 265, "Context", "Useful, but not proof", "Guide posts, snippets, Node summaries, Luna prep and storylines direct attention.<br/><br/>A captured social post proves what its author said, not the underlying allegation.<br/><br/>The registry is guidance, not a closed universe. Syndicated copies do not become independent reports.", ORANGE, 13)
    memory = [
        ("Exact event", "Aliases + output lifecycle. Prevent a blind second create; preserve distinct developments."),
        ("Workbench", "72-hour context; reusable evidence up to 24 hours after revalidation. Precise unresolved objectives."),
        ("Storyline", "Broader ongoing subject, selected by Luna. NBN owns it; Node themes are not live model context."),
    ]
    for i, (title, body) in enumerate(memory):
        x = 48 + 306 * i
        rect(c, x, 439, 292, 154, colors.HexColor("#e6eee8"), LINE)
        text(c, x + 15, 454, 261, title, 16, GREEN, True)
        text(c, x + 15, 487, 261, body, 12, max_height=93)
    text(c, 48, 614, 904, "SHA-256 is a fingerprint for identity/integrity, not encryption. Model/provider credentials stay out of Desk snapshots and this guide.", 12, MUTED)

    page(c, "06 / Publishing controls", "Delivery is a lifecycle, not a button press.",
         "Autopost OFF preserves the full editorial stack. It changes eligible delivery into a human Typefully draft.", "publisher.py + publisher_typefully.py + CORRECTIONS.md")
    card(c, 48, 165, 280, 300, "Before any write", "Record intent", "Persist the exact desired thread and canonical event family before the network call.<br/><br/>A single safe untouched draft can be replaced when enabled. Human-edited, comment-marked or ambiguous work is protected.", BLUE, 14)
    card(c, 360, 165, 280, 300, "Remote delivery", "Read it back", "Clean news lead first.<br/><br/><b>Source: receipt URL</b> in the immediate first reply.<br/><br/>Verify ordered content. Scheduling and confirmed publication are different outcomes.", ORANGE, 14)
    card(c, 672, 165, 280, 300, "After the attempt", "Reconcile safely", "Ambiguous response? Do not blindly POST again.<br/><br/>Known Typefully records reconcile normally every five minutes. Manual publication updates confirmation time and coverage.", GREEN, 14)
    arrow(c, 332, 310, 355, 310); arrow(c, 644, 310, 667, 310)
    note(c, 493, "Owner-only actions", "Viewing is read-only. Intake's Send to newsdesk queues a skipped lead for reconsideration next run, with Brady's override and prior skip reason. It is not approval to publish. Review retains guarded stage/dismiss and mutation controls.", ORANGE, 85)
    text(c, 48, 601, 904, "The internal daily receipt audit is disabled by owner decision. Corrections remain human-reviewed. The rolling audit may turn autopost OFF for an evidenced systemic failure, never ON.", 12, MUTED)

    page(c, "07 / Reading the Desk", "See the work. Know what the numbers mean.",
         "A run-first workspace with a persistent wide-screen inspector. Visible browser tabs refresh every 15 seconds.", "DESK-GUIDE.md + desk_api.py + desk_ui/")
    views = [("Newsroom", "Latest run; Previous/Next pin history. Input, research, decisions, copy and activity."),
             ("Intake", "Unique first-seen-day items, current status and preparation reasons. Search to drill down."),
             ("Research inspector", "Assignments, returned findings, prepared captures and cited evidence. Missing is unknown."),
             ("Outputs", "Locally tracked copy, receipt, timestamps and confirmation. Not every remote draft."),
             ("System & costs", "Current roster/effort, stage and period costs, averages, source/search health and PDF.")]
    for i, (title, body) in enumerate(views):
        y = 165 + i * 65
        rect(c, 48, y, 904, 57, colors.white, LINE, 5)
        text(c, 63, y + 12, 190, title, 15, BLUE, True)
        text(c, 272, y + 11, 659, body, 13, max_height=39)
    note(c, 509, "Do not collapse the clocks", "Source time != first seen != local output recorded != confirmed publication. Peer timing needs a separate audit comparison. Missing timestamps or costs remain unknown.", BLUE, 82)
    text(c, 48, 609, 904, "History stays pinned until Back to latest. Rich observations expire after 14 days; gaps are not zero work. Editor fallbacks are not rewrites. Current publisher state has its own clock. Review tools retain guarded actions.", 12, MUTED)

    page(c, "08 / Operating discipline", "Observe, learn, make the smallest useful change.",
         "The machinery now supports calibration; it does not replace editorial taste or the owner's authority.", "AUDIT-AUTONOMY.md + HANDOFF-CODEX.md")
    card(c, 48, 165, 280, 324, "Costs", "Measure the right bill", "Recorded intake/prep/research/writer/editor usage includes tokens, cache shape, latency, native calls and cost provenance.<br/><br/>xAI reported totals where available; other supported calls are estimated.<br/><br/>Unknown costs are not zero.", BLUE, 13)
    card(c, 360, 165, 280, 324, "Audit scope", "Observe and improve", "<b>Internal daily audit: disabled.</b> Historical receipt checks remain available.<br/><br/><b>Codex rolling audit:</b> health, quality, misses, peer speed, cost and smallest technical repairs.<br/><br/>Bounded approved-style prompt tuning is allowed; broader changes need approval.", ORANGE, 13)
    card(c, 672, 165, 280, 324, "Release discipline", "Keep it reversible", "Independent review when requested.<br/><br/>Offline tests, clean release archive, SQLite backup.<br/><br/>Deploy to the existing Railway worker; smoke and observe a natural cycle.<br/><br/>Restore the audit. Never enable autopost as a release step.", GREEN, 13)
    note(c, 514, "Cost boundaries", "Direct per-run costs use distinct metered production runs; unlinked intake stays shared. Day/week/month averages use complete Central periods. Historical receipt audits, hosting, source/search services and Codex remain outside the ledger.", ORANGE, 88)
    text(c, 48, 618, 904, "Current reference map: DOCUMENTATION.md. Detailed architecture: SYSTEM.md. Prompt authority: orientation-brief-v2.md. Historical plans and bake-offs remain dated evidence, not live instructions.", 11, MUTED)
    c.save()
    print(f"Created {OUTPUT} ({PAGE} pages)")


if __name__ == "__main__":
    build()
