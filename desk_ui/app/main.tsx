import React, { useState, useEffect, useRef, useCallback } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  Clock3,
  FlaskConical,
  Inbox,
  Layers3,
  Radio,
  Send,
  ShieldCheck,
  SquarePen,
  X,
  Link2,
  CircleHelp,
} from "lucide-react";
import {
  Sidebar,
  SidebarProvider,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import logo from "./nbn-logo.png";

type Row = Record<string, any>;
type State = {
  view: string;
  run: string;
  lead: string;
  tab: string;
  detail: string;
  filter: string;
  follow: boolean;
  open: boolean;
  d: string;
  q: string;
  page: number;
  status: string;
};
const nav = [
  { id: "newsroom", name: "Newsroom", icon: Layers3 },
  { id: "intake", name: "Intake & sources", icon: Inbox },
  { id: "outputs", name: "Outputs", icon: Send },
  { id: "system", name: "System", icon: Activity },
];
const tabNames = ["decisions", "research", "desk", "copy", "activity"];
const token = new URLSearchParams(location.search).get("k") || "";
function readState(): State {
  const p = new URLSearchParams(location.search);
  const path = location.pathname.split("/")[2];
  const view =
    p.get("view") ||
    (path === "runs" || !path || path === "live" ? "newsroom" : path);
  return {
    view: nav.some((n) => n.id === view) ? view : "newsroom",
    run: p.get("run") || "",
    lead: p.get("lead") || "",
    tab: tabNames.includes(p.get("tab") || "") ? p.get("tab")! : "decisions",
    detail: ["overview", "research", "copy", "visuals"].includes(p.get("detail") || "")
      ? p.get("detail")!
      : "overview",
    filter: p.get("filter") || "all",
    follow: p.has("run") ? p.get("follow") === "1" : true,
    open: p.get("open") === "1",
    d: p.get("d") || "",
    q: p.get("q") || "",
    page: Math.max(1, Math.min(250, Number(p.get("page")) || 1)),
    status: p.get("state") || "",
  };
}
function authUrl(path: string, params: Row = {}) {
  const q = new URLSearchParams({ k: token });
  for (const [k, v] of Object.entries(params))
    if (v !== null && v !== undefined && v !== "") q.set(k, String(v));
  return `${path}?${q}`;
}
const clock = (v: any, full = false) =>
  v
    ? new Intl.DateTimeFormat("en-US", {
        timeZone: "America/Chicago",
        month: full ? "short" : undefined,
        day: full ? "numeric" : undefined,
        hour: "numeric",
        minute: "2-digit",
        second: full ? "2-digit" : undefined,
      }).format(new Date(Number(v) * 1000)) + (full ? " CT" : "")
    : "Not recorded";
const dollars = (n: any, d = 2) =>
  typeof n === "number" ? `$${n.toFixed(d)}` : "—";
function href(raw: any) {
  try {
    const u = new URL(String(raw));
    return ["https:", "http:"].includes(u.protocol) &&
      !u.username &&
      !u.password
      ? u.href
      : "";
  } catch {
    return "";
  }
}
function External({ url, children }: { url: any; children: React.ReactNode }) {
  const u = href(url);
  return u ? (
    <a href={u} target="_blank" rel="noreferrer noopener">
      <span>{children}</span> <ArrowUpRight size={14} />
    </a>
  ) : (
    <span>{children}</span>
  );
}
function Note({ children }: { children: React.ReactNode }) {
  return (
    <div className="evidence-note">
      <CircleHelp size={16} />
      <span>{children}</span>
    </div>
  );
}

function Reconsider({ item, refresh }: { item: Row; refresh: () => void }) {
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState<Row | null>(null);
  const inFlight = useRef(false);
  const control = item.reconsider || {};
  const request = submitted || control.request;
  useEffect(() => {
    if (submitted && control.latest_action_id >= submitted.id)
      setSubmitted(null);
  }, [control.latest_action_id, submitted]);
  const queued = request && ["queued", "processing"].includes(request.state);
  async function send() {
    if (inFlight.current || queued) return;
    inFlight.current = true;
    setSending(true);
    setError("");
    try {
      const response = await fetch("/desk/api/item-action", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          k: token,
          id: item.url_hash,
          action: "reconsider",
          expected_action_id: String(control.latest_action_id || 0),
        }),
        signal: AbortSignal.timeout(12000),
      });
      if (response.status === 403)
        throw Error("Your Desk access link is missing or expired.");
      const outcome = await response.json();
      if (!response.ok || !outcome.ok)
        throw Error(outcome.reason || "Request was not accepted.");
      setSubmitted(outcome);
    } catch (e: any) {
      setError(
        e.name === "TimeoutError" || e.name === "TypeError"
          ? "Could not confirm queueing. Refresh the card; retrying will not duplicate a pending request."
          : e.message,
      );
    } finally {
      inFlight.current = false;
      setSending(false);
      refresh();
    }
  }
  if (!control.eligible && !request && !sending && !error) return null;
  return (
    <div className="reconsider-control">
      {(control.eligible || sending || queued) && (
        <Button
          variant="outline"
          size="sm"
          disabled={sending || !!queued}
          onClick={send}
        >
          <Send size={14} />{" "}
          {sending
            ? "Queueing…"
            : queued
              ? "Queued for newsdesk"
              : "Send to newsdesk"}
        </Button>
      )}
      <span role="status">
        {queued
          ? "Next scheduled run · Brady’s skip override and original reason will accompany this lead."
          : request?.state === "completed"
            ? "Delivered to the writer for reconsideration; not approval to publish."
            : request?.state === "blocked"
              ? request.result
              : "Override this skip for a fresh look. The writer still makes the editorial call."}
      </span>
      {error && <span role="alert">{error}</span>}
    </div>
  );
}
function Empty({
  title,
  children,
}: {
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="missing-state">
      <CircleHelp size={23} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
function Pill({ text }: { text: any }) {
  const s = String(text || "Not recorded");
  return (
    <span
      className={
        "outcome " +
        (/Dropped|Failed|error|Uncertain|Unfinished/.test(s)
          ? "rose"
          : /Draft|Delivered|Published|healthy|ok/.test(s)
            ? "green"
            : "amber")
      }
    >
      {s}
    </span>
  );
}
function Copy({
  body,
  label,
  note,
}: {
  body?: string;
  label: string;
  note?: string;
}) {
  return (
    <article className="copy-version">
      <div className="copy-label">
        <SquarePen size={16} />
        <strong>{label}</strong>
        <span>{note}</span>
      </div>
      {body ? (
        <>
          <div className="tweet-author">
            <img src={logo} width={36} height={36} alt="" />
            <div>
              Next Block News<span>@nextblocknews_</span>
            </div>
          </div>
          <div className="post-copy">
            {body.split(/\n\s*\n/).map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        </>
      ) : (
        <Empty title="No copy recorded">
          This stage may not have been reached, may not have returned copy, or
          its response was not retained.
        </Empty>
      )}
    </article>
  );
}
function Json({
  value,
  label = "Recorded payload",
}: {
  value: any;
  label?: string;
}) {
  return (
    <details className="payload">
      <summary>{label}</summary>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}
function CopyPanel({ story }: { story: Row }) {
  const delivery = story.delivery || {},
    actualEditor = ["initial", "recovery"].includes(story.editor?.origin);
  return (
    <div className="copy-surface">
      <div className="copy-comparison">
        <Copy
          body={story.writer}
          label="Writer proposal"
          note="Recorded dossier"
        />
        <Copy
          body={
            actualEditor
              ? story.editor?.post
              : delivery.submitted_copy || story.editor?.post
          }
          label={
            actualEditor
              ? "Editor return"
              : delivery.submitted_copy
                ? "Submitted copy"
                : "Writer copy · editor unavailable"
          }
          note={
            actualEditor
              ? story.editor.origin
              : delivery.submitted_copy
                ? "Publisher materialization"
                : story.editor?.origin?.replaceAll("_", " ")
          }
        />
      </div>
      {story.editor && (
        <Note>
          {!actualEditor && ["unavailable_fallback", "omitted_fallback"].includes(story.editor.origin) &&
            <strong>Needs human review — editor response failed. </strong>}
          {story.editor.verdict}: {story.editor.reason} ·{" "}
          {story.editor.origin?.replaceAll("_", " ")}
        </Note>
      )}
      {story.reader_receipt?.url && <p className="meta-copy">
        Reader source: <External url={story.reader_receipt.url}>{story.reader_receipt.source || "Open receipt"}</External>
      </p>}
      {delivery.now && (
        <section className="current-output">
          <h3>
            Output now <Pill text={delivery.now.state} />
          </h3>
          <p>
            Last publisher check:{" "}
            {clock(delivery.now.publisher_synced_at, true)}. This may differ
            from the copy recorded during the run.
          </p>
          <External url={delivery.now.typefully_url}>
            Open in Typefully
          </External>
          {delivery.now.public_url && (
            <External url={delivery.now.public_url}>View on X</External>
          )}
          <Json
            label="Current locally tracked copy"
            value={delivery.now.body}
          />
        </section>
      )}
    </div>
  );
}
function WriterFeedback({ record }: { record?: Row }) {
  const status = record?.status || "not_recorded";
  const labels: Row = {
    not_recorded: "No writer self-report was recorded for this run.",
    no_feedback: "The writer had no feedback to add.",
    invalid_ignored: "Optional feedback could not be read; editorial work was unaffected.",
    expired: "This self-report’s 14-day detail retention has expired.",
  };
  return <div className="writer-feedback">
    <p className="meta-copy">Writer self-report · one input for your review, not a verified diagnosis.
      {record?.model ? ` ${record.model} · ${record.effort} effort · ${clock(record.at, true)}` : ""}</p>
    {status !== "provided" ? <p>{labels[status] || "Not recorded"}</p> : <>
      {[["what_helped", "What helped"], ["what_hindered", "What got in the way"],
        ["suggested_improvement", "Suggested improvement"]].map(([key, label]) =>
        record?.feedback?.[key] ? <div className="finding" key={key}><div>
          <strong>{label}</strong><p>{record.feedback[key]}</p>
        </div></div> : null)}
      {!!record?.feedback?.references?.length && <p className="meta-copy">
        References: {record.feedback.references.join(" · ")}</p>}
    </>}
  </div>;
}

function researchRows(run: Row, story?: Row) {
  return (run.artifacts || []).filter((a: Row) => {
    if (!["tool", "research_return", "native_research", "native_receipts"].includes(a.kind)) return false;
    if (!story) return true;
    const p = a.payload || {},
      args = p.arguments || p.assignment || {},
      members = story.members || [];
    return (
      [
        ...(args.candidate_ids || []),
        ...(args.candidates || []).map((c: Row) => c.candidate_id),
      ].some((id: string) => members.includes(id)) ||
      members.includes(args.candidate_id) ||
      (story.evidence_fetch_ids || []).includes(p.returned?.fetch_id)
    );
  });
}
function Research({ run, story }: { run: Row; story?: Row }) {
  const artifacts = researchRows(run, story);
  const candidates = (run.candidates || []).filter(
    (c: Row) => !story || story.members.includes(c.id),
  );
  const prepared = (run.packet?.prepared_evidence || []).filter(
    (e: Row) =>
      !story ||
      (story.evidence_fetch_ids || []).includes(e.fetch_id) ||
      story.selected_fetch_id === e.fetch_id,
  );
  return (
    <div className="research-detail">
      <div className="section-heading">
        <h3>Research assignments</h3>
        <span className="tiny-label">Recorded work, not hidden reasoning</span>
      </div>
      {candidates
        .filter((c: Row) => c.assignment)
        .map((c: Row) => (
          <div className="finding" key={c.id}>
            <FlaskConical size={17} />
            <div>
              <strong>{c.title}</strong>
              <p>{c.assignment}</p>
            </div>
          </div>
        ))}
      {prepared.map((e: Row, i: number) => (
        <article className="research-record" key={"prefetch" + i}>
          <div className="section-heading">
            <h3>Prepared source capture</h3>
            <Pill text="Delivered to writer" />
          </div>
          <External url={e.final_url || e.url}>
            {e.source_name || "Open source"}
          </External>
          <p className="meta-copy">
            Captured before the writer’s first turn · {e.fetch_id}. This is
            evidence supplied with the desk, not a later research request.
          </p>
          {e.text && (
            <details className="payload">
              <summary>
                Inspected text{e.text_truncated ? " · excerpt" : ""}
              </summary>
              <pre>{e.text}</pre>
            </details>
          )}
          <Json value={e} />
        </article>
      ))}
      {!artifacts.length && !prepared.length && (
        <Empty title="Research returns not recorded here">
          No linked research return was retained in this view. Older runs kept
          counters, not full returns. Unassigned work may be available in the
          run’s Research tab.
        </Empty>
      )}
      {artifacts.map((a: Row) => {
        const p = a.payload || {},
          r = p.returned || {},
          memo = r.memo_untrusted_not_evidence || p.memo;
        return (
          <article className="research-record" key={a.id}>
            <div className="section-heading">
              <h3>
                {p.tool?.replaceAll("_", " ") || (a.kind === "native_research" ? "Writer native research" : "Research reporter return")}
              </h3>
              <Pill text={a.phase} />
            </div>
            <p className="meta-copy">
              {clock(a.at, true)}
              {a.truncated ? " · Sanitized or truncated" : ""}
              {a.expired ? " · Rich payload expired" : ""}
            </p>
            {p.arguments?.query && (
              <p>
                <strong>Search:</strong> {p.arguments.query}
              </p>
            )}
            {p.arguments?.objective && <p>{p.arguments.objective}</p>}
            {p.observed_urls?.length > 0 && <>
              <p className="meta-copy">{p.calls} native calls · {p.run_calls} in this run. Observed URLs are pointers; they are not source extracts.</p>
              {p.observed_urls.map((url: string) => <p key={url}><External url={url}>{url}</External></p>)}
            </>}
            {p.arguments?.url && (
              <External url={p.arguments.url}>Requested source</External>
            )}
            {memo &&
              typeof memo === "object" &&
              Object.entries(memo)
                .filter(([k, v]) => typeof v === "string" && v)
                .map(([k, v]) => (
                  <div className="finding" key={k}>
                    <div>
                      <strong>{k.replaceAll("_", " ")}</strong>
                      <p>{String(v)}</p>
                    </div>
                  </div>
                ))}
            {r.kind && (
              <p>
                {r.kind}: {r.message || ""}
              </p>
            )}
            {r.fetch_id && (
              <div className="source-receipt">
                <Link2 size={17} />
                <div>
                  <strong>{r.source_name || "Source capture"}</strong>
                  <span>
                    {r.retrieval_kind === "provider_reported_extract"
                      ? "Provider-reported paraphrase, not verbatim page text"
                      : "Fetched source text"}
                  </span>
                </div>
                <External url={r.final_url}>Open source</External>
              </div>
            )}
            {(r.inspected_evidence || p.receipts || r.receipts || p.retained_sources || r.results || [])
              .slice(0, 12)
              .map((e: Row, i: number) => (
                <div className="source-receipt" key={i}>
                  <Link2 size={16} />
                  <div>
                    <strong>
                      {e.source_name ||
                        e.title ||
                        e.author ||
                        "Research source"}
                    </strong>
                    <span>
                      {e.retrieval_kind === "provider_reported_extract"
                        ? "Provider-reported extract"
                        : e.fetch_id
                          ? "Captured evidence"
                          : "Search result / source finding"}
                    </span>
                    <p>{e.source_summary || e.snippet || ""}</p>
                  </div>
                  <External url={e.final_url || e.url}>Source</External>
                </div>
              ))}
            {a.payload && (
              <Json
                value={a.payload}
                label="Assignment, returned findings & retained evidence"
              />
            )}
          </article>
        );
      })}
      {story && (
        <>
          <div className="eyebrow">DOWNSTREAM DECISION</div>
          <blockquote className="research-verdict">{story.reason}</blockquote>
          <p className="meta-copy">
            Cited evidence IDs:{" "}
            {(story.evidence_fetch_ids || []).join(", ") || "None recorded"}. A
            citation shows use; it does not prove how much a finding influenced
            the writer.
          </p>
        </>
      )}
      <div className="review-callout">
        <div className="eyebrow">QUALITY REVIEW · HUMAN JUDGMENT</div>
        <ul>
          <li>Did the research answer the assignment?</li>
          <li>Was the evidence timely, relevant and accurately represented?</li>
          <li>Did useful findings reach the copy—or justify passing?</li>
          <li>Was the effort proportionate, without repetitive searching?</li>
        </ul>
      </div>
    </div>
  );
}
function VisualPanel({run, story}: {run: Row; story: Row}) {
  const panel = story.visuals || {assets: []};
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  useEffect(() => {setMessage(""); setSubmitted(false);}, [story.id, panel.version]);
  async function request(action: string, asset: Row, preset = "landscape") {
    if (busy || submitted) return;
    setBusy(true); setMessage("");
    try {
      const response = await fetch("/desk/api/visual-action", {method: "POST",
        headers: {"Content-Type": "application/x-www-form-urlencoded"},
        body: new URLSearchParams({k: token, run: run.run_id, story: story.id, action,
          asset: asset.asset_id, preset, version: String(panel.version || 0)}), signal: AbortSignal.timeout(12000)});
      const result = await response.json();
      if (!response.ok || !result.ok) throw Error(result.reason || "Request not accepted");
      setSubmitted(true); setMessage("Queued. The worker will get a fresh editor review before changing an untouched draft.");
    } catch (e: any) {setMessage(e.message || "Could not confirm request; refresh before retrying.");}
    finally {setBusy(false);}
  }
  const locked = busy || submitted || ["pending", "reviewing", "delivery_pending", "awaiting_media", "in_flight", "ambiguous", "needs_owner_review"].includes(panel.request?.state);
  return <div className="inspector-section visual-panel">
    <p className="meta-copy">An image is optional. These are exact stored pixels, not regenerated previews. Source permissions and editorial approval are separate.</p>
    {panel.decision !== "none" && panel.decision && <p className="meta-copy">Image decision: {({approve:"approved",omit:"omitted — text only",hold:"held for review",text_fallback:"approved text fallback — no image"} as Row)[panel.decision] || panel.decision}{panel.delivery_state && ` · Delivery: ${panel.delivery_state.replaceAll("_"," ")}`}</p>}
    {panel.request && <p className="meta-copy">Latest request: {panel.request.action} · {panel.request.state}</p>}
    {message && <p role="status">{message}</p>}
    {!panel.assets.length && <p>No visual was inspected or rendered for this story.</p>}
    {panel.assets.map((a: Row) => <article key={a.asset_id} className="visual-card">
      <div className="visual-card-heading"><strong>{a.kind.replaceAll("_", " ")}</strong>
        {a.asset_id === panel.selected_asset_id && <Pill text="Selected" />}</div>
      <a href={`/desk/visuals/${a.asset_id}?${new URLSearchParams({k: token})}`} target="_blank" rel="noreferrer">
        <img loading="lazy" src={`/desk/visuals/${a.asset_id}?${new URLSearchParams({k: token})}`}
          alt={a.metadata.alt_text || "Source visual under review"} /></a>
      <p>{a.metadata.purpose}</p>
      <dl><dt>Alt text</dt><dd>{a.metadata.alt_text || "Not supplied"}</dd>
        <dt>Source / credit</dt><dd>{a.metadata.credit || "Unknown"} · <External url={a.metadata.source_url}>Source</External></dd>
        <dt>Reuse</dt><dd>{a.metadata.reuse_status?.replaceAll("_", " ") || "Unknown"}</dd>
        <dt>Delivery</dt><dd>{a.upload?.state || "Not uploaded"}{a.upload?.error && ` · ${a.upload.error}`}</dd>
      </dl>
      <div className="visual-actions">
        <Button size="sm" variant="outline" disabled={locked} onClick={() => request("select",a)}>Select for review</Button>
        <Button size="sm" variant="outline" disabled={locked} onClick={() => request("omit",a)}>Use text only</Button>
        {["quote","excerpt","bar","line","comparison"].includes(a.kind) && <Button size="sm" variant="outline" disabled={locked}
          onClick={() => request("regenerate",a,a.metadata.preset === "square" ? "landscape" : "square")}>
          Review {a.metadata.preset === "square" ? "landscape" : "square"} version</Button>}
      </div>
      <details><summary>Exact recipe and provenance</summary><pre>{JSON.stringify(a.metadata,null,2)}</pre></details>
    </article>)}
  </div>;
}
function Inspector({
  run,
  story,
  detail,
  onDetail,
  onCompare,
}: {
  run: Row;
  story: Row;
  detail: string;
  onDetail: (s: string) => void;
  onCompare: () => void;
}) {
  const members = run.candidates.filter((c: Row) =>
    story.members.includes(c.id),
  );
  return (
    <>
      <div className="inspector-heading">
        <span className="eyebrow">SELECTED STORY</span>
        <h2>{story.title}</h2>
        <Pill text={story.outcome} />
      </div>
      <Tabs
        value={detail}
        onValueChange={(v) => onDetail(String(v))}
        className="inspector-tabs"
      >
        <TabsList variant="line">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="research">Research</TabsTrigger>
          <TabsTrigger value="copy">Copy</TabsTrigger>
          <TabsTrigger value="visuals">Visuals</TabsTrigger>
        </TabsList>
        <TabsContent value="overview">
          <div className="inspector-section">
            <div className="eyebrow">THE DECISION</div>
            <p>{story.reason}</p>
            {story.writer_reason && story.writer_reason !== story.reason && (
              <p className="meta-copy">
                Writer’s reader value: {story.writer_reason}
              </p>
            )}
            <div className="inspector-rule" />
            <div className="eyebrow">SOURCE LEADS · {members.length}</div>
            {members.map((c: Row) => (
              <article className="source-receipt" key={c.id}>
                <Inbox size={16} />
                <div>
                  <strong>{c.source}</strong>
                  <span>{c.title}</span>
                  <small>
                    {c.provenance === "writer_packet"
                      ? "Recorded writer input"
                      : "Retained intake; not an exact historical packet"}
                  </small>
                </div>
                <External url={c.url}>Open</External>
              </article>
            ))}
            <div className="inspector-rule" />
            <div className="eyebrow">EDITOR</div>
            {story.editor ? (
              <>
                {["unavailable_fallback", "omitted_fallback"].includes(story.editor.origin) &&
                  <Note>Needs human review — editor response failed</Note>}
                <Pill text={story.editor.verdict} />
                <p>{story.editor.reason}</p>
                <p className="meta-copy">
                  {story.editor.origin?.replaceAll("_", " ")}
                </p>
              </>
            ) : (
              <p>
                No editor response recorded. This is not an editor rejection.
              </p>
            )}
            <div className="inspector-rule" />
            <div className="eyebrow">EVENT IDENTITY</div>
            <p className="meta-copy">
              Submitted: {story.story_key || "Not recorded"}
              <br />
              Effective during review:{" "}
              {story.effective_key || "Not separately recorded"}
            </p>
            <Button
              className="compare-link"
              variant="outline"
              onClick={onCompare}
            >
              Open side-by-side comparison <ArrowUpRight size={16} />
            </Button>
            {story.delivery?.now && (
              <p>
                <External url={story.delivery.now.typefully_url}>
                  Open output in Typefully
                </External>
              </p>
            )}
          </div>
        </TabsContent>
        <TabsContent value="research">
          <Research run={run} story={story} />
        </TabsContent>
        <TabsContent value="copy">
          <CopyPanel story={story} />
        </TabsContent>
        <TabsContent value="visuals"><VisualPanel run={run} story={story} /></TabsContent>
      </Tabs>
    </>
  );
}
function Nav({
  state,
  now,
  navigate,
}: {
  state: State;
  now: Row;
  navigate: (p: Partial<State>, replace?: boolean) => void;
}) {
  const { setOpenMobile } = useSidebar();
  return (
    <Sidebar className="desk-sidebar" collapsible="offcanvas">
      <SidebarHeader>
        <div className="brand">
          <img src={logo} width={36} height={36} alt="" />
          <div>
            Next Block<span>NEWS DESK</span>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <div className="nav-caption">WORKSPACE</div>
        <SidebarMenu>
          {nav.map(({ id, name, icon: Icon }) => (
            <SidebarMenuItem key={id}>
              <SidebarMenuButton
                className="nav-link"
                isActive={state.view === id}
                onClick={() => {
                  navigate({
                    view: id,
                    open: false,
                    page: 1,
                    status: "",
                    q: "",
                  });
                  setOpenMobile(false);
                }}
              >
                <Icon />
                <span>{name}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
        <div className="sidebar-note">
          <span className="small-dot" />
          Autopost {now.autopost ? "ON" : "OFF"}
          <span>
            {now.autopost
              ? "Publication is enabled."
              : "Publication gated in Typefully."}
            <br />
            No publication switches here.
          </span>
        </div>
      </SidebarContent>
      <SidebarFooter>
        <a className="review-tools" href={authUrl("/report", { d: state.d })}>
          Review tools <ArrowUpRight size={16} />
        </a>
        <p className="sidebar-footnote">
          Live production observations.
          <br />
          All times Central.
        </p>
        <div className="profile">
          <span>B</span>
          <div>
            Brady<small>Editor-in-chief</small>
          </div>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}

function App() {
  const [state, setState] = useState<State>(readState),
    [data, setData] = useState<Row | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [paused, setPaused] = useState(false),
    [wide, setWide] = useState(matchMedia("(min-width:1440px)").matches),
    [refresh, setRefresh] = useState(0);
  const stateRef = useRef(state),
    abort = useRef<AbortController | null>(null),
    returnFocus = useRef<HTMLElement | null>(null),
    scroll = useRef(0),
    loadedKey = useRef("");
  const navigate = useCallback((patch: Partial<State>, replace = false) => {
    const s = { ...stateRef.current, ...patch };
    stateRef.current = s;
    setState(s);
    const q: Row = {
      view: s.view,
      run: s.run,
      lead: s.lead,
      tab: s.tab,
      detail: s.detail,
      filter: s.filter,
      follow: s.follow ? "1" : "0",
      open: s.open ? "1" : "0",
      d: s.d,
      q: s.q,
      page: s.page,
      state: s.status,
    };
    history[replace ? "replaceState" : "pushState"](s, "", authUrl("/desk", q));
  }, []);
  useEffect(() => {
    const read = () => {
      const s = readState();
      stateRef.current = s;
      setState(s);
    };
    addEventListener("popstate", read);
    const media = matchMedia("(min-width:1440px)");
    let previous = media.matches;
    const resize = () => {
      if (previous && !media.matches && stateRef.current.lead)
        navigate({ open: true }, true);
      setWide(media.matches);
      previous = media.matches;
    };
    media.addEventListener("change", resize);
    return () => {
      removeEventListener("popstate", read);
      media.removeEventListener("change", resize);
    };
  }, [navigate]);
  const requestKey = [
    state.view,
    state.run,
    state.follow,
    state.d,
    state.q,
    state.page,
    state.status,
  ].join("|");
  useEffect(() => {
    let active = true;
    const timer = setInterval(() => {
      if (!document.hidden && !paused) setRefresh((n) => n + 1);
    }, 15000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [paused]);
  useEffect(() => {
    const controller = new AbortController();
    abort.current?.abort();
    abort.current = controller;
    const s = stateRef.current;
    const different = loadedKey.current !== requestKey;
    if (different) setBusy(true);
    const timeout = setTimeout(() => controller.abort(), 12000);
    fetch(
      authUrl("/desk/api/workspace", {
        view: s.view,
        run: s.follow && s.view === "newsroom" ? "" : s.run,
        d: s.d,
        q: s.q,
        page: s.page,
        state: s.status,
      }),
      { signal: controller.signal, cache: "no-store" },
    )
      .then(async (r) => {
        if (!r.ok)
          throw Error(
            r.status === 403
              ? "Your Desk access link is missing or expired."
              : r.status === 404
                ? "This run is not available in production history."
                : "The Desk connection is temporarily unavailable.",
          );
        return r.json();
      })
      .then((next) => {
        if (controller.signal.aborted) return;
        setError("");
        setBusy(false);
        if (
          !different &&
          (window.getSelection()?.toString() ||
            document.activeElement?.tagName === "INPUT")
        )
          return;
        setData(next);
        loadedKey.current = requestKey;
        if (s.view === "newsroom" && next.run) {
          const r = next.run;
          const selected = r.stories.some(
            (l: Row) => l.id === stateRef.current.lead,
          )
            ? stateRef.current.lead
            : r.stories[0]?.id || "";
          if (
            r.run_id !== stateRef.current.run ||
            selected !== stateRef.current.lead
          )
            navigate(
              {
                run: r.run_id,
                lead: selected,
                open:
                  r.run_id !== stateRef.current.run
                    ? false
                    : stateRef.current.open,
              },
              true,
            );
        }
      })
      .catch((e) => {
        if (controller.signal.aborted && abort.current !== controller) return;
        setBusy(false);
        setError(
          e.name === "AbortError"
            ? "The Desk request timed out. Your previous view is preserved."
            : e.message,
        );
      })
      .finally(() => clearTimeout(timeout));
    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
  }, [requestKey, refresh, navigate]);
  const now = data?.now || {},
    run = data?.run,
    story =
      run?.stories.find((s: Row) => s.id === state.lead) || run?.stories[0];
  const runMatches =
    state.view === "newsroom" &&
    data?.view === "newsroom" &&
    run &&
    (state.follow || run.run_id === state.run);
  const paneRef = useCallback((el: HTMLDivElement | null) => {
    if (el) {
      el.scrollTop = scroll.current;
      el.onscroll = () => {
        scroll.current = el.scrollTop;
      };
    }
  }, []);
  function selectRun(id: string, follow = false) {
    scroll.current = 0;
    navigate({ run: id, follow, lead: "", open: false, filter: "all" });
  }
  function selectStory(s: Row, detail = state.detail) {
    returnFocus.current = document.activeElement as HTMLElement;
    scroll.current = 0;
    navigate({ lead: s.id, open: true, detail });
  }
  function close() {
    navigate({ open: false });
    requestAnimationFrame(() => returnFocus.current?.focus());
  }
  const compare = () => {
    navigate({ tab: "copy", open: false });
    document
      .querySelector(".workspace-tabs")
      ?.scrollIntoView({ block: "nearest" });
  };
  const inspector =
    runMatches && story ? (
      <Inspector
        run={run}
        story={story}
        detail={state.detail}
        onDetail={(detail) => navigate({ detail }, true)}
        onCompare={compare}
      />
    ) : null;
  return (
    <SidebarProvider
      style={{ "--sidebar-width": "13.25rem" } as React.CSSProperties}
    >
      <Nav state={state} now={now} navigate={navigate} />
      <div className="application">
        <header className="topbar">
          <div className="crumb">
            <SidebarTrigger />
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>{nav.find((n) => n.id === state.view)?.name}</strong>
          </div>
          <div className="top-status">
            <span className="small-dot" />
            <span>Worker {now.worker || "connecting"}</span>
            <span className="divider" />
            <span>{clock(data?.observed_at)}</span>
            <button onClick={() => setPaused((v) => !v)} aria-pressed={paused}>
              {paused ? "Resume refresh" : "Pause refresh"}
            </button>
          </div>
        </header>
        <main id="main" className="main-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">NEXT BLOCK NEWS</div>
              <h1>
                {state.view === "newsroom"
                  ? "Inside the newsroom"
                  : nav.find((n) => n.id === state.view)?.name}
              </h1>
            </div>
            <span className="sample-stamp">
              Production<span>Observed {clock(data?.observed_at, true)}</span>
            </span>
          </div>
          {error && (
            <div className="connection-error" role="alert">
              {error}{" "}
              <Button
                variant="outline"
                onClick={() => setRefresh((n) => n + 1)}
              >
                Retry
              </Button>
            </div>
          )}
          {!data && (
            <Empty title="Opening the newsroom">
              Loading recorded runs and current health.
            </Empty>
          )}
          {busy && data && loadedKey.current !== requestKey && (
            <div className="loading-banner" role="status">
              Loading selected view…
            </div>
          )}
          {data && state.view === "newsroom" && data.view === "newsroom" && (
            <>
              <section className="run-bar" aria-label="Selected run">
                <div className="run-identity">
                  <span className="run-icon">
                    <Layers3 size={20} />
                  </span>
                  <div>
                    <Select
                      value={run?.run_id || null}
                      onValueChange={(id) => selectRun(String(id))}
                    >
                      <SelectTrigger
                        className="run-picker"
                        aria-label="Choose a run"
                      >
                        <SelectValue>
                          {run
                            ? `${clock(run.created_at)} run`
                            : "No recorded runs"}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent className="run-picker-options">
                        {(data.navigation.recent || []).map((r: Row) => (
                          <SelectItem key={r.run_id} value={r.run_id}>
                            {clock(r.created_at, true)} · {r.status}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <small>
                      {run
                        ? `${clock(run.created_at, true)} · ${run.status}`
                        : "Waiting for the first production newsroom run"}
                    </small>
                  </div>
                </div>
                <div
                  className="run-pagination"
                  role="navigation"
                  aria-label="Run navigation"
                >
                  <Button
                    variant="ghost"
                    aria-label="Previous run"
                    disabled={!data.navigation.older || busy}
                    onClick={() => selectRun(data.navigation.older)}
                  >
                    <ChevronLeft /> Previous
                  </Button>
                  <Button
                    variant="ghost"
                    aria-label="Next run"
                    disabled={!data.navigation.newer || busy}
                    onClick={() => selectRun(data.navigation.newer)}
                  >
                    Next <ChevronRight />
                  </Button>
                </div>
                <Button
                  className="latest-button"
                  variant="outline"
                  onClick={() => selectRun("", true)}
                >
                  <Radio size={15} />
                  {state.follow ? "Following latest" : "Back to latest"}
                </Button>
              </section>
              {!state.follow && (
                <div className="pinned-notice">
                  <Clock3 size={14} />
                  <span>
                    {data.navigation.latest?.run_id !== run?.run_id
                      ? "Newer runs available. Your selection is pinned."
                      : "History pinned. New runs will not move this view."}
                  </span>
                </div>
              )}
              {!run && (
                <Empty title="No production runs recorded">
                  An intake poll or an empty cadence window is not a newsroom
                  run.
                </Empty>
              )}
              {runMatches && (
                <div className="run-grid">
                  <section className="run-workspace">
                    <div className="run-summary">
                      <span className="status-marker">
                        <Clock3 size={16} />
                        {run.completed_at
                          ? "Recorded run"
                          : "Latest checkpoint"}{" "}
                        · {run.status}
                      </span>
                      <h2>
                        {run.proposal_count ?? "—"} proposal
                        {run.proposal_count === 1 ? "" : "s"}.{" "}
                        {run.delivery_records} delivery record
                        {run.delivery_records === 1 ? "" : "s"}.
                      </h2>
                      <p>
                        {run.run_note ||
                          "Follow the leads through writing, editing and delivery."}
                      </p>
                    </div>
                    <details className="payload">
                      <summary>Writer feedback{run.writer_feedback?.status === "provided" ? " · available" : ""}</summary>
                      <WriterFeedback record={run.writer_feedback} />
                    </details>
                    <Json label="Memory catalog delivered to this run" value={run.packet?.memory_catalog || { status: "Not recorded for this run" }} />
                    <div className="journey">
                      {[
                        [
                          run.packet_recorded
                            ? "Delivered leads"
                            : "Advanced estimate",
                          run.delivered_count ?? run.advanced_estimate ?? "—",
                          Inbox,
                        ],
                        [
                          "Writer proposals",
                          run.proposal_count ?? "—",
                          SquarePen,
                        ],
                        [
                          "Editor responses",
                          run.packet_recorded
                            ? run.stories.filter((s: Row) =>
                                ["initial", "recovery"].includes(
                                  s.editor?.origin,
                                ),
                              ).length
                            : "—",
                          ShieldCheck,
                        ],
                        ["Delivery records", run.delivery_records, Send],
                      ].map(([label, n, Icon]: any) => (
                        <div key={label}>
                          <Icon size={16} />
                          <strong>{n}</strong>
                          <span>{label}</span>
                        </div>
                      ))}
                    </div>
                    {!run.packet_recorded && (
                      <Note>
                        Partial history: the exact writer packet and full stage
                        responses were not retained for this run. Advanced
                        estimates describe preparation, not proof the writer
                        received the leads. Missing editor responses are not
                        zero reviews.
                      </Note>
                    )}
                    <Tabs
                      value={state.tab}
                      onValueChange={(v) => navigate({ tab: String(v) }, true)}
                      className="workspace-tabs"
                    >
                      <TabsList variant="line">
                        {tabNames.map((t) => (
                          <TabsTrigger key={t} value={t}>
                            {t === "desk"
                              ? "Delivered desk"
                              : t[0].toUpperCase() + t.slice(1)}
                          </TabsTrigger>
                        ))}
                      </TabsList>
                      <TabsContent value="decisions">
                        <div className="table-toolbar">
                          <span>
                            {run.stories.length} stories / ungrouped leads
                          </span>
                          <Select
                            value={state.filter}
                            onValueChange={(v) =>
                              navigate({ filter: String(v) }, true)
                            }
                          >
                            <SelectTrigger aria-label="Filter decisions">
                              <SelectValue>
                                {state.filter === "all"
                                  ? "All decisions"
                                  : state.filter}
                              </SelectValue>
                            </SelectTrigger>
                            <SelectContent>
                              {["all", "proposals", "dropped", "deferred"].map(
                                (v) => (
                                  <SelectItem key={v} value={v}>
                                    {v}
                                  </SelectItem>
                                ),
                              )}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="decision-list">
                          {run.stories
                            .filter(
                              (s: Row) =>
                                state.filter === "all" ||
                                (state.filter === "proposals" && s.writer) ||
                                (state.filter === "dropped" &&
                                  s.outcome.includes("Dropped")) ||
                                (state.filter === "deferred" &&
                                  /Deferred|Held|Unfinished/.test(s.outcome)),
                            )
                            .map((s: Row) => (
                              <button
                                className={
                                  "decision-row " +
                                  (s.id === story?.id ? "selected" : "")
                                }
                                data-selected={s.id === story?.id || undefined}
                                key={s.id}
                                onClick={() => selectStory(s)}
                              >
                                <span className="source-avatar">
                                  {s.source?.[0] || "N"}
                                </span>
                                <div className="decision-main">
                                  <h3>{s.title}</h3>
                                  <span>
                                    {s.source} · {s.members.length} lead
                                    {s.members.length === 1 ? "" : "s"}
                                  </span>
                                  <p>{s.reason}</p>
                                </div>
                                <div className="decision-status">
                                  <Pill text={s.outcome} />
                                  <small>
                                    {s.editor
                                      ? "Editor / downstream"
                                      : s.writer
                                        ? "After writing"
                                        : "Writer"}
                                  </small>
                                </div>
                                <ChevronRight size={17} />
                              </button>
                            ))}
                        </div>
                        {!run.stories.length && (
                          <Empty title="No retained writer proposals or decisions">
                            Inspect preparation and the activity trail for the
                            last completed stage.
                          </Empty>
                        )}
                      </TabsContent>
                      <TabsContent value="research">
                        <Research run={run} />
                      </TabsContent>
                      <TabsContent value="desk">
                        <div className="desk-packet">
                          <div className="section-heading">
                            <h3>
                              {run.packet_recorded
                                ? "Delivered to the writer"
                                : "Captured intake & preparation"}
                            </h3>
                            <span>
                              {run.captured ?? "Unknown"} captured ·{" "}
                              {run.background.length} not sent
                            </span>
                          </div>
                          {run.candidates.map((c: Row) => (
                            <article className="desk-candidate" key={c.id}>
                              <span className="tiny-label">
                                {run.background.some((b: Row) => b.id === c.id)
                                  ? "BACKGROUND · NOT SENT"
                                  : "ADVANCED"}{" "}
                                · {c.source}
                              </span>
                              <h3>{c.title}</h3>
                              {c.summary && <p>{c.summary}</p>}
                              <p>{c.assignment}</p>
                              <External url={c.url}>Original lead</External>
                              <Json
                                value={
                                  c.writer_card?.candidate_id
                                    ? c.writer_card
                                    : c.preparation
                                }
                                label={
                                  c.writer_card?.candidate_id
                                    ? "Exact delivered card"
                                    : "Recorded preparation"
                                }
                              />
                            </article>
                          ))}
                          {run.packet_recorded && (
                            <>
                              <h3>Context supplied with this desk</h3>
                              {Object.entries(run.packet)
                                .filter(([k]) => k !== "intake_board")
                                .map(([k, v]) => (
                                  <Json
                                    key={k}
                                    value={v}
                                    label={k.replaceAll("_", " ")}
                                  />
                                ))}
                              {run.packet_truncated && (
                                <Note>
                                  This observation was sanitized or truncated;
                                  it is not a byte-for-byte original.
                                </Note>
                              )}
                            </>
                          )}
                          {!run.packet_recorded && (
                            <Note>
                              Available indexes and today’s mutable memory
                              cannot reconstruct the exact historical prompt.
                            </Note>
                          )}
                        </div>
                      </TabsContent>
                      <TabsContent value="copy">
                        {story ? (
                          <CopyPanel story={story} />
                        ) : (
                          <Empty title="No copy to compare" />
                        )}
                      </TabsContent>
                      <TabsContent value="activity">
                        <div className="activity-list">
                          {run.artifacts.map((a: Row) => (
                            <article key={a.id}>
                              <span className="activity-dot" />
                              <div>
                                <strong>
                                  {a.kind.replaceAll("_", " ")} · {a.phase}
                                </strong>
                                <p>
                                  {clock(a.at, true)}
                                  {a.ref ? " · " + a.ref : ""}
                                  {a.expired ? " · Payload expired" : ""}
                                  {a.truncated ? " · Sanitized/truncated" : ""}
                                </p>
                                <Json
                                  value={a.payload}
                                  label="Recorded handoff"
                                />
                              </div>
                            </article>
                          ))}
                          {!run.artifacts.length && (
                            <Empty title="Detailed activity was not retained">
                              Run start: {clock(run.created_at, true)}. Last
                              checkpoint: {clock(run.updated_at, true)}.
                              Completion: {clock(run.completed_at, true)}.
                            </Empty>
                          )}
                        </div>
                      </TabsContent>
                    </Tabs>
                    <div className="run-footer">
                      <span>
                        {run.cost === null
                          ? "Model cost not recorded"
                          : `${dollars(run.cost, 3)} recorded model cost`}
                        {run.unknown_cost ? " · incomplete" : ""}
                      </span>
                      <span>
                        {run.counters.fetches || 0} successful captures ·{" "}
                        {run.counters.searches || 0} searches
                      </span>
                    </div>
                  </section>
                  {wide && (
                    <aside className="inspector" ref={paneRef}>
                      {inspector || <Empty title="Select a story" />}
                    </aside>
                  )}
                </div>
              )}
              <section className="arriving-panel">
                <div className="section-heading">
                  <h3>Arriving now</h3>
                  <span className="tiny-label">
                    Current intake · separate from this run
                  </span>
                </div>
                <div className="arrival-list">
                  {(data.arriving || []).map((r: Row) => (
                    <article key={r.url_hash}>
                      <span>{clock(r.first_seen)}</span>
                      <div>
                        <strong>{r.title}</strong>
                        <small>
                          {r.source} · {r.status}
                        </small>
                      </div>
                    </article>
                  ))}
                </div>
                <p className="meta-copy">
                  Next editorial deadline: {clock(now.next_desk, true)}. A due
                  deadline waits for the worker and eligible leads.
                </p>
              </section>
            </>
          )}
          {data && data.view === state.view && state.view !== "newsroom" && (
            <Support
              state={state}
              data={data}
              navigate={navigate}
              refresh={() => setRefresh((n) => n + 1)}
            />
          )}
        </main>
      </div>
      <Sheet
        open={!wide && state.open && !!inspector}
        onOpenChange={(v) => {
          if (!v) close();
        }}
      >
        <SheetContent
          className="inspector-drawer"
          side="right"
          showCloseButton={false}
        >
          <SheetHeader className="drawer-heading">
            <SheetTitle>Story detail</SheetTitle>
            <SheetDescription className="sr-only">
              Decisions, research and copy for the selected story.
            </SheetDescription>
            <Button
              variant="ghost"
              aria-label="Close story detail"
              onClick={close}
            >
              <X size={20} />
            </Button>
          </SheetHeader>
          <div className="drawer-scroll inspector" ref={paneRef}>
            {inspector}
          </div>
        </SheetContent>
      </Sheet>
    </SidebarProvider>
  );
}

function Support({
  state,
  data,
  navigate,
  refresh,
}: {
  state: State;
  data: Row;
  navigate: (p: Partial<State>, replace?: boolean) => void;
  refresh: () => void;
}) {
  const [period, setPeriod] = useState("today"),
    [showSources, setShowSources] = useState(false);
  const c = data.costs,
    sp = c?.periods?.[period];
  return (
    <section className="support-view">
      {state.view !== "system" && (
        <>
          <div className="support-intro">
            <div>
              <h2>
                {state.view === "intake"
                  ? "Before the writer"
                  : "From the desk to readers"}
              </h2>
              <p>
                {state.view === "intake"
                  ? "Unique leads first seen on this Central day. Routing and output states are current."
                  : "Locally tracked outputs created or confirmed on this day—not the whole Typefully account."}
              </p>
            </div>
          </div>
          <form className="live-filters" onSubmit={(e) => e.preventDefault()}>
            <label>
              Central day
              <input
                type="date"
                value={state.d || data.day}
                onChange={(e) => navigate({ d: e.target.value, page: 1 }, true)}
              />
            </label>
            <label>
              Find a lead or source
              <input
                aria-label="Find a lead or source"
                value={state.q}
                onChange={(e) => navigate({ q: e.target.value, page: 1 }, true)}
              />
            </label>
            <label>
              State
              <select
                value={state.status}
                onChange={(e) =>
                  navigate({ status: e.target.value, page: 1 }, true)
                }
              >
                <option value="">All</option>
                {(state.view === "intake"
                  ? ["new", "held", "skipped", "drafted", "posted", "failed"]
                  : ["DRAFT", "confirmed", "UNCERTAIN", "FAILED", "IMMEDIATE"]
                ).map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </label>
          </form>
        </>
      )}
      {state.view === "intake" && (
        <>
          <Button variant="outline" onClick={() => setShowSources((v) => !v)}>
            {showSources ? "Show leads" : "Source health"}
          </Button>
          {showSources ? (
            <Sources rows={data.sources} />
          ) : (
            <div className="intake-list">
              {data.items.map((r: Row) => (
                <article className="intake-row live-intake" key={r.url_hash}>
                  <span className="source-avatar">{r.source?.[0]}</span>
                  <div>
                    <h3>
                      <External url={r.url}>{r.title}</External>
                    </h3>
                    <span>
                      {r.source} · {clock(r.first_seen, true)}
                    </span>
                    <p>
                      {r.note ||
                        r.mailroom_reason ||
                        "Awaiting a recorded decision."}
                    </p>
                    <div className="intake-actions">
                      <small>
                        {r.decision_stage || "Intake"} ·{" "}
                        {r.decision_category || r.mailroom_route || r.status}
                      </small>
                      <a
                        href={
                          authUrl("/report", { d: data.day }) +
                          (r.status === "skipped" ? "#skipped" : "#held")
                        }
                      >
                        Review actions ↗
                      </a>
                    </div>
                    {r.preparation && (
                      <p>
                        <button
                          className="text-link"
                          onClick={() =>
                            navigate({
                              view: "newsroom",
                              run: r.preparation.run_id,
                              lead: "lead:" + r.url_hash,
                              follow: false,
                              open: true,
                              tab: "decisions",
                            })
                          }
                        >
                          Open preparation run <ArrowRight size={14} />
                        </button>
                      </p>
                    )}
                    <Reconsider item={r} refresh={refresh} />
                    <Json
                      value={{
                        mailroom: r.mailroom_route,
                        reason: r.mailroom_reason,
                        preparation: r.preparation,
                        owner_override: r.reconsider?.request,
                      }}
                      label="Routing detail"
                    />
                  </div>
                  <Pill text={r.status} />
                </article>
              ))}
            </div>
          )}
          {!data.items.length && !showSources && (
            <Empty title="No matching intake" />
          )}
        </>
      )}
      {state.view === "outputs" && (
        <div className="output-list">
          {data.outputs.map((r: Row) => (
            <article className="output-card" key={r.id}>
              <div className="section-heading">
                <Pill text={r.state} />
                <span className="tiny-label">
                  Local output #{r.id} · {clock(r.created, true)}
                </span>
              </div>
              <Copy body={r.body} label="Current tracked copy" />
              <div className="output-links">
                <External url={r.typefully_url}>Open in Typefully</External>
                {r.public_url && (
                  <External url={r.public_url}>View on X</External>
                )}
                <External url={r.receipt_url}>Source reply receipt</External>
                {r.run_id && (
                  <button
                    className="text-link"
                    onClick={() =>
                      navigate({
                        view: "newsroom",
                        run: r.run_id,
                        lead: r.story_id || "",
                        follow: false,
                        open: true,
                        tab: "copy",
                      })
                    }
                  >
                    Open originating run <ArrowRight size={14} />
                  </button>
                )}
              </div>
              <p className="meta-copy">
                First seen {clock(r.first_seen, true)} · Confirmed publication{" "}
                {clock(r.confirmed_at, true)} · Publisher check{" "}
                {clock(r.publisher_synced_at, true)}.
              </p>
              <p className="meta-copy">
                {r.performance?.likes ?? "Unknown"} likes ·{" "}
                {r.performance?.reposts ?? "Unknown"} reposts · observed{" "}
                {clock(r.performance_synced_at, true)}. Weak, age-dependent
                feedback.
              </p>
            </article>
          ))}
          {!data.outputs.length && <Empty title="No matching local outputs" />}
        </div>
      )}
      {state.view !== "system" && (
        <div className="support-pagination">
          <Button
            variant="outline"
            disabled={state.page <= 1}
            onClick={() => navigate({ page: state.page - 1 })}
          >
            Previous page
          </Button>
          <span>Page {data.page}</span>
          <Button
            variant="outline"
            disabled={!data.more}
            onClick={() => navigate({ page: state.page + 1 })}
          >
            Next page
          </Button>
        </div>
      )}
      {state.view === "system" && (
        <>
          <div className="health-grid">
            {[
              [
                "Worker",
                data.now.worker,
                "Last completed cycle: " + clock(data.now.last_cycle, true),
              ],
              [
                "Publisher",
                data.now.publisher_error ? "Error recorded" : "Reconciliation",
                clock(data.now.publisher_sync, true),
              ],
              [
                "Newsroom",
                `${data.cadence_minutes} min`,
                "Next deadline: " + clock(data.now.next_desk, true),
              ],
              [
                "Publication",
                data.now.autopost ? "Autopost ON" : "Autopost OFF",
                `${data.now.pending_delivery} unresolved delivery operations`,
              ],
            ].map(([label, value, note]) => (
              <article className="health-card" key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
                <small>{note}</small>
              </article>
            ))}
          </div>
          <section className="model-roster">
            <div className="section-heading">
              <div>
                <div className="eyebrow">THE TEAM AT WORK</div>
                <h2>Current model roster</h2>
              </div>
              <span className="tiny-label">
                Observed {clock(data.roster.observed_at, true)}
              </span>
            </div>
            <div className="roster-grid">
              {data.roster.seats.map((r: Row) => (
                <article className="roster-card" key={r.role}>
                  <div className="roster-role">
                    <ShieldCheck size={18} />
                    <span>{r.role}</span>
                    <Pill text={r.mode} />
                  </div>
                  <h3>{r.model}</h3>
                  <p>
                    {r.provider} ·{" "}
                    {r.effort === "No override"
                      ? r.effort
                      : `${r.effort} effort`}
                  </p>
                  <small>{r.note}</small>
                </article>
              ))}
            </div>
            <p className="meta-copy">
              This running process’s configuration—not inferred from older
              calls. Publishing and reconciliation run in code. Historical runs
              retain their recorded models.
            </p>
          </section>
          <section className="feedback-panel">
            <div className="section-heading"><div>
              <div className="eyebrow">FROM THE WRITER’S DESK</div>
              <h2>Writer feedback</h2>
            </div></div>
            <p className="meta-copy">Optional observations, not verified diagnoses. Nothing here changes prompts, policy, memory, or publication automatically. Details retained for 14 days.</p>
            <div className="feedback-grid">
              {(data.writer_feedback?.rows || []).map((r: Row, i: number) =>
                <article className="research-record" key={r.run_id + i}>
                  <WriterFeedback record={r} />
                  <Button variant="outline" onClick={() => navigate({ view: "newsroom", run: r.run_id,
                    follow: false, lead: "", open: false, page: 1 })}>Inspect run <ArrowRight size={14} /></Button>
                </article>)}
            </div>
            {!data.writer_feedback?.rows?.length && <Empty title="No writer feedback recorded yet" />}
            <div className="support-pagination">
              <Button variant="outline" disabled={state.page <= 1} onClick={() => navigate({ page: state.page - 1 })}>Newer feedback</Button>
              <span>Page {data.writer_feedback?.page || 1}</span>
              <Button variant="outline" disabled={!data.writer_feedback?.more} onClick={() => navigate({ page: state.page + 1 })}>Older feedback</Button>
            </div>
          </section>
          <section className="cost-panel">
            <div className="section-heading">
              <div>
                <div className="eyebrow">OPERATING COST</div>
                <h2>What the newsroom costs</h2>
              </div>
              <span className="tiny-label">
                Observed {clock(c.observed_at, true)}
              </span>
            </div>
            <Tabs value={period} onValueChange={(v) => setPeriod(String(v))}>
              <TabsList variant="line">
                {["today", "week", "month"].map((v) => (
                  <TabsTrigger value={v} key={v}>
                    {v === "today"
                      ? "Today"
                      : v === "week"
                        ? "Week to date"
                        : "Month to date"}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
            {!sp ? (
              <Empty title="No model usage recorded" />
            ) : (
              <>
                <div className="cost-kpi-grid">
                  {[
                    [
                      "Known spend",
                      dollars(sp.cost),
                      `${sp.calls} calls · ${sp.start} through ${sp.through}`,
                    ],
                    [
                      "Per newsroom run",
                      dollars(sp.per_run, 3),
                      `${sp.runs} distinct metered runs · direct costs only`,
                    ],
                    [
                      "Shared costs",
                      dollars(sp.shared_cost, 3),
                      "Intake / preparation without a linked newsroom",
                    ],
                    [
                      "Unknown-cost calls",
                      sp.unknown,
                      sp.unknown
                        ? "Totals are incomplete lower bounds"
                        : "All recorded calls have a cost basis",
                    ],
                  ].map(([label, value, note]) => (
                    <article className="cost-kpi" key={String(label)}>
                      <span>{label}</span>
                      <strong>{value}</strong>
                      <small>{note}</small>
                    </article>
                  ))}
                </div>
                <div className="table-scroll">
                  <table className="cost-table">
                    <thead>
                      <tr>
                        <th>Stage</th>
                        <th>Spend</th>
                        <th>Share</th>
                        <th>Calls</th>
                        <th>Direct / run</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sp.stages.map((s: Row) => (
                        <tr key={s.name}>
                          <td>
                            <strong>{s.name}</strong>
                            <small>{s.models.join(" · ")}</small>
                          </td>
                          <td>
                            {dollars(s.cost, 3)}
                            {s.unknown ? " + unknown" : ""}
                          </td>
                          <td>
                            {sp.cost ? Math.round((s.cost / sp.cost) * 100) : 0}
                            %
                          </td>
                          <td>{s.calls}</td>
                          <td>
                            {dollars(
                              sp.runs ? s.linked_cost / sp.runs : null,
                              3,
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <Note>
                  Writing includes research done inside the desk session. Zero
                  delegated research calls does not mean no research. Shared
                  intake isn’t arbitrarily assigned to a run.
                </Note>
                <p className="meta-copy">
                  {dollars(sp.reported, 3)} provider-reported ·{" "}
                  {dollars(sp.estimated, 3)} rate-estimated. Native tools are
                  already included in xAI’s reported totals.
                </p>
              </>
            )}
            <div className="section-heading">
              <h3>Average completed periods</h3>
              <span className="tiny-label">Not a forecast</span>
            </div>
            <div className="cost-average-grid">
              {["day", "week", "month"].map((unit) => (
                <article key={unit}>
                  <span>Per {unit}</span>
                  <strong>{dollars(c.averages?.[unit]?.value)}</strong>
                  <small>
                    {c.averages?.[unit]?.count || 0} complete Central calendar{" "}
                    {unit}s
                    {c.averages?.[unit]?.unknown ? " · incomplete cost" : ""}
                  </small>
                </article>
              ))}
            </div>
            <p className="meta-copy">
              Ledger begins {clock(c.ledger_start, true)}. Review window:{" "}
              {c.coverage_from || "not available"} through {c.through || "now"}{" "}
              (up to 93 days). Partial opening/current periods are excluded from
              averages; covered zero-call days count. Historical model rosters
              are blended.
            </p>
            {c.bounded && (
              <Note>
                Query limit reached. Totals are partial; complete-period
                averages are unavailable.
              </Note>
            )}
            <p className="meta-copy">
              Excluded replay / test / shadow: {dollars(c.excluded?.cost)} ·
              Unclassified traffic: {dollars(c.unclassified?.cost)}. Neither is
              silently counted as production.
            </p>
            <Note>
              This is the recorded model ledger, not the full invoice. Source
              services, external search, Railway, Typefully, past legacy receipt
              audits and Codex are outside its scope.
            </Note>
          </section>
          <section className="system-section">
            <h2>Sources & dependencies</h2>
            <Sources rows={data.sources} />
            <p className="meta-copy">
              Node fetch: {clock(data.now.node_fetch, true)} · Upstream pulse:{" "}
              {data.now.node_generated || "Not recorded"}
              {data.now.node_error ? " · Node error recorded" : ""}.
            </p>
            {data.search.map((s: Row) => (
              <article className="dependency" key={s.provider}>
                <strong>{s.provider}</strong>
                <Pill text={s.state} />
                <span>
                  {s.total_searches_left ?? "Unknown"} searches left ·{" "}
                  {s.consecutive_failures} consecutive failures ·{" "}
                  {s.error_kind || "No error recorded"}
                </span>
              </article>
            ))}
          </section>
          {data.perception && (
            <section className="system-section">
              <h2>Perception reporting</h2>
              <p className="meta-copy">One reporting interface · separate REST and MCP capacity.
                New research allowance: {data.perception.daily_new_work_limit}/day,
                including up to {data.perception.survey_daily_limit} subject surveys.</p>
              <div className="health-grid">
                {["rest", "mcp"].map((surface) => (
                  <article className="dependency" key={surface}>
                    <strong>{surface.toUpperCase()} today (UTC)</strong>
                    <span>{data.perception.today.filter((r: Row) => r.surface === surface)
                      .reduce((n: number, r: Row) => n + r.attempts, 0)} recorded NBN attempts</span>
                  </article>
                ))}
              </div>
              <p className="meta-copy">Last feed: {clock(data.perception.feed.last_success, true)} ·
                {!data.perception.feed.last_success ? " Not observed" : data.perception.feed.partial ? " Partial coverage / backlog" : " Last window caught up"} ·
                Next backlog page: {data.perception.feed.next_page || "None recorded"}.</p>
              <Note>{data.perception.quota_scope}. Search results are pointers; article text may be partial.
                Shared source reuse does not refresh the original publication date.</Note>
              <p className="meta-copy">Reuse since release: {data.perception.reuse_since_release.query_cache_hits || 0} query-cache hits ·
                {" "}{data.perception.reuse_since_release.retained_article_reads || 0} retained-article reads.
                These avoid provider retrieval, not the Writer's reading cost.</p>
              <Json label="Recent Perception requests and backoff" value={data.perception} />
            </section>
          )}
          <section className="system-section">
            <h2>Recent model calls</h2>
            <p className="meta-copy">
              A transport success is not a successful editorial outcome. Review
              the originating run’s decisions.
            </p>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Seat / model</th>
                    <th>Recorded</th>
                    <th>Result</th>
                    <th>Duration</th>
                    <th>Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_calls.map((r: Row, i: number) => (
                    <tr key={i}>
                      <td>
                        {r.seat}
                        <small>
                          {r.model} · {r.effort || "default"}
                        </small>
                      </td>
                      <td>{clock(r.created_at)}</td>
                      <td>{r.outcome}</td>
                      <td>{(r.latency_ms / 1000).toFixed(1)}s</td>
                      <td>
                        {r.cost_source === "unknown"
                          ? "Unknown"
                          : dollars(r.estimated_cost_usd, 3)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <a
              className="review-tools"
              href={authUrl("/desk/system-guide.pdf")}
            >
              Visual system guide ↗
            </a>
          </section>
        </>
      )}
    </section>
  );
}
function Sources({ rows }: { rows: Row[] }) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>Source / lane</th>
            <th>Last poll result</th>
            <th>Last successful poll</th>
            <th>Results</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.source_key}>
              <td>
                {r.label}
                <small>
                  {r.kind} · {r.cadence}s throttle / loop
                </small>
              </td>
              <td>
                <Pill text={r.enabled ? r.outcome : "Disabled"} />
                <small>
                  {clock(r.attempted_at, true)} {r.error_kind}
                </small>
              </td>
              <td>{clock(r.succeeded_at, true)}</td>
              <td>{r.result_count ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="meta-copy">
        Successful empty polls are healthy. These are existing source polls, not
        extra checks. Not observed means the new health recording has no
        observation yet; throttle skips do not overwrite the last real result.
      </p>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
