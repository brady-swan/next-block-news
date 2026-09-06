// Destructive only to the disposable loopback fixture: never use a production URL.
import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
import assert from "node:assert/strict";
const require = createRequire("/Users/brady/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/package.json");
const { chromium } = require("playwright");
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ viewport: { width: 1728, height: 1117 } });
const base = "http://127.0.0.1:8766/desk/intake?k=local-preview";
const errors = [];
let posts = 0;
page.on("pageerror", e => errors.push(e.message));
page.on("request", r => { if (r.method() === "POST") posts++; });
try {
  await mkdir("outputs/qa", { recursive: true });
  await page.goto(base);
  const card = page.locator(".live-intake").filter({ has: page.getByRole("button", { name: "Send to newsdesk", exact: true }) }).first();
  await card.waitFor();
  for (const width of [390, 768, 1728, 2560]) {
    await page.setViewportSize({ width, height: 1117 });
    const layout = await card.evaluate(el => {
      const title = el.querySelector("h3 a span").getBoundingClientRect();
      const arrow = el.querySelector("h3 a svg").getBoundingClientRect();
      const meta = el.querySelector(".intake-actions small").getBoundingClientRect();
      const link = el.querySelector(".intake-actions a").getBoundingClientRect();
      return { titleTop: title.top, arrowTop: arrow.top, gap: link.left - meta.right,
        wrapped: link.top > meta.bottom, overflow: document.documentElement.scrollWidth > innerWidth + 1 };
    });
    assert.ok(Math.abs(layout.arrowTop - layout.titleTop) < 12, `title arrow same first line at ${width}`);
    assert.ok(layout.wrapped || layout.gap >= 12, `review link separated at ${width}`);
    assert.ok(!layout.overflow, `no overflow at ${width}`);
  }
  await page.setViewportSize({ width: 1728, height: 1117 });
  // Explicit rejection renders in place and is safe to retry after refresh.
  await page.route("**/desk/api/item-action", async route => {
    await route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ ok: false, reason: "Fixture conflict; refresh this card" }) });
    await page.unroute("**/desk/api/item-action");
  });
  await card.getByRole("button", { name: "Send to newsdesk", exact: true }).click();
  await page.getByRole("alert").filter({ hasText: "Fixture conflict" }).waitFor();
  const before = posts;
  await card.getByRole("button", { name: "Send to newsdesk", exact: true }).evaluate(button => { button.click(); button.click(); });
  const queued = page.getByRole("button", { name: "Queued for newsdesk", exact: true });
  await queued.waitFor();
  assert.equal(posts - before, 1, "double click sends exactly one request");
  assert.ok(await queued.isDisabled());
  await page.reload();
  await queued.waitFor();
  assert.ok(await queued.isDisabled(), "queue state survives reload");
  assert.ok((await page.locator(".reconsider-control").innerText()).includes("Brady"), "owner note shown");
  await page.screenshot({ path: "outputs/qa/intake-reconsider-1728.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "outputs/qa/intake-reconsider-390.png", fullPage: true });
  assert.deepEqual(errors, []);
  console.log("PASS: arrow/link layout at four widths; inline conflict; single POST on double click; durable queued state; owner notice; no browser errors.");
} finally {
  await browser.close();
}
