// Smoke check of the search, parcel, feasibility, map and deals screens in Chromium.
// Run with the engine and the web app up: node scripts/smoke.cjs [base url], default http://localhost:3010
// Needs the playwright package and a Chromium it can launch, and the tile server (docker compose up -d);
// screenshots go to web/screenshots/. Deals the run creates are deleted at the end.
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");

const BASE = process.argv[2] || process.env.WEB_URL || "http://localhost:3010";
const OUT = path.join(__dirname, "..", "screenshots");
const PIN = "16121020310000"; // 624 N Troy St, Humboldt Park, vacant RT-4 lot

let failures = 0;
const dealIds = [];
function check(ok, what) {
  console.log(`${ok ? "ok  " : "FAIL"} ${what}`);
  if (!ok) failures++;
}

async function settled(page) {
  await page.waitForFunction(() => !document.querySelector("[role=status]")?.textContent?.includes("Recalculating"));
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

  await page.goto(`${BASE}/`);
  await page.fill("input[name=q]", "1500 N");
  await page.click("button[type=submit]");
  await page.waitForSelector("table.hits");
  const hits = await page.locator("table.hits tbody tr").count();
  check(hits > 1, `search "1500 N" lists ${hits} parcels`);
  await page.screenshot({ path: path.join(OUT, "search.png") });

  await page.goto(`${BASE}/?q=624 N Troy St`);
  await page.waitForURL(`**/parcels/${PIN}`);
  check(true, "search for one address opens the parcel page");
  await page.waitForSelector("text=What zoning allows");
  check((await page.locator("h1").textContent()).includes("624 N Troy St"), "parcel page shows the address");
  check((await page.locator(".fact").count()) === 8, "parcel page has 8 key facts");
  check((await page.locator("details.src").count()) > 15, "numbers carry source disclosures");
  await page.screenshot({ path: path.join(OUT, "parcel.png"), fullPage: true });

  await page.click("text=Run feasibility");
  await page.waitForURL(`**/parcels/${PIN}/feasibility*`);
  await page.waitForSelector(".sc");
  check((await page.locator(".sc").count()) === 3, "feasibility shows scenarios A, B and C");
  const total = await page.locator("tr.total td.num").textContent();
  check(/\$[\d,]+ \(-\$[\d,]+ \/ \+\$[\d,]+\)/.test(total), `total cost in dollars with dollar margins: ${total}`);
  check((await page.locator("text=reference lines, not a verdict").count()) > 0, "reference lines are labeled");
  check((await page.locator("text=Estimates, not tax, legal, zoning or appraisal advice").count()) > 0, "estimate label shown");
  await page.screenshot({ path: path.join(OUT, "feasibility-sell.png"), fullPage: true });

  // Edit land for all scenarios and recalculate.
  await page.click("button:has-text('All scenarios')");
  const land = page.locator("label:has-text('Land price') input");
  await land.fill("60000");
  await page.click("button:has-text('Recalculate')");
  await settled(page);
  const landCell = await page.locator("table.t tbody tr").first().locator("td.num").first().textContent();
  check(landCell.trim() === "$60,000", `land override applied: ${landCell}`);

  // Turn the Enterprise Zone incentive off.
  const ez = page.locator("label.inc:has-text('Enterprise Zone') input");
  const wasOn = await ez.isChecked();
  await ez.click();
  await settled(page);
  check((await ez.isChecked()) !== wasOn, "incentive toggle re-posts and flips");

  // Import an overrides file.
  const csv = path.join(OUT, "..", "scripts", "sample-overrides.csv");
  await page.setInputFiles("[data-testid=import]", csv);
  await settled(page);
  check((await page.locator("text=Imported").count()) > 0, "overrides CSV imported");

  // Hold.
  await page.click("button:has-text('Build and hold')");
  await settled(page);
  check((await page.locator("text=Loan at 1.3 DSCR").count()) > 0, "hold block shows the DSCR loan");
  await page.screenshot({ path: path.join(OUT, "feasibility-hold.png"), fullPage: true });

  // PDF and CSV links answer.
  const pdfHref = await page.locator("a:has-text('One-page PDF')").getAttribute("href");
  const pdf = await page.request.get(`${BASE}${pdfHref}`);
  check(pdf.ok() && pdf.headers()["content-type"] === "application/pdf", `PDF link returns a PDF (${(await pdf.body()).length} bytes)`);
  const csvHref = await page.locator("a:has-text('Lines as CSV')").getAttribute("href");
  const lines = await (await page.request.get(`${BASE}${csvHref}`)).text();
  check(lines.includes("Total cost") && lines.includes("$60,000") === false && lines.includes(",60000,"), "CSV export has the lines and the edited land");

  // Save the scenario on screen as a deal.
  await page.click("[data-testid=save-deal]");
  await page.waitForSelector("text=Saved as deal");
  const savedText = await page.locator("text=Saved as deal").textContent();
  const dealId = Number(savedText.match(/deal (\d+)/)[1]);
  dealIds.push(dealId);
  check(dealId > 0, `feasibility saved as deal ${dealId}`);
  const saved = await (await page.request.get(`${BASE}/api/deals/${dealId}`)).json();
  check(saved.exit === "hold" && saved.overrides.all && saved.overrides.all.land === 60000 && saved.result && saved.result.run_on,
    `deal keeps the edits (land ${saved.overrides.all && saved.overrides.all.land}), exit ${saved.exit} and a dated run (${saved.result && saved.result.run_on})`);

  // Phone width.
  const phone = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await phone.goto(`${BASE}/parcels/${PIN}/feasibility`);
  await phone.waitForSelector(".sc");
  const overflow = await phone.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  check(overflow <= 1, `no sideways scroll at phone width (overflow ${overflow}px)`);
  await phone.screenshot({ path: path.join(OUT, "feasibility-phone.png") });

  try {
    await mapChecks(browser);
    await dealChecks(browser);
  } catch (e) {
    check(false, `map or deals check stopped: ${e.message.split("\n")[0]}`);
  }

  // Remove the deals this run made, so the smoke test leaves the database as it found it.
  for (const id of dealIds) await page.request.delete(`${BASE}/api/deals/${id}`);
  await browser.close();
  console.log(failures ? `${failures} check(s) failed` : "all checks passed");
  process.exit(failures ? 1 : 0);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});

