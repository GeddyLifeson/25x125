"""Load report: rows per table, the latest pull of each source, and failed pulls in the last 7 days.

Run: python -m jobs.report
"""

from core.db import connect

TABLES = ["parcel", "parcel_shape", "parcel_site", "parcel_address", "sale", "permit", "building_char",
          "condo_char", "zoning_district_area", "overlay", "transit_station", "parcel_signal"]  # fmt: skip


def run(url: str | None = None) -> dict:
    with connect(url) as conn:
        counts = {t: conn.execute(f"select count(*) from {t}").fetchone()[0] for t in TABLES}
        latest = conn.execute(
            "select distinct on (dataset_id) dataset_id, host, status, row_count, finished_at"
            " from source_pull order by dataset_id, started_at desc"
        ).fetchall()
        failed = conn.execute(
            "select dataset_id, started_at, note from source_pull"
            " where status = 'failed' and started_at > now() - interval '7 days' order by started_at desc"
        ).fetchall()
    return {"counts": counts, "latest": latest, "failed": failed}


def main() -> None:
    r = run()
    print("Rows per table")
    for t, n in r["counts"].items():
        print(f"  {t:<22} {n:>10,}")
    print("Latest pull per source")
    for ds, host, status, n, done in r["latest"]:
        when = done.strftime("%Y-%m-%d %H:%M") if done else "-"
        print(f"  {ds:<24} {status:<8} {n or 0:>10,}  {when}  {host}")
    print(f"Failed pulls, last 7 days: {len(r['failed'])}")
    for ds, started, note in r["failed"]:
        print(f"  {ds} {started:%Y-%m-%d %H:%M} {note[:100]}")


if __name__ == "__main__":
    main()
