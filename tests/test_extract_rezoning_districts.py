import io
import json

from pypdf import PdfReader, PdfWriter

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
    p = x.request_params(b"%PDF-1.4")
    assert p["model"] == x.MODEL
    assert p["output_config"]["format"]["schema"]["required"][0] == "changes"
    assert p["messages"][0]["content"][0]["type"] == "document"
    json.dumps(p)


def test_estimate_counts_at_most_two_pages_each():
    est = x.estimate([{"pages": "1"}, {"pages": "9"}])
    assert est["pages_sent"] == 3
    assert est["dollars"] < 0.01