async function mapIdleAfter(page, t) {
  await page.waitForFunction((t) => Number(document.body.dataset.mapIdle || 0) > t, t, { timeout: 15000 });
}

async function mapChecks(browser) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const tiles = { lots: 0, land_value: 0, lots_for_sale: 0, bad: 0 };
  page.on("response", (r) => {
    const m = r.url().match(/\/tiles\/(\w+)\//);
    if (!m) return;
    if (r.status() === 200 || r.status() === 204) tiles[m[1]]++;
    else tiles.bad++;
  });
  let t = Date.now();
  await page.goto(`${BASE}/map?community_area=23`);
  await page.waitForSelector("[data-testid=results] li");
  await mapIdleAfter(page, t);
  const first = Date.now() - t;
  const rows = await page.locator("[data-testid=results] li").count();
  check(rows > 0, `map and list open for Humboldt Park with ${rows} lots in ${first} ms`);
  check((await page.locator("[data-testid=results] li .rpts").first().textContent()).includes("Zoning"), "each lot shows its points by part");
  check(tiles.lots > 0 && tiles.bad === 0, `lot tiles load (${tiles.lots} tiles, ${tiles.bad} errors)`);
  check((await page.locator(".maplibregl-ctrl-attrib").textContent()).includes("Cook County Assessor"), "map carries data attribution");
  check((await page.locator("text=it does not rate investment quality").count()) > 0, "score is labeled a sorting aid");
  await page.screenshot({ path: path.join(OUT, "map.png") });

  // Filter: min score 50. List and map must both settle in under 2 seconds.
  t = Date.now();
  await page.fill("[data-testid=min-score]", "50");
  await page.waitForFunction(() => {
    const s = [...document.querySelectorAll("[data-testid=results] li .rscore")].map((e) => Number(e.textContent));
    return s.length > 0 && s.every((v) => v >= 50);
  });
  const listMs = Date.now() - t;
  await mapIdleAfter(page, t);
  const mapMs = Date.now() - t;
  check(listMs < 2000 && mapMs < 2000, `min score 50: list updated in ${listMs} ms, map in ${mapMs} ms (target under 2,000)`);
  check(page.url().includes("min_score=50"), "filters are kept in the address bar");

  // Chip filter: vacant land only.
  t = Date.now();
  await page.click("button.chip:has-text('Vacant land')");
  await page.waitForFunction(() => {
    const li = [...document.querySelectorAll("[data-testid=results] li")];
    return location.search.includes("vacant=true") && li.length > 0 && li.every((e) => e.textContent.includes("Vacant land"));
  });
  check(true, `vacant-land chip filters the list (${Date.now() - t} ms)`);
  await page.click("button.chip:has-text('Vacant land')");

  // Sort by lot size.
  await page.selectOption("[data-testid=sort]", "lot");
  await page.waitForFunction(() => location.search.includes("sort=lot"));
  await page.waitForSelector("[data-testid=results] li");
  check(true, "sort by lot size reloads the list");
  await page.selectOption("[data-testid=sort]", "score");

  // CSV export of the list.
  const csvHref = await page.locator("[data-testid=csv]").getAttribute("href");
  const csv = await (await page.request.get(`${BASE}${csvHref}`)).text();
  const csvRows = csv.trim().split("\n");
  check(csvRows[0].startsWith("pin10,pin,address") && csvRows.length > 1 && csvHref.includes("min_score=50"),
    `list CSV has the filtered rows (${csvRows.length - 1} rows)`);

  // Pick a lot from the list: side panel with the points breakdown and links.
  await page.click("[data-testid=results] li button.rrow");
  await page.waitForSelector("[data-testid=panel]");
  const panel = page.locator("[data-testid=panel]");
  check((await panel.locator("table.pts tr").count()) === 6, "side panel shows the six score parts");
  check((await panel.locator("a:has-text('Run feasibility')").count()) === 1 && (await panel.locator("a:has-text('Parcel page')").count()) === 1,
    "side panel links to the parcel page and feasibility");
  await mapIdleAfter(page, Date.now() - 50);
  await page.screenshot({ path: path.join(OUT, "map-panel.png") });

  // Click a lot on the map itself (zoomed in after the pick): the panel opens for that lot.
  await panel.locator("button.x").click();
  let tc = Date.now();
  await page.fill("[data-testid=min-score]", "");
  await mapIdleAfter(page, tc);
  const box = await page.locator("[data-testid=map]").boundingBox();
  let opened = false;
  for (const [dx, dy] of [[60, 0], [0, 60], [-60, 0], [0, -60], [90, 90], [-90, -90], [120, 0]]) {
    await page.mouse.click(box.x + box.width / 2 + dx, box.y + box.height / 2 + dy);
    try {
      await page.waitForSelector("[data-testid=panel]", { timeout: 1500 });
      opened = true;
      break;
    } catch {
      // a street, not a lot: try the next spot
    }
  }
  check(opened, "clicking a lot on the map opens its panel");

  // Layers: fast path, land value, lots for sale.
  await page.click("[data-testid=layer-fast]");
  await page.click("[data-testid=layer-land]");
  await page.click("[data-testid=layer-sale]");
  t = Date.now();
  await page.waitForTimeout(300);
  await mapIdleAfter(page, t);
  check(tiles.land_value > 0 && tiles.lots_for_sale > 0 && tiles.bad === 0,
    `layers load: land value ${tiles.land_value} tiles, lots for sale ${tiles.lots_for_sale} tiles`);
  check((await page.locator("text=City (ChiBlockBuilder)").count()) > 0 && (await page.locator("text=Paler where fewer than 5 sales").count()) > 0,
    "layer legends for land value and public lots for sale");
  await page.screenshot({ path: path.join(OUT, "map-layers.png") });

  // Zoom out to the area to see land values and lots for sale together.
  await page.selectOption("[data-testid=area]", "");
  await page.selectOption("[data-testid=area]", "23");
  await mapIdleAfter(page, Date.now());
  await page.screenshot({ path: path.join(OUT, "map-layers-area.png") });
  await page.close();
}

