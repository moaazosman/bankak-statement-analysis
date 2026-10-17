"""PDF اصطناعي حقيقي (reportlab) بنفس تخطيط كشف بنكك: تكرار كل سطر + رقم صفحة في التذييل."""
import io

import pytest

pytest.importorskip("reportlab")
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402
from reportlab.pdfbase.pdfmetrics import stringWidth  # noqa: E402

import core  # noqa: E402
from synth import d_in, make_statement, out_group  # noqa: E402


def _pdf(df, per_page=14):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    H = 842

    def put(x, top, s, size=7):
        c.setFont("Helvetica", size)
        c.drawString(x, H - top - 7, s)

    def centered(cx, top, s):
        put(cx - stringWidth(s, "Helvetica", 7) / 2, top, s)

    rows = [r for _, r in df.iterrows() for _ in (0, 1)]       # الكشف يكرر كل سطر
    for p in range(0, len(rows), per_page):
        if p == 0:
            put(60, 100, "Name : TEST USER", 9); put(60, 114, "Customer No : 0000001", 9)
            for t, x in (("Tran", 53), ("Date", 77), ("Description", 181)):
                put(x, 311, t, 9)
            centered(337, 311, "Debit"); centered(415, 311, "Credit"); centered(507, 311, "Balance")
        top = 340.4
        for r in rows[p:p + per_page]:
            put(56, top, r["date"].strftime("%d-%b-%Y"))
            put(116, top, r["description"][:60])
            if r["debit"] == r["debit"]:
                centered(337, top, f"{r['debit']:,.2f}")
            if r["credit"] == r["credit"]:
                centered(415, top, f"{r['credit']:,.2f}")
            centered(507, top, f"{r['balance']:,.0f}")
            top += 25
        put(36, 816.5, "(c) Bank of Khartoum"); put(514, 815.7, f"Page {p // per_page + 1}")
        c.showPage()
    c.save()
    return buf.getvalue()


def test_synthetic_pdf_roundtrip_matches_known_totals():
    ch = [("2026-10-01", d_in(1), None, 50000)] + out_group("2026-10-02", 2, 12000) + \
         out_group("2026-10-03", 3, 8000, fee=100) + [("2026-10-04", d_in(4), None, 2500)]
    src = make_statement(ch)
    pdf = _pdf(src.df)
    st = core.read_statement(io.BytesIO(pdf))
    assert st.dedupe_mode == "paired" and len(st.df) == len(src.df)
    tx, fees = core.build_transactions(st)
    S = core.summarize(tx, fees)
    assert S["received"] == 52500 and S["sent"] == 20000 and S["fees"] == 60 + 110
    rec = core.reconcile(st.df)
    assert rec["ok"], rec
