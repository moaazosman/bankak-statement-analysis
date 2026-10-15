"""منطق قراءة وتحليل كشف حساب بنك الخرطوم (بنكك) PDF."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd
import pdfplumber

DATE_RE = re.compile(r"^\d{2}-[A-Za-z]{3}-\d{4}$")
AMOUNT_RE = re.compile(r"^\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?$")
ID_RE = re.compile(r"(?<!\d)(\d{11})(?!\d)")

MONTHS_AR = {1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
             7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"}


def ar_date(ts) -> str:
    return f"{ts.day} {MONTHS_AR[ts.month]}"


WEEKDAYS_AR = {0: "الإثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس",
               4: "الجمعة", 5: "السبت", 6: "الأحد"}


@dataclass
class Statement:
    df: pd.DataFrame                       # كل الأسطر الخام (بعد إزالة التكرار اختياريًا)
    meta: dict = field(default_factory=dict)
    raw_rows: int = 0
    duplicates_removed: int = 0


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _meta(text: str) -> dict:
    def g(label):
        m = re.search(rf"{label}\s*:\s*(.+)", text)
        return m.group(1).strip() if m else ""
    return {
        "name": g("Name"),
        "customer_no": g("Customer No"),
        "account_type": g("Account Type"),
        "currency": g("Currency") or "SDG",
        "issue_date": g("Issue Date"),
        "period": g("Duration"),
    }


def _parse_page(page, cols):
    words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
    # حدود الأعمدة من رأس الجدول إن وجد
    for w in words:
        if w["text"] == "Debit":
            cols["debit"] = (w["x0"] + w["x1"]) / 2
        elif w["text"] == "Credit":
            cols["credit"] = (w["x0"] + w["x1"]) / 2
        elif w["text"] == "Balance":
            cols["balance"] = (w["x0"] + w["x1"]) / 2
    footer = min((w["top"] for w in words if w["text"] == "©"), default=page.height)
    header_bottom = max((w["bottom"] for w in words if w["text"] == "Balance"), default=0)
    words = [w for w in words if header_bottom <= w["top"] < footer]

    dates = sorted((w for w in words if DATE_RE.match(w["text"]) and w["x0"] < 110),
                   key=lambda w: w["top"])
    if not dates:
        return []
    cols["desc_x0"] = max(d["x1"] for d in dates) + 4
    ys = [d["top"] for d in dates]
    rows = [{"date": d["text"], "desc": [], "debit": 0.0, "credit": 0.0, "balance": None}
            for d in dates]
    split_dc = (cols["debit"] + cols["credit"]) / 2
    split_cb = (cols["credit"] + cols["balance"]) / 2

    for w in words:
        if w in dates:
            continue
        # السطر يتبع آخر تاريخ يسبقه (الوصف يبدأ بنفس سطر التاريخ ثم يلتف للأسفل)
        i = max((k for k in range(len(ys)) if ys[k] <= w["top"] + 1), default=0)
        xc = (w["x0"] + w["x1"]) / 2
        if w["x0"] >= cols["desc_x0"] and xc < split_dc - 25 and not (
                AMOUNT_RE.match(w["text"]) and w["x0"] > cols["debit"] - 40):
            rows[i]["desc"].append((w["top"], w["x0"], w["text"]))
        elif AMOUNT_RE.match(w["text"]):
            if xc < split_cb and xc < split_dc:
                rows[i]["debit"] = _num(w["text"])
            elif xc < split_cb:
                rows[i]["credit"] = _num(w["text"])
            else:
                rows[i]["balance"] = _num(w["text"])
    out = []
    for r in rows:
        desc = " ".join(t for _, _, t in sorted(r["desc"], key=lambda x: (round(x[0]), x[1])))
        desc = desc.replace("++++ End of Statement ++++", "").strip()
        r["description"] = re.sub(r"\s+", " ", desc)
        del r["desc"]
        out.append(r)
    return out


def _dedupe(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """كشوف بنكك تكرر كل سطر مرتين متتاليتين. نكتشف ذلك من (التاريخ، المدين، الدائن)
    دون الاعتماد على نص الوصف أو الرصيد لأنهما قد يختلفان بين نسختي السطر."""
    n = len(df)
    key = ["date", "debit", "credit"]
    if n >= 2 and n % 2 == 0:
        a = df.iloc[0::2].reset_index(drop=True)
        b = df.iloc[1::2].reset_index(drop=True)
        if (a[key] == b[key]).all(axis=1).mean() >= 0.95:
            return a, n - len(a)
    out = df.drop_duplicates(subset=key + ["description"])
    return out, n - len(out)


def read_statement(file, drop_duplicates: bool = True) -> Statement:
    cols = {"debit": 337.0, "credit": 415.0, "balance": 507.0, "desc_x0": 100.0}
    rows, meta = [], {}
    with pdfplumber.open(file) as pdf:
        for n, page in enumerate(pdf.pages):
            if n == 0:
                meta = _meta(page.extract_text() or "")
            rows += _parse_page(page, cols)
    if not rows:
        raise ValueError("لم أجد أي معاملات. تأكد أن الملف كشف حساب بنكك بصيغة PDF نصية.")
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], format="%d-%b-%Y")
    raw = len(df)
    removed = 0
    if drop_duplicates:
        df, removed = _dedupe(df)
    return Statement(df.reset_index(drop=True), meta, raw, removed)


# ---------------------------------------------------------------- التصنيف
def _kind(desc: str) -> str:
    d = desc.lower()
    if d.startswith("stamp duty"):
        return "دمغة"
    if d.startswith("charges") or "bankak fees" in d:
        return "رسوم"
    return "معاملة"


def _category(desc: str) -> str:
    d = desc.lower()
    if "zain" in d:
        return "شحن رصيد زين"
    if "sudani" in d:
        return "شحن رصيد سوداني"
    if "esali" in d or "esaly" in d:
        return "إيصالي (فواتير)"
    if "p2p" in d or "other bank" in d:
        return "تحويل لبنك آخر"
    if "ebs" in d:
        return "تحويل عبر EBS"
    if "funds transfer" in d:
        return "تحويل بنكك"
    return "أخرى"


def build_transactions(stmt: Statement) -> tuple[pd.DataFrame, pd.DataFrame]:
    """يرجع (المعاملات الأساسية مع رسومها، سجل الرسوم)."""
    df = stmt.df.copy()
    df["kind"] = df["description"].map(_kind)
    df["category"] = df["description"].map(_category)
    df["tx_id"] = df["description"].str.extract(ID_RE, expand=False)
    df["fee"] = df["debit"].where(df["kind"] != "معاملة", 0.0)

    fees = df[df["kind"] != "معاملة"].copy()
    fees["amount"] = fees["debit"]
    fee_by_tx = fees.groupby("tx_id")["amount"].sum().rename("fees")

    tx = df[df["kind"] == "معاملة"].copy()
    tx["direction"] = tx["credit"].gt(0).map({True: "مستلم", False: "مرسل"})
    tx["amount"] = tx["debit"] + tx["credit"]
    tx = tx.join(fee_by_tx, on="tx_id")
    tx["fees"] = tx["fees"].fillna(0.0)
    tx["weekday"] = tx["date"].dt.weekday.map(WEEKDAYS_AR)
    tx = tx[["date", "weekday", "direction", "category", "amount", "fees",
             "description", "tx_id"]].sort_values("date").reset_index(drop=True)

    fees = fees.join(tx.set_index("tx_id")["category"].rename("tx_category")
                     .groupby(level=0).first(), on="tx_id")
    fees["fee_type"] = fees["kind"]
    return tx, fees[["date", "fee_type", "amount", "tx_category", "tx_id"]].reset_index(drop=True)


def summarize(tx: pd.DataFrame, fees: pd.DataFrame) -> dict:
    sent = tx[tx.direction == "مرسل"]
    recv = tx[tx.direction == "مستلم"]
    total_fees = fees["amount"].sum()
    return {
        "received": recv.amount.sum(), "received_n": len(recv),
        "sent": sent.amount.sum(), "sent_n": len(sent),
        "fees": total_fees,
        "stamp": fees.loc[fees.fee_type == "دمغة", "amount"].sum(),
        "service": fees.loc[fees.fee_type == "رسوم", "amount"].sum(),
        "net": recv.amount.sum() - sent.amount.sum() - total_fees,
        "fee_pct": (total_fees / sent.amount.sum() * 100) if len(sent) else 0.0,
        "avg_sent": sent.amount.mean() if len(sent) else 0.0,
        "avg_recv": recv.amount.mean() if len(recv) else 0.0,
    }


def daily(tx: pd.DataFrame, fees: pd.DataFrame) -> pd.DataFrame:
    idx = pd.date_range(tx.date.min(), tx.date.max())
    s = tx[tx.direction == "مرسل"].groupby("date").amount.agg(sent="sum", sent_n="count")
    r = tx[tx.direction == "مستلم"].groupby("date").amount.agg(received="sum", received_n="count")
    f = fees.groupby("date").amount.sum().rename("fees")
    d = pd.concat([s, r, f], axis=1).reindex(idx).fillna(0.0)
    d.index.name = "date"
    d["net"] = d.received - d.sent - d.fees
    d["cum_net"] = d.net.cumsum()
    d["total_n"] = d.sent_n + d.received_n
    return d.reset_index()
