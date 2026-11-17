import { getSources, settle } from "../../lib/engine";
import { day, num } from "../../lib/format";

export const dynamic = "force-dynamic";
export const metadata = { title: "Data sources · 25x125" };

export default async function SourcesPage() {
  const r = await settle(getSources());
  if (!r.ok)
    return (
      <main className="wrap">
        <p className="err">Could not load the source list: {r.error}</p>
      </main>
    );
  const { sources, attribution, not_used, label } = r.value;
  const loaded = sources.filter((s) => s.last_pulled).length;
  return (
    <main className="wrap">
      <section className="head">
        <div>
          <h1>Data sources</h1>
          <span className="muted">
            {sources.length} public datasets; {loaded} have a copy date in this database. {label}
          </span>
        </div>
      </section>

      <section className="card">
        <h2>Datasets</h2>
        <p className="sub">Screens read our nightly copy, never the portals. &quot;Last copied&quot; is the date of the newest finished pull.</p>
        <div className="scroll">
          <table className="t" data-testid="sources">
            <thead>
              <tr>
                <th>Dataset</th>
                <th>Publisher</th>
                <th>Used for</th>
                <th>Refresh</th>
                <th>Last copied</th>
                <th className="num">Rows</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => (
                <tr key={s.name}>
                  <td>
                    <a href={s.url} target="_blank" rel="noreferrer">
                      {s.name}
                    </a>
                    <div className="basis mono">{s.id}</div>
                  </td>
                  <td>{s.publisher}</td>
                  <td>
                    {s.used_for}
                    {s.display !== "shown with its source and date" && <div className="basis">{s.display}</div>}
                  </td>
                  <td>{s.refresh}</td>
                  <td>{s.last_pulled ? day(s.last_pulled) : "n/a"}</td>
                  <td className="num">{s.rows !== null ? num(s.rows) : "n/a"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2>Attribution</h2>
        <dl className="qa">
          {attribution.map((a) => (
            <div key={a.name}>
              <dt>
                <a href={a.url} target="_blank" rel="noreferrer">
                  {a.name}
                </a>
              </dt>
              <dd>
                {a.text} <span className="muted">Terms checked {day(a.verified_on)}.</span>
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="card">
        <h2>Not used</h2>
        <ul style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 6 }}>
          {not_used.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      </section>
    </main>
  );
}
