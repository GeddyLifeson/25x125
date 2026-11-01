// Smoke check of the parcel and feasibility screens in Chromium.
// Run with the engine and the web app up: node scripts/smoke.cjs [base url], default http://localhost:3010
// Needs the playwright package and a Chromium it can launch; screenshots go to web/screenshots/.
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");

const BASE = process.argv[2] || process.env.WEB_URL || "http://localhost:3010";
const OUT = path.join(__dirname, "..", "screenshots");
const PIN = "16121020310000"; // 624 N Troy St, Humboldt Park, vacant RT-4 lot

let failures = 0;
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

  // Phone width.
  const phone = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await phone.goto(`${BASE}/parcels/${PIN}/feasibility`);
  await phone.waitForSelector(".sc");
  const overflow = await phone.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  check(overflow <= 1, `no sideways scroll at phone width (overflow ${overflow}px)`);
  await phone.screenshot({ path: path.join(OUT, "feasibility-phone.png") });

  await browser.close();
  console.log(failures ? `${failures} check(s) failed` : "all checks passed");
  process.exit(failures ? 1 : 0);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
