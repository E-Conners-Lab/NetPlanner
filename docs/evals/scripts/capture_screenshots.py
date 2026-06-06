"""Capture NetPlanner-on-Nemotron screenshots for the writeup (Phase 2a).

Drives the live app through Playwright: registers a throwaway account, creates a
project with context, and asks the Advisor a strategy question phrased to stay
single-round (Finding #6: Nemotron is eager to call the research tool). Saves
screenshots to ../images/.

Prereqs — the app must be running on Nemotron:
    # backend (from backend/):
    PROVIDER=nvidia_nim uv run uvicorn app.main:app --port 8000
    # frontend (from frontend/):
    npm run dev

Run (from backend/, so Playwright is on the env):
    uv run --with playwright python -m playwright install chromium   # once
    uv run --with playwright python ../docs/evals/scripts/capture_screenshots.py
"""

import asyncio
import time
from pathlib import Path

from playwright.async_api import async_playwright

BASE = "http://localhost:5173"
OUT = Path(__file__).resolve().parents[1] / "images"
OUT.mkdir(parents=True, exist_ok=True)

EMAIL = f"nemotron.demo+{int(time.time())}@netplanner.test"
PASSWORD = "NemotronEval2026!"  # >=12 chars, demo-only throwaway account

QUESTION = (
    "Without looking up current prices, help me frame a CapEx vs OpEx narrative "
    "for refreshing our 220 campus access points, and outline the ROI argument I "
    "should bring to the budget committee."
)


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await (
            await browser.new_context(
                viewport={"width": 1320, "height": 940}, device_scale_factor=2
            )
        ).new_page()

        # 1. Register a throwaway account.
        await page.goto(f"{BASE}/register", wait_until="networkidle")
        await page.fill("input[type=email]", EMAIL)
        await page.fill("input[type=password]", PASSWORD)
        await page.click("button:has-text('Create account')")
        await page.wait_for_selector("text=Dashboard", timeout=20000)

        # 2. Create a project with context.
        await page.click("button:has-text('New Project')")
        await page.fill(
            "input[placeholder='e.g. Campus LAN Refresh']", "Campus Wi-Fi Refresh"
        )
        await page.fill("input[placeholder='e.g. Acme Corp']", "Northwind University")
        await page.fill(
            "textarea[placeholder='Brief summary of the project goals…']",
            "Replace 220 aging Wi-Fi 5 access points across 4 academic buildings with "
            "Wi-Fi 6E, cloud-managed, with strong assurance/AIOps tooling.",
        )
        await page.fill(
            "textarea[placeholder='Describe the current network environment…']",
            "220 legacy 802.11ac access points on an on-prem wireless controller.",
        )
        await page.fill("input[placeholder='e.g. 250000']", "400000")
        await page.click("button:has-text('Create Project')")

        # 3. Open the project, then its Advisor.
        await page.wait_for_selector("text=Campus Wi-Fi Refresh", timeout=15000)
        await page.click("text=Campus Wi-Fi Refresh")
        await page.wait_for_url("**/projects/**", timeout=15000)
        project_id = page.url.split("/projects/")[1].split("/")[0]
        await page.screenshot(path=str(OUT / "nemotron-dashboard.png"))

        await page.goto(
            f"{BASE}/projects/{project_id}/advisor", wait_until="networkidle"
        )
        await page.screenshot(path=str(OUT / "nemotron-advisor-empty.png"))

        # 4. Ask the Advisor (Nemotron) and wait for the streamed answer.
        await page.fill("textarea[aria-label='Message input']", QUESTION)
        await page.click("button[aria-label='Send message']")
        try:
            await page.wait_for_selector("text=Advisor is responding…", timeout=15000)
        except Exception:
            pass  # model may have answered faster than we polled
        try:
            await page.wait_for_selector(
                "text=Advisor is responding…", state="detached", timeout=180000
            )
        except Exception:
            pass
        await page.wait_for_selector(".advisor-md", timeout=10000)
        await asyncio.sleep(1.5)

        await page.screenshot(path=str(OUT / "nemotron-advisor.png"), full_page=True)

        # Hero crop: scroll the conversation to the TOP so the user's question +
        # the start of Nemotron's answer + the NetPlanner chrome are all in frame.
        # Find the scrollable ancestor of the first message rather than guessing a
        # class (the textarea is also overflow-y-auto).
        await page.evaluate(
            """() => {
                const el = document.querySelector('.advisor-md');
                if (!el) return;
                let p = el.parentElement;
                while (p && p.scrollHeight <= p.clientHeight) p = p.parentElement;
                if (p) p.scrollTop = 0;
            }"""
        )
        await asyncio.sleep(0.8)
        await page.screenshot(path=str(OUT / "nemotron-advisor-hero.png"))

        answer = await page.inner_text(".advisor-md")
        print(f"OK — answer chars: {len(answer)}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
