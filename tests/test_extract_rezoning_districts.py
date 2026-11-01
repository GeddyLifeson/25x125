import csv
import io
import json

import psycopg
from pypdf import PdfReader, PdfWriter

from db.migrate import migrate
from jobs import extract_rezoning_districts as x


def test_clean_district_restores_hyphens_and_pd_numbers():
    assert x.clean_district("rt4") == "RT-4"
    assert x.clean_district("RS 3") == "RS-3"
    assert x.clean_district("RM-4.5") == "RM-4.5"
    assert x.clean_district("B3 2") == "B3-2"
    assert x.clean_district("C1-1") == "C1-1"
    assert x.clean_district("DX-12") == "DX-12"
    assert x.clean_district("PD1234") == "PD 1234"
    assert x.clean_district("Residential-Business Planned Development No. 1458") == "PD 1458"
    assert x.clean_district("PD") == "PD"
    assert x.clean_district("") is None


def test_pick_ordinance_prefers_legislation_attachment():
    atts = [
        {"fileName": "ZLB.pdf", "path": "https://x/a.pdf", "attachmentType": "Committee Letter"},
        {"fileName": "O2026-1 Ordinance.pdf", "path": "https://x/b.pdf", "attachmentType": "Legislation"},
        {"fileName": "O2026-1 Application.pdf", "path": "https://x/c.pdf", "attachmentType": "Miscellaneous"},
    ]
    assert x.pick_ordinance(atts)["path"] == "https://x/b.pdf"
    assert (
        x.pick_ordinance([{"fileName": "Ordinance.pdf", "path": "https://x/d.pdf"}])["path"]
        == "https://x/d.pdf"
    )
    assert x.pick_ordinance(atts[:1]) is None


def test_first_pages_trims_long_scans(tmp_path):
    w = PdfWriter()
    for _ in range(5):
        w.add_blank_page(612, 792)
    path = tmp_path / "o.pdf"
    with path.open("wb") as f:
        w.write(f)
    assert len(PdfReader(io.BytesIO(x.first_pages(path))).pages) == x.PAGES


def test_request_uses_small_model_and_json_schema():
    p = x.request_params(("pdf", b"%PDF-1.4"))
    assert p["model"] == x.MODEL
    assert p["output_config"]["format"]["schema"]["required"][0] == "changes"
    assert p["messages"][0]["content"][0]["type"] == "document"
    json.dumps(p)


def test_guess_tokens_counts_at_most_two_pages():
    assert x.guess_tokens({"pages": "9"}, ("pdf", b"")) == 2 * x.TOKENS_PER_PAGE + x.PROMPT_TOKENS
    assert x.guess_tokens({"pages": "40"}, ("text", "a" * 3500)) == 1000 + x.PROMPT_TOKENS


def test_valid_district_list():
    for d in [
        "RS-3",
        "RT-4",
        "RT-3.5",
        "RM-6.5",
        "B3-2",
        "C1-1.5",
        "M2-3",
        "DX-12",
        "DX-10",
        "DS-7",
        "POS-3",
        "PD 1234",
        "PMD 4A",
        "POS-2",
        "T",
    ]:
        assert x.valid_district(d), d
    for d in ["RS-4", "B4-2", "DX-9", "RT4", "RT-4.5", "DC-3", "XYZ", None]:
        assert not x.valid_district(d), d
    assert x.clean_district("PMD 4a") == "PMD 4A"


def test_application_cross_check():
    text = "9.    Present Zoning District             RT-4                Proposed Zoning District         RM-5\n10."
    assert x.application_districts(text) == ("RT-4", "RM-5")
    assert x.application_districts("no districts here") == (None, None)


def test_text_source_request():
    p = x.request_params(("text", "SECTION 1 ..."))
    assert p["messages"][0]["content"][0]["source"]["type"] == "text"
    assert p["thinking"] == {"type": "disabled"}


def test_clean_district_fixes_common_ocr_errors():
    assert x.clean_district("BL-1") == "B1-1"
    assert x.clean_district("ML-2") == "M1-2"
    assert x.clean_district("RT3.S") == "RT-3.5"


