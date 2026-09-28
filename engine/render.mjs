// render.mjs <page.html> <frames-dir> [scale] [still.png]
// Draws every frame of a built motion page with its render hook, in headless
// Chromium, and writes them as numbered PNGs at the wallpaper's size times
// `scale` (1, the full size, unless the motion sets render_scale); `themotion
// finish` scales them to the pattern's size. Given a fourth path, it also
// writes the still drawn the same way, for comparing frames against it.
import { chromium } from "playwright-core"
import { execFileSync } from "node:child_process"
import fs from "node:fs"

const [page, out, scale = "1", stillOut] = process.argv.slice(2)
fs.rmSync(out, { recursive: true, force: true })
fs.mkdirSync(out, { recursive: true })

function findChromium() {
  if (process.env.THEMOTION_CHROMIUM) return process.env.THEMOTION_CHROMIUM
  for (const name of ["chromium", "google-chrome-stable", "google-chrome", "chromium-browser"]) {
    try { return execFileSync("which", [name], { encoding: "utf8" }).trim() } catch {}
  }
  return undefined // playwright's own download, if installed
}

const browser = await chromium.launch({ executablePath: findChromium(), args: ["--force-color-profile=srgb"] })
const tab = await browser.newPage()
const errors = []
tab.on("pageerror", e => errors.push(e.message))
await tab.goto("file://" + fs.realpathSync(page) + "?render&scale=" + scale)
await tab.waitForFunction(() => window.__themotion || document.querySelector(".error"), null, { timeout: 60000 })
if (errors.length || !(await tab.evaluate(() => !!window.__themotion))) {
  console.error("the scene failed to load:", errors.join("; "))
  process.exit(1)
}
const { length, fps } = await tab.evaluate(() => window.__themotion)
const frames = Math.round(length * fps)
for (let i = 0; i < frames; i++) {
  const png = await tab.evaluate(t => { window.__themotion.render(t); return document.getElementById("cv").toDataURL("image/png") }, i / fps)
  fs.writeFileSync(`${out}/${String(i).padStart(4, "0")}.png`, Buffer.from(png.split(",")[1], "base64"))
}
if (stillOut) {
  const png = await tab.evaluate(() => { window.__themotion.still(); return document.getElementById("cv").toDataURL("image/png") })
  fs.writeFileSync(stillOut, Buffer.from(png.split(",")[1], "base64"))
}
await browser.close()
if (errors.length) { console.error("errors while rendering:", errors.join("; ")); process.exit(1) }
console.log(`rendered ${frames} frames`)
