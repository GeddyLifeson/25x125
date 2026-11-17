import Link from "next/link";
import { SAMPLE_ADDRESS, SAMPLE_PIN } from "../../lib/sample";

export const metadata = { title: "Help · 25x125" };

const STEPS: { title: string; text: string; href: string; link: string }[] = [
  {
    title: "1. Find a lot",
    text: "Type an address or PIN, or pick a community area and filter the list: zoning, minimum units by right, vacant land, city lots for sale, lots in the next county tax sale. The list and the map show the same lots.",
    href: "/",
    link: "Open search",
  },
  {
    title: "2. Read the parcel page",
    text: "Zoning and what each approval path allows, the lot's size, what stands on it, nearby new-construction sales, violations and 311 reports, overlays, incentives that may apply, and a list to check before buying.",
    href: `/parcels/${SAMPLE_PIN}`,
    link: `Open ${SAMPLE_ADDRESS}`,
  },
  {
    title: "3. Run feasibility",
    text: "Up to three building scenarios, each for sale or for hold. Costs show in dollars with a dollar range. Change any assumption: land price, cost per square foot, unit size, sale price, rent, loan terms. Switch off incentives that don't fit your deal.",
    href: `/parcels/${SAMPLE_PIN}/feasibility`,
    link: "Run the sample",
  },
  {
    title: "4. Save and export",
    text: "Save the lot as a deal, track its stage and your owner contacts, and export a one-page PDF or a CSV for a partner or lender.",
    href: "/deals",
    link: "Open deals",
  },
];

const QA: { q: string; a: string }[] = [
  {
    q: "Where do the numbers come from?",
    a: "Public records from the City of Chicago, Cook County, the Census Bureau and FHFA, copied into our database each night. The small \"source\" mark beside a number shows its dataset and the date it was pulled. The Data sources page lists every dataset.",
  },
  {
    q: "What is the development score?",
    a: "A 0 to 100 sorting aid: zoning upside, by-right profit, acquisition signals, location and incentives, less penalties. Each lot shows its points by part. It does not rate investment quality.",
  },
  {
    q: "Why does a cost show a range?",
    a: "The range depends on the estimate stage and on how much local data sits behind the number. Thin data widens it, and the screen says so. Your own job costs can replace the defaults on any deal.",
  },
  {
    q: "What does \"by right\" mean here?",
    a: "What the zoning district allows with a standard permit and no zoning relief. Other paths (administrative adjustment, an added ADU, rezoning) are listed with the approval each needs.",
  },
  {
    q: "A lot is flagged for the county tax sale. Can I buy it there?",
    a: "A tax buyer at the Annual Tax Sale buys a lien on unpaid taxes, not the deed. The owner can pay before the sale and can redeem afterward. The flag is a sign the owner may want to sell; confirm any balance with the Cook County Treasurer.",
  },
  {
    q: "Is this advice?",
    a: "No. Results are estimates, not tax, legal, zoning or appraisal advice. The app shows the math and its sources; it does not recommend what to build or buy. An Illinois-licensed architect must stamp drawings for buildings of 3 or more units.",
  },
  {
    q: "A number looks wrong. What do I do?",
    a: "Use \"Report an error\" on the parcel page or Feedback in the top bar. Say what you expected and where you saw it. Reports go to the team with the page and the numbers attached.",
  },
];

export default function HelpPage() {
  return (
    <main className="wrap" style={{ maxWidth: 960 }}>
      <section className="head">
        <div>
          <h1>How to use 25x125</h1>
          <span className="muted">Four steps from an address to a one-page deal summary. Chicago only for now.</span>
        </div>
        <div className="btns">
          <Link className="btn primary" href={`/parcels/${SAMPLE_PIN}`}>
            Try the sample lot
          </Link>
        </div>
      </section>

      <section className="steps" aria-label="Steps">
        {STEPS.map((s) => (
          <div key={s.title} className="card">
            <h2>{s.title}</h2>
            <p className="sub" style={{ marginBottom: 10 }}>
              {s.text}
            </p>
            <Link href={s.href}>{s.link}</Link>
          </div>
        ))}
      </section>

      <section className="card">
        <h2>Questions</h2>
        <dl className="qa">
          {QA.map((x) => (
            <div key={x.q}>
              <dt>{x.q}</dt>
              <dd>{x.a}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="card">
        <h2>More</h2>
        <ul className="plain">
          <li>
            <Link href="/sources">Data sources and attribution</Link>
            <span className="muted">Every dataset, its publisher and the last copy date</span>
          </li>
          <li>
            <Link href="/areas">Community areas</Link>
            <span className="muted">New-construction sales, cost index and land value for each of the 77 areas</span>
          </li>
          <li>
            <Link href="/feedback">Feedback</Link>
            <span className="muted">Report an error or ask for something missing</span>
          </li>
        </ul>
      </section>
    </main>
  );
}