def test_api_key_prefers_project_name(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    monkeypatch.setenv("CLAUDE_API_KEY_25X125", "b")
    assert x.api_key() == "b"
    monkeypatch.delenv("CLAUDE_API_KEY_25X125")
    assert x.api_key() == "a"
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert x.api_key() is None


def test_clean_district_drops_trailing_district_name():
    assert x.clean_district("C1-2 Neighborhood Commercial District") == "C1-2"
    assert x.clean_district("RT-4-RESIDENTIAL-TWO-FLAT,-TOWNHOUSE-AND-MULTI-UNIT") == "RT-4"
    assert x.clean_district("RM-4.5, as amended") == "RM-4.5"
    assert x.clean_district("B3-3-TOD") == "B3-3"


def test_section1_to_district_reads_ocr_text():
    assert (
        x.section1_to_district("... to those of a Cl-1, Neighborhood Commercial District. SECTION 2")
        == "C1-1"
    )
    assert x.section1_to_district("to those of a RT4 Residential Two-Flat") == "RT-4"
    assert x.section1_to_district("to those of a Bl-3, Neighborhood Shopping") == "B1-3"
    assert x.section1_to_district("no section here") is None


def _write_csvs(tmp_path, monkeypatch):
    out, checked = tmp_path / "out.csv", tmp_path / "checked.csv"
    base = {k: "" for k in x.OUT_COLUMNS} | {
        "model": "claude-haiku-5-5",
        "pdf_url": "u",
        "extracted_on": "2026-11-01",
    }
    rows = [
        base | {"record_number": "A", "changes": '[{"from": "RS-3", "to": "RT-4"}]', "needs_check": "False"},
        base | {"record_number": "B", "changes": '[{"from": "RS-3", "to": "B1-1"}]', "needs_check": "True"},
        base | {"record_number": "C", "changes": '[{"from": "RS-3", "to": "RT-4.5"}]', "needs_check": "True"},
        base | {"record_number": "D", "changes": "", "needs_check": "True"},
        base | {"record_number": "E", "changes": '[{"from": "B3-2", "to": "C-2"}]', "needs_check": "True"},
    ]
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, x.OUT_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    with checked.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            ["record_number", "status", "changes", "checked_against", "note", "checked_by", "checked_on"]
        )
        w.writerow(
            ["B", "corrected", '[{"from": "RS-3", "to": "C1-1"}]', "Section 1", "Cl-1", "hand", "2026-11-01"]
        )
        w.writerow(["C", "unresolved", "", "Section 1", "RT-4.5", "hand", "2026-11-01"])
        w.writerow(["D", "not_a_rezoning", "", "Section 1", "Pedestrian Street", "hand", "2026-11-01"])
    monkeypatch.setattr(x, "OUT", out)
    monkeypatch.setattr(x, "CHECKED", checked)


def test_hand_checks_override_and_flagged_rows_stay_hidden(tmp_path, monkeypatch):
    _write_csvs(tmp_path, monkeypatch)
    got = {r["record_number"]: (r["check"], r["from_district"], r["to_district"]) for r in x.merged_rows()}
    assert got == {
        "A": ("model", "RS-3", "RT-4"),
        "B": ("corrected", "RS-3", "C1-1"),
        "C": ("unresolved", None, None),
        "D": ("not_a_rezoning", None, None),
        "E": ("unresolved", None, None),  # flagged and never checked
    }


def test_apply_copies_checked_districts_into_the_table(db_url, tmp_path, monkeypatch):
    migrate(db_url)
    _write_csvs(tmp_path, monkeypatch)
    with psycopg.connect(db_url) as conn:
        conn.execute("delete from rezoning")
        for rec in "ABCDE":
            conn.execute(
                "insert into rezoning (record_number, matter_id, title, type1, alderman_filed) values (%s, 'm', 't', false, false)",
                (rec,),
            )
    assert x.apply(db_url) == 5
    with psycopg.connect(db_url) as conn:
        got = conn.execute(
            "select record_number, from_district, to_district, district_check from rezoning order by 1"
        ).fetchall()
    assert got == [
        ("A", "RS-3", "RT-4", "model"),
        ("B", "RS-3", "C1-1", "corrected"),
        ("C", None, None, "unresolved"),
        ("D", None, None, "not_a_rezoning"),
        ("E", None, None, "unresolved"),
    ]


def test_checked_file_covers_every_flagged_row():
    with x.OUT.open(newline="", encoding="utf-8") as f:
        flagged = {r["record_number"] for r in csv.DictReader(f) if r["needs_check"] == "True"}
    with x.CHECKED.open(newline="", encoding="utf-8") as f:
        checked = {r["record_number"]: r for r in csv.DictReader(f)}
    assert flagged <= set(checked)
    assert {r["status"] for r in checked.values()} <= {
        "confirmed",
        "corrected",
        "not_a_rezoning",
        "unresolved",
    }
    for r in checked.values():
        for c in json.loads(r["changes"] or "[]"):
            assert c["from"] is None or x.valid_district(c["from"]), (r["record_number"], c)
            assert x.valid_district(c["to"]), (r["record_number"], c)


def test_nightly_imports_without_the_ai_extra():
    """The desktop app installs only the main dependencies, so jobs.nightly must not import anthropic."""
    import subprocess
    import sys

    code = "import sys, jobs.nightly; sys.exit(1 if 'anthropic' in sys.modules else 0)"
    assert subprocess.run([sys.executable, "-c", code], check=False).returncode == 0
