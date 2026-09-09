# Audit environment-metadata correction — September 9, 2026

This is a new, local-only diagnostic correction, not a repeat of the completed Perception
release or original continuity work. The 05:14 heartbeat supplied a host date/environment
update in a user-role message. Its structured metadata was
`content_item_kinds=["environments.environment_context"]`; the helper classified it as an
owner trigger before the actual heartbeat arrived.

Actual journal: turn `01a08496-870b-73d1-bf5a-2dfb5427c25b`, start05:14:12.638UTC;
heartbeat `fco_01a08496-871e-7c42-a145-392dea1e0e6f`, scheduled05:14:12.618UTC and recorded
05:14:12.668UTC. Raw metadata inspection and a read-only resolver pass established the
heartbeat/no-owner-steering identity before audit changes. No old user request was resumed.

Smallest repair: recognize that exact host metadata kind alongside `agents_md.instructions`.
Only nonempty lists containing exclusively known host kinds are ignored for trigger detection.
Mixed, unknown, malformed (including unhashable members), untagged and real user XML messages
stay user input. Host context remains binding; it just is not a newly submitted request.

Independent lead approved the plan and final two-file diff. All20continuity tests pass,
including new regression cases; reviewer independently ran them and checked the diff.
The normal helper CLI now recognizes this same live heartbeat and reports no owner steering.
No Railway deployment, model/prompt/credential change, automation mutation or Typefully write
is part of this repair. The local helper is used by the laptop audit, not the NBN worker.

Rollback is the small helper/test diff only; no data restoration. Future unknown host metadata
still requires inspection. This is not proof every future host format is covered.
