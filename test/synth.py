"""بيانات اصطناعية فقط — لا تحتوي أي بيانات عميل حقيقي."""
from contextlib import contextmanager
from unittest.mock import patch

import pandas as pd

import core

HEADER = [("Tran", 53, 75), ("Date", 77, 97), ("Description", 181, 231),
          ("Debit", 325, 348), ("Credit", 401, 429), ("Balance", 490, 524)]


def _w(text, x0, x1, top):
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": top + 8}


class FakePage:
    """صفحة تحاكي pdfplumber بإحداثيات قريبة من كشف بنكك الفعلي (عرض 595)."""
    width, height = 595, 842

    def __init__(self, rows=(), header=True, page_no=1, extra=()):
        self.words = []
        if header:
            self.words += [_w(t, a, b, 311) for t, a, b in HEADER]
        top = 340.4
        for r in rows:
            self.words.append(_w(r["date"], 56, 95, top))
            toks = r.get("desc", "").split()
            for i, t in enumerate(toks):
                line, col = divmod(i, 5)
                self.words.append(_w(t, 116 + col * 30, 116 + col * 30 + 28, top + 7 * line))
            if r.get("debit") is not None:
                self.words.append(_w(r["debit"], 325, 350, top))
            if r.get("credit") is not None:
                self.words.append(_w(r["credit"], 398, 433, top))
            if r.get("balance") is not None:
                self.words.append(_w(r["balance"], 490, 520, top))
            top += 25
        self.words += list(extra)
        # تذييل: "© Bank of Khartoum   Page N" — "Page" أعلى قليلاً من "©" كما في الكشف الحقيقي
        self.words += [_w("©", 36, 44, 816.5), _w("Bank", 48, 70, 816.5),
                       _w("Page", 514, 530, 815.7), _w(str(page_no), 535, 540, 815.7)]

    def extract_words(self, **kw):
        return [dict(w) for w in self.words]

    def extract_text(self):
        return "Name : TEST USER\nCustomer No : 0000001\nAccount Type : Saving Account\nCurrency : SDG\n"


class FakePdf:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@contextmanager
def fake_pdf(*pages):
    with patch.object(core.pdfplumber, "open", return_value=FakePdf(list(pages))):
        yield


def row(date, desc, debit=None, credit=None, balance=None):
    return {"date": date, "desc": desc, "debit": debit, "credit": credit, "balance": balance}


# ---- بناء Statement مباشرة (للاختبارات المالية) --------------------------------
def d_out(i, ref="1"):      # عملية تحويل مرسلة
    return f"Funds Transfer - MB # 2018813{i:04d},Transfer ref.{ref}"


def d_stamp(i, ref="1"):
    return f"Stamp Duty - Funds Transfer - MB #2018813{i:04d} , Transfer ref.{ref}"


def d_charge(i, ref="1"):
    return f"Charges - Funds Transfer - MB #2018813{i:04d} , Transfer ref.{ref}"


def d_in(i, ref="1"):
    return f"TRF EBS BBAN # 2018813{i:04d},Transfer ref.{ref}"


def make_statement(chrono, opening=0.0, doubled=False, with_balance=True):
    """chrono: [(date, desc, debit, credit)] بالترتيب الزمني. الناتج بترتيب الكشف (الأحدث أولاً)
    والرصيد = الرصيد بعد كل سطر."""
    bal, recs = opening, []
    for date, desc, dr, cr in chrono:
        bal = bal + (cr or 0) - (dr or 0)
        recs.append({"date": pd.Timestamp(date), "description": desc,
                     "debit": float(dr) if dr else float("nan"),
                     "credit": float(cr) if cr else float("nan"),
                     "balance": bal if with_balance else float("nan"),
                     "conflict": False, "page": 1})
    recs = recs[::-1]
    if doubled:
        recs = [r for r in recs for _ in (0, 1)]
    df = pd.DataFrame(recs)
    df["tx_id"] = df["description"].str.extract(core.ID_RE, expand=False)
    return core.Statement(df=df, raw_rows=len(df))


def out_group(date, i, amount, fee=50, stamp=10):
    """تحويل مرسل كما في الكشف: العملية ثم الرسوم ثم الدمغة (زمنياً)."""
    return [(date, d_out(i), amount, None), (date, d_charge(i), fee, None), (date, d_stamp(i), stamp, None)]