async function dealChecks(browser) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto(`${BASE}/deals?d=${dealIds[0]}`);
  await page.waitForSelector("[data-testid=deal-table]");
  const allCount = Number(await page.locator("[data-testid=stage-all] .v").textContent());
  check(allCount >= 1, `deals screen lists ${allCount} deal(s)`);
  const row = page.locator("[data-testid=deal-table] tbody tr.sel");
  check((await row.count()) === 1, "the saved deal is picked");
  const profit = await row.locator("td.num").first().textContent();
  check(/\$|NOI/.test(profit), `deal row shows the saved numbers (${profit.replace("source", "").trim()})`);

  const before = Number(await page.locator("[data-testid=stage-contacted] .v").textContent());
  await row.locator("select[aria-label='Change status']").selectOption("contacted");
  await page.waitForFunction((b) => Number(document.querySelector("[data-testid=stage-contacted] .v").textContent) === b + 1, before);
  check(true, "changing the status moves the pipeline count");

  await page.selectOption("[data-testid=log-kind]", "call");
  await page.fill("[data-testid=log-note]", "Owner interested; wants comps before naming a price");
  await page.click("button:has-text('Log contact')");
  await page.waitForSelector("[data-testid=log] li:has-text('wants comps')");
  check(true, "contact logged in the outreach log");
  check((await page.locator("text=Calls and texts follow TCPA rules; email follows CAN-SPAM.").count()) === 1, "TCPA and CAN-SPAM note shown");

  const csv = await (await page.request.get(`${BASE}/api/deals?format=csv`)).text();
  check(csv.startsWith("id,pin,pin10,address") && csv.includes(PIN), "deals CSV export has the deal");
  const log = await (await page.request.get(`${BASE}/api/deals/events?format=csv`)).text();
  check(log.includes("wants comps"), "outreach log CSV export has the contact");

  // Import: one new lead from a CSV file.
  const file = path.join(OUT, "smoke-deals-import.csv");
  fs.writeFileSync(file, "pin,stage,next_step,notes\n16-12-102-031-0000,Lead,Find owner contact,smoke import\n");
  await page.setInputFiles("[data-testid=deal-import]", file);
  await page.waitForSelector("text=1 new, 0 updated");
  const after = await (await page.request.get(`${BASE}/api/deals`)).json();
  const imported = after.filter((d) => d.notes === "smoke import");
  for (const d of imported) dealIds.push(d.id);
  check(imported.length === 1, "deals CSV import adds the row");
  await page.screenshot({ path: path.join(OUT, "deals.png"), fullPage: true });

  // Open the deal's feasibility: its saved edits come back.
  await page.goto(`${BASE}/parcels/${PIN}/feasibility?deal=${dealIds[0]}`);
  await page.waitForSelector(".sc");
  check((await page.locator(`text=Loaded the edits saved with deal ${dealIds[0]}`).count()) === 1, "feasibility opens with the deal's saved edits");
  check((await page.locator("[data-testid=update-deal]").count()) === 1, "feasibility offers to update the deal");
  await page.close();

  // Phone width: map and deals.
  const phone = await browser.newPage({ viewport: { width: 390, height: 844 } });
  for (const [url, sel, shot] of [["/map?community_area=23", "[data-testid=results] li", "map-phone.png"], ["/deals", "[data-testid=deal-table]", "deals-phone.png"]]) {
    await phone.goto(`${BASE}${url}`);
    await phone.waitForSelector(sel);
    const overflow = await phone.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    check(overflow <= 1, `${url}: no sideways scroll at phone width (overflow ${overflow}px)`);
    await phone.screenshot({ path: path.join(OUT, shot) });
  }
  await phone.close();
}
