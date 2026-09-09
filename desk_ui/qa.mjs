// Run against scripts/preview_workspace.py. Offline fixtures; no provider requests.
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import assert from "node:assert/strict";
const req = createRequire(
  process.env.NBN_QA_RUNTIME ||
    "/Users/brady/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/package.json",
);
const { chromium } = req("playwright");
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ viewport: { width: 1728, height: 1117 } });
const base =
  process.env.NBN_QA_URL || "http://127.0.0.1:8766/desk?k=local-preview";
const errors = [],
  passed = [];
page.on("pageerror", (e) => errors.push(e.message));
const check = (v, label) => {
  assert.ok(v, label);
  passed.push(label);
};
await mkdir("outputs/qa", { recursive: true });
async function ready() {
  await page.locator(".run-summary").waitFor();
  await page.waitForTimeout(250);
}
async function tab(name) {
  await page
    .locator('.workspace-tabs>[data-slot="tabs-list"]')
    .getByRole("tab", { name, exact: true })
    .click();
  await page.waitForTimeout(150);
}
async function overflow(label) {
  check(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
    label + " no horizontal overflow",
  );
}
try {
  await page.goto(base);
  await ready();
  check(
    new URL(page.url()).searchParams.get("k") === "local-preview",
    "Authenticated URL preserved after initial selection",
  );
  check(
    (await page.locator(".run-summary").innerText()).includes("2 proposals"),
    "Real dossier proposals projected",
  );
  check(
    (await page.locator(".journey").innerText()).includes("4"),
    "Background excluded from delivered count",
  );
  await page.screenshot({
    path: "outputs/qa/newsroom-1728.png",
    fullPage: true,
  });
  check((await page.locator('.handoff-panel').innerText()).includes('individual Bitcoin use'), 'Required next-shift letter visible');
  await page.locator('.handoff-panel').screenshot({path:'outputs/qa/letter-panel.png'});
  await page.getByRole("button", { name: "Previous run", exact: true }).click();
  await ready();
  check(
    new URL(page.url()).searchParams.get("run") === "cycle:fixture-1",
    "Previous run stable identity",
  );
  check(
    new URL(page.url()).searchParams.get("follow") === "0",
    "History is pinned",
  );
  await page.getByRole("button", { name: "Previous run", exact: true }).click();
  await ready();
  check(
    (await page.locator(".run-summary").innerText()).includes("0 proposals"),
    "Zero-output run included",
  );
  check(
    await page
      .getByRole("button", { name: "Previous run", exact: true })
      .isDisabled(),
    "Oldest end disabled",
  );
  await page.getByRole("button", { name: "Next run", exact: true }).click();
  await ready();
  await page.goBack();
  await ready();
  check(
    new URL(page.url()).searchParams.get("run") === "cycle:fixture-0",
    "Browser Back restores prior run",
  );
  await page
    .getByRole("button", { name: "Back to latest", exact: true })
    .click();
  await ready();
  check(
    new URL(page.url()).searchParams.get("follow") === "1",
    "Back to latest resumes following",
  );
  await tab("Research");
  check(
    await page
      .getByRole("heading", { name: "Prepared source capture" })
      .isVisible(),
    "Prefetched evidence first class",
  );
  check(
    await page.getByText("research story", { exact: true }).isVisible(),
    "Research return visible",
  );
  await page.screenshot({
    path: "outputs/qa/research-1728.png",
    fullPage: true,
  });
  await tab("Copy");
  check(
    await page.locator(".run-workspace .copy-comparison").isVisible(),
    "Copy comparison visible",
  );
  check(
    (await page.locator(".inspector .copy-version").count()) === 0,
    "Inspector independent of main tab",
  );
  await page.screenshot({ path: "outputs/qa/copy-1728.png", fullPage: true });
  await tab("Decisions");
  for (const width of [320, 390, 768, 1024, 1440, 1728, 1920, 2560]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.waitForTimeout(150);
    // Resizing a selected wide inspector deliberately opens its drawer.
    const close = page.getByRole("button", {
      name: "Close story detail",
      exact: true,
    });
    if (await close.isVisible()) await close.click();
    await overflow(String(width));
    await page.screenshot({
      path: `outputs/qa/newsroom-${width}.png`,
      fullPage: true,
    });
    await page.locator(".decision-row").first().click();
    if (width < 1440) {
      await page.getByRole("dialog").waitFor();
      await page.waitForTimeout(350);
      check(
        await page.locator(".inspector-drawer").isVisible(),
        width + " uses detail drawer",
      );
    } else
      check(
        await page.locator("aside.inspector").isVisible(),
        width + " uses persistent inspector",
      );
    await page
      .locator(".inspector:visible")
      .getByRole("tab", { name: "Copy", exact: true })
      .click();
    check(
      await page
        .locator(".inspector:visible .copy-version")
        .first()
        .evaluate((el) => parseFloat(getComputedStyle(el).paddingLeft) >= 18),
      width + " post-card padding",
    );
    await page.screenshot({
      path: `outputs/qa/detail-${width}.png`,
      fullPage: width >= 1440,
    });
    if (width < 1440) {
      await page.keyboard.press("Escape");
      await page.getByRole("dialog").waitFor({ state: "hidden" });
      check(
        !(await page.getByRole("dialog").isVisible()),
        width + " Escape closes inspector",
      );
    }
  }
  await page.setViewportSize({ width: 1728, height: 1117 });
  await page.getByRole("button", { name: "System", exact: true }).click();
  await page.getByRole("heading", { name: "Current model roster" }).waitFor();
  check(
    (await page.locator(".roster-grid").innerText()).includes("disabled"),
    "Daily audit disabled in current roster",
  );
  await page.screenshot({ path: "outputs/qa/system-1728.png", fullPage: true });
  const continuityPanel = page.locator('.feedback-panel').filter({has: page.getByRole('heading', {name:'What the next desk is watching'})});
  check((await continuityPanel.innerText()).includes('original dataset confirmed'), 'Active reporting question visible');
  check((await continuityPanel.innerText()).includes('Ranked keyword fallback'), 'Embedding fallback honestly visible');
  await continuityPanel.screenshot({path:'outputs/qa/continuity-panel.png'});
  for (const width of [390, 1024, 2560]) {
    await page.setViewportSize({ width, height: 1000 });
    await overflow("System " + width);
    await page.screenshot({
      path: `outputs/qa/system-${width}.png`,
      fullPage: true,
    });
  }
  await page.goto(base.replace("/desk?", "/report?"));
  await page
    .getByRole("heading", { name: "Review tools", exact: true })
    .waitFor();
  check(
    await page.locator("#needs-you").isVisible(),
    "Review action queue visible",
  );
  check(
    (await page.locator(".legacy-diagnostics").first().getAttribute("open")) ===
      null,
    "Legacy diagnostic wall collapsed",
  );
  await page.screenshot({ path: "outputs/qa/review-2560.png", fullPage: true });
  await page.goto(base + "&view=outputs");
  await page
    .getByText("Current tracked copy", { exact: true })
    .first()
    .waitFor();
  await page.screenshot({
    path: "outputs/qa/outputs-2560.png",
    fullPage: true,
  });
  await page.goto(base + "&view=intake");
  await page.locator(".intake-list").waitFor();
  await page.screenshot({ path: "outputs/qa/intake-2560.png", fullPage: true });
  await page.goto(base);
  await ready();
  await page.route("**/desk/api/workspace?*", (r) =>
    r.fulfill({ status: 503, body: "unavailable" }),
  );
  await page.getByRole("button", { name: "Previous run", exact: true }).click();
  await page.getByRole("alert").waitFor();
  check(
    await page.getByRole("button", { name: "Retry", exact: true }).isVisible(),
    "Failure preserves retry affordance",
  );
  check(errors.length === 0, "No browser exceptions: " + errors.join("; "));
  console.log(
    JSON.stringify({ passed: passed.length, checks: passed }, null, 2),
  );
  await writeFile(
    "outputs/qa/results.json",
    JSON.stringify({ passed, errors }, null, 2),
  );
} finally {
  await browser.close();
}
