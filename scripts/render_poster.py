"""Render the 48 x 36 in poster to PDF (print and Canva import) and a preview PNG.

Needs the dashboard dev server: pnpm --dir dashboard dev --port 3123
Usage: python scripts/render_poster.py poster/ [--phone]
--phone first replays one /drive round and saves the phone screenshot the poster embeds.
Prints the smallest text size in points and any region whose content overflows.
"""
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

BASE = "http://localhost:3123"
REPO = Path(__file__).resolve().parents[1]
HIDE_DEV = "nextjs-portal{display:none!important}"

async def phone_shot(b):
    ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
    pg = await ctx.new_page()
    await pg.goto(f"{BASE}/drive", wait_until="networkidle")
    await pg.add_style_tag(content=HIDE_DEV)
    # The top-down view exposes the pedestrian as SVG, so it times the brake; the poster shows the 3D result.
    await pg.get_by_role("radio", name="Top-down").click()
    await pg.get_by_role("button", name="Start").click()
    await pg.wait_for_function("document.querySelectorAll('svg ellipse').length >= 3", timeout=10000)
    await pg.wait_for_timeout(200)
    box = await pg.get_by_role("button", name="Brake").bounding_box()
    await pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    await pg.mouse.down()
    await pg.wait_for_selector("text=Try again", timeout=10000)
    await pg.mouse.up()
    await pg.get_by_role("radio", name="3D street").click()
    await pg.wait_for_timeout(2000)
    await pg.evaluate("window.scrollTo(0,0)")
    await pg.screenshot(path=f"{REPO}/dashboard/public/poster/drive-phone.png")
    await ctx.close()

AUDIT = """() => {
  let minPt = 1e9, smallest = [];
  for (const el of document.querySelectorAll('main p, main h1, main h2, main h3, main text, main tspan, main span, main figcaption, main sup')) {
    const ownText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!ownText) continue;
    const fs = parseFloat(getComputedStyle(el).fontSize);
    let scale = 1;
    const svg = el.closest('svg');
    if (svg && svg.viewBox.baseVal && svg.viewBox.baseVal.width) scale = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
    const pt = Math.round(fs * scale * 0.75 * 10) / 10;
    if (pt < minPt) { minPt = pt; smallest = []; }
    if (pt === minPt) smallest.push(el.textContent.trim().slice(0, 30));
  }
  const overflow = [];
  for (const region of document.querySelectorAll('main > div')) {
    const r = region.getBoundingClientRect();
    for (const child of region.querySelectorAll('*:not(svg *)')) {
      const c = child.getBoundingClientRect();
      if (c.width && (c.bottom > r.bottom + 1 || c.right > r.right + 1)) { overflow.push((region.querySelector('h2,h1')||{}).textContent + ' <- ' + child.tagName + ' ' + Math.round(c.bottom - r.bottom)); break; }
    }
  }
  return { minPt, smallest: smallest.slice(0, 5), overflow };
}"""

async def poster(b, out):
    ctx = await b.new_context(viewport={"width": 4608, "height": 3456})
    pg = await ctx.new_page()
    await pg.goto(f"{BASE}/poster", wait_until="networkidle")
    await pg.add_style_tag(content=HIDE_DEV)
    await pg.evaluate("document.fonts.ready")
    audit = await pg.evaluate(AUDIT)
    print("min text pt:", audit["minPt"], audit["smallest"])
    print("overflowing regions:", audit["overflow"])
    await pg.screenshot(path=f"{out}/poster-preview.png")
    await pg.pdf(path=f"{out}/poster.pdf", width="48in", height="36in", print_background=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
    await ctx.close()

async def main():
    out = sys.argv[1]
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        if "--phone" in sys.argv:
            await phone_shot(b)
        await poster(b, out)
        await b.close()
asyncio.run(main())
