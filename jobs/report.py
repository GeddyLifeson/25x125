"""Load report: rows per table, the latest pull of each source, and failed pulls in the last 7 days.

Run: python -m jobs.report
"""

from core.db import connect

TABLES = ["parcel", "parcel_shape", "parcel_site", "parcel_address", "sale", "permit", "building_char",
          "condo_char", "zoning_district_area", "overlay", "transit_station", "parcel_signal", "boundary", "street_segment", "lot_use", "comp", "hpi", "cost_index", "permit_wait", "land_sale", "land_value", "acs_rent", "zori_growth", "rule",
          "parcel_proximity", "assessor_permit", "exempt_parcel", "building_footprint", "cost_escalation_index", "lot_for_sale", "rezoning", "assessed_value", "older_sale", "tax_sale_list"]  # fmt: skip


DROP_SHARE = 0.10  # TASKS.md, SaaS setup: alert on a count drop over 10%


def count_drops(conn, share: float = DROP_SHARE) -> list[dict]:
    """Sources whose newest finished pull has over 10% fewer rows than the pull before it with the same query.

    Pulls that load only new rows (sales, permits) carry their start date in the query, so they never pair up
    and are not compared. A source that returns far fewer rows usually means the portal changed or cut off."""
    rows = conn.execute(
        """select host, dataset_id, row_count, prev, finished_at from (
             select host, dataset_id, row_count, finished_at,
                    lag(row_count) over w as prev, row_number() over (partition by host, dataset_id, query
                                                                      order by finished_at desc) as n
             from source_pull where status = 'ok' and finished_at is not null and row_count is not null
             window w as (partition by host, dataset_id, query order by finished_at)
           ) x where n = 1 and prev > 0 and row_count < prev * (1 - %s::numeric) order by host, dataset_id""",
        (share,),
    ).fetchall()
    return [{"host": h, "dataset_id": ds, "rows": n, "previous_rows": prev, "finished_at": at.isoformat(),
             "drop": round(1 - n / prev, 3)} for h, ds, n, prev, at in rows]  # fmt: skip


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
        drops = count_drops(conn)
    return {"counts": counts, "latest": latest, "failed": failed, "drops": drops}


def main() -> dict:
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
    print(f"Row counts down over {DROP_SHARE:.0%} from the pull before: {len(r['drops'])}")
    for d in r["drops"]:
        print(
            f"  {d['dataset_id']} {d['previous_rows']:,} -> {d['rows']:,} ({d['drop']:.0%} fewer)  {d['host']}"
        )
    return r


if __name__ == "__main__":
    main()
