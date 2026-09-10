# Local Codex reporter pilot —0076

Current host: `/Users/brady/codex/nbn-reporter-pilot`. Runtime and separate account login
are already installed. Do not repeat device login or use the historical container spike.
No API model key fallback, autopost, existing-draft writes, or old audit/pipeline restart.

The operator-only setup script copies reviewed tools/instructions into the isolated runtime;
it preserves auth. `prepare` changes the configuration binding: run the updated local
sandbox probe again, then check effective config/session before inference. Never relax
the inner sandbox if an outer operator sandbox prevents running the probe.

`reporter_setup.py provision` sets only the five approved NBN reporter/mode variables on
the exact production service, passing tokens through stdin and skipping deployment.
Keep generated connection files in the protected `control` directory, never the repo.
The reporter token and supervisor token are distinct and absent from model environment.
The exact13 reviewed MCP tools are explicitly preapproved; unknown future tools are
not enabled. `auto` is not preapproval under an unattended `never` approval policy.
Shell/network/credential boundaries remain unchanged. Smoke an actual model tool call,
not merely tools/list, before treating the reporter connection as operational.

Deploy a clean, reviewed checkout of the backend, with infrastructure mode and autopost
OFF. Verify health, unauthenticated rejection, exact roles, tools, read-only baseline and
Desk. The eight September10 morning experiment drafts are imported/synchronized, not rebuilt.

Once ready, operator `reporter_supervisor.py start` creates a fixed7200-second shift and
persists the immutable cutoff outside model reach. Its prewritten start-intent ID allows
safe recovery after a lost start response. Never remove that file to evade a cutoff.
`run` resumes only that shift/session. One process lock,20-second lease checks and
five-minute model cooldown; idle unchanged polls do not invoke the model. `caffeinate`
holds the awake Mac only for the supervisor lifetime. `pause` revokes the remote shift;
`status` reads its pulse. No command automatically creates the next pilot.

Run from the reviewed runtime using its venv Python, with stdout/stderr in protected
control logs. Keep all backend/source/publisher credentials on Railway. A later host
migration is separate work; Railway Cloud Agents availability does not authorize one.

The MCP server returns actual image content blocks. Browser access is public HTTP(S)
GET/HEAD only, in a new isolated context with private-address checks, service workers,
WebSockets and downloads disabled. Browser screenshots are research, not reuse authority.
Backend images/renderer use the existing asset store and Typefully media outbox.

Observe Desk → Codex pilot and backend records. Messages use stable IDs and authenticated
senders; only a reply to a delivered same-shift message acknowledges it. Existing Typefully
comments are contextual feedback, never infrastructure or publishing commands.

At cutoff/pause/failure the model stops. Infrastructure may stay up for read-only review.
An ambiguous submission is never retried under a new ID: reconcile read-only or ask the owner.
Rollback stops the pilot; it does not switch the old pipeline back on.
