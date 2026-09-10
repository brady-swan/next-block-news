"""Read-only research capability smoke; only public BIS and a saved source PDF."""
import json
import os
from pathlib import Path
import subprocess

from local_probe import STATE, WORK, runtime_env

os.environ.clear()
os.environ.update(runtime_env())

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, chromium_sandbox=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 1000},
                                  service_workers='block', accept_downloads=False)
    page = context.new_page()
    response = page.goto('https://www.bis.org/', wait_until='domcontentloaded', timeout=45000)
    screenshot = WORK / 'bis-browser-smoke.png'
    page.screenshot(path=str(screenshot))
    print(json.dumps({'browser_url': page.url, 'status': response.status if response else None,
                      'title': page.title(), 'text_excerpt': page.locator('body').inner_text()[:1000],
                      'screenshot': str(screenshot), 'bytes': screenshot.stat().st_size}), flush=True)
    context.close()
    browser.close()

source = Path('/Users/brady/claude/next-block-news/audit/evidence/2026-09-09-treasury-buyback-schedule.pdf')
local = WORK / 'treasury-pdf-smoke.pdf'
local.write_bytes(source.read_bytes())
result = subprocess.run(['/opt/homebrew/bin/pdftotext', '-layout', '-f', '1', '-l', '1',
                         str(local), '-'], capture_output=True, text=True, check=True, timeout=15)
subprocess.run(['/opt/homebrew/bin/pdftoppm', '-f', '1', '-singlefile', '-scale-to', '1600',
                '-png', str(local), str(WORK / 'treasury-pdf-smoke')],
               capture_output=True, check=True, timeout=20)
print(json.dumps({'pdf_text_excerpt': result.stdout[:2500],
                  'render': str(WORK / 'treasury-pdf-smoke.png')}), flush=True)
