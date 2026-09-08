"""Exporta o símbolo SVG local para os tamanhos exigidos pelo manifesto PWA."""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "static/icons"
svg = (ICONS / "icon.svg").read_text(encoding="utf-8")
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    for name, size, maskable in [
        ("icon-192.png", 192, False),
        ("icon-512.png", 512, False),
        ("maskable-512.png", 512, True),
    ]:
        page = browser.new_page(
            viewport={"width": size, "height": size}, device_scale_factor=1
        )
        scale = "70%" if maskable else "100%"
        page.set_content(
            f"<style>body{{margin:0;background:#0f52ba;height:100vh;display:grid;place-items:center}}svg{{width:{scale};height:{scale}}}</style>{svg}"
        )
        page.screenshot(path=str(ICONS / name))
        page.close()
    browser.close()
