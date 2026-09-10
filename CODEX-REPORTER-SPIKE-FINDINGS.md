# Codex reporter compatibility spike — September 10, 2026

## Outcome

Phase 1 is **blocked on sandbox compatibility on the tested Railway container**.
This is not a failed model-quality test: no account login, model turn, browser
research session, or Typefully write occurred. The rest of sprint 0076 is not built.

The independent lead reviewer approved the plan and isolated spike, with an explicit
gate: prove the runtime can protect its account credentials and supervisor controls
before signing in. The required policy failed on this host. We did not relax it.

## What was built

An isolated compatibility image in `infra/codex-reporter/`, with:

- Codex CLI 0.154.0, Python SDK `openai-codex` 0.147.0, and explicit runtime selection.
- Planned Astra medium / Standard, ChatGPT-only login, and no API fallback.
- Playwright 1.62.0 / Chromium and Poppler installed for subsequent capability tests.
- A persistent volume, separate workspace/control/auth directories, and UID 10001.
- A health-only startup process, with no editorial loop, NBN connection or publisher.
- Operator-only, no-secret sandbox canaries that must pass before login or inference.

Only this small directory was uploaded, not the dirty repository checkout. No
existing NBN runtime code, source roster, prompts, draft content or settings changed.

## Actual-host evidence

| Check | Observed result |
| --- | --- |
| Isolated image build and deployment | Success; health-only worker started |
| SDK ↔ pinned CLI metadata handshake as UID 10001 | Passed; SDK 0.147.0, CLI 0.154.0 |
| Existing reporter login | None: `account_present: false` |
| Runtime model listing | Astra listed, including medium effort; not proof of account entitlement or inference |
| Normal Codex sandbox canary | Failed before executing the canary |
| Direct user-namespace probe | `unshare: unshare failed: Permission denied` |
| Namespace sysctl reads | `max_user_namespaces=1321632`, `unprivileged_userns_clone=1` |
| Runtime compatibility feature | `use_legacy_landlock` exposed as deprecated, not removed |
| One compatibility probe with unchanged permissions | Rejected as incompatible with the required permission profile |

Normal sandbox failure:

```text
bwrap: Creating new namespace failed: Permission denied
```

Compatibility-path failure:

```text
permission profiles requiring direct runtime enforcement are incompatible with --use-legacy-landlock
```

The container reported seccomp mode 2 and no CAP_SYS_ADMIN. These observations, plus
the direct `unshare` failure, establish a restriction in this running environment;
they do not establish which particular host rule Railway could change. A positive
namespace sysctl alone does not establish permission to create a namespace.

The compatibility probe changed only the runtime's exposed Landlock selector for
that one command. It retained every credential/control read denial, allowed-workspace
rule and network restriction. It did not authenticate or enable unrestricted execution.

The SDK metadata handshake is only a partial pass. Inference, effective model/effort
after session resume, real browser/image/PDF use, restart continuity, private tool
access and draft delivery remain **untested**.

## Why stop here

The new worker would hold a login to the owner's Codex account. Basic workspace-write
mode is not equivalent to the reviewed profile: broad reads would expose that login
to shell commands. Directory mode 0700 does not separate processes running as the
same account. The approved pilot does not authorize silently downgrading isolation.

OpenAI documents that the Linux bubblewrap path and bundled helper require user
namespaces. It also documents compatibility restrictions for fine-grained filesystem
policies. The actual-host failures above are consistent with those limitations.
[Sandboxing](https://learn.chatgpt.com/docs/sandboxing),
[permissions](https://learn.chatgpt.com/docs/permissions).

This does **not** claim that Codex can never run on Railway. It means this tested
Railway environment cannot run the approved combination of shell capability and
credential/control isolation. We have not tested alternative account/tool isolation
architectures, and they would require a revised plan rather than an ad hoc bypass.

## Next decision

Recommended: keep the existing NBN backend on Railway and place only the Codex
reporter on a conventional Linux VM where the required sandbox can run. Verify the
same no-login canary on that host before proceeding. A cross-host deployment also
needs a small authenticated HTTPS connection to the NBN adapter, rather than relying
on Railway-only private service DNS. Provider, machine and spending need owner approval.

A local Mac pilot is a reasonable shorter path if the owner prefers to prove the
workflow first and can keep the machine awake. It does not prove always-on hosting.
It would still require the same bounded draft-only integration and capability tests.

Neither option has been provisioned, logged in, or started. The reviewed backend
integration work remains useful; it has deliberately not been built ahead of the
runtime compatibility gate.

## Independent checkpoint review

The lead reviewer approved preserving this stopped partial spike. Before any future
authentication attempt, tighten the probe receipt: invalidate it before testing and
bind a pass to the current runtime/configuration, rather than checking file existence.
Also test the active auth-side configuration and workspace `.codex` protections;
root ownership of `/opt/nbn-reporter/config.toml` alone does not prove those boundaries.
These are follow-up requirements, not completed fixes. No successful sandbox receipt
was produced on this host, so no stale pass has authorized login.

## Resources and safe checkpoint

- Branch: `codex/0076-codex-newsroom-pilot`; unrelated working-tree changes preserved.
- Railway project: `1e1f32d1-6153-4f71-80b3-9543050caa7e`.
- Isolated service: `nbn-codex-reporter`, `5a11533a-3202-4fc6-9c1f-2314a379250d`.
- Spike deployment: `d65e813a-6a82-4bdf-b0b2-09c2223d05cc`.
- Volume: `1412f18d-d27d-41ed-afb2-d9e54ef3370a`, mounted at `/reporter-state`.
- No public domain was created; variable names checked for unintended API/publisher keys.
- The original NBN backend, embedding service and audit have not been restarted.
- Health-only spike shutdown completed. Railway readback confirmed zero active
  deployments and no latest deployment for all three services; volumes retained.
- Both the dedicated audit and completed direct-reporting-shift automations remain
  `PAUSED`, verified from their saved configuration.
- No account credentials were added. No model or Typefully usage occurred in this spike.

Local follow-up hardening in `probe.py` sanitizes the SDK parent's environment and
explicitly enables Chromium's own sandbox. These changes were **not deployed or
browser-tested**. Do not mistake a successfully built browser dependency for verified
browser execution, or use the older deployed browser probe to waive that check.

Stop here pending the owner's hosting decision. Do not restart the old system, audit,
or completed reporting shift; do not continue automatically from the build approval
as though all compatibility gates passed.
