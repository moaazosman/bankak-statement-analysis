"""منطق قراءة وتدقيق وتحليل كشف حساب بنك الخرطوم (بنكك) PDF.

مبادئ التصميم:
- لا يُحذف أي سطر ولا تُهمل أي قيمة بصمت: كل حالة ملتبسة تُسجَّل في قائمة التحذيرات.
- اتجاه العملية يُحدَّد من عمود المدين/الدائن (مواقع الأعمدة في الصفحة) لا من نص الوصف.
- مطابقة الرصيد تُستخدم كدليل على صحة القراءة (سلسلة الأرصدة بين الأسطر المتتالية).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd
import pdfplumber

DATE_RE = re.compile(r"^\d{2}-[A-Za-z]{3}-\d{4}$")
AMOUNT_RE = re.compile(r"^\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?$|^\d+(?:\.\d{1,2})?$")
ID_RE = re.compile(r"(?<!\d)(\d{11})(?!\d)")
MONTHS_EN = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

MONTHS_AR = {1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
             7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"}
WEEKDAYS_AR = {0: "الإثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس",
               4: "الجمعة", 5: "السبت", 6: "الأحد"}
UNKNOWN = "غير محدد"


def ar_date(ts, year: bool = True) -> str:
    return f"{ts.day} {MONTHS_AR[ts.month]}" + (f" {ts.year}" if year else "")


@dataclass
class Statement:
    df: pd.DataFrame                              # الأسطر بعد إزالة التكرار (ترتيب الكشف الأصلي)
    meta: dict = field(default_factory=dict)
    raw_rows: int = 0
    duplicates_removed: int = 0
    dedupe_mode: str = "none"                     # paired | adjacent | none
    warnings: list = field(default_factory=list)  # تحذيرات القراءة
    rejected: pd.DataFrame = field(default_factory=pd.DataFrame)  # أسطر رُفضت (تاريخ غير صالح)


# ------------------------------------------------------------------ القراءة
def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _parse_date(s: str):
    """تاريخ بصيغة 15-Oct-2026 دون الاعتماد على لغة النظام. يرجع NaT إن كان غير صالح."""
    try:
        d, m, y = s.split("-")
        return pd.Timestamp(datetime(int(y), MONTHS_EN[m.lower()], int(d)))
    except (ValueError, KeyError):
        return pd.NaT


def _meta(text: str) -> dict:
    def g(label):
        m = re.search(rf"{label}\s*:\s*(.+)", text)
        return m.group(1).strip() if m else ""
    return {"name": g("Name"), "customer_no": g("Customer No"),
            "account_type": g("Account Type"), "currency": g("Currency") or "SDG",
            "issue_date": g("Issue Date"), "period": g("Duration")}


def _parse_page(page, cols):
    """يرجع (الأسطر، نص وصف مكمّل لسطر الصفحة السابقة)."""
    words = page.extract_words(keep_blank_chars=False, use_text_flow=False)

    # رأس الجدول: كلمة Tran وبقية كلمات الرأس على نفس الخط (لا نعتمد على كلمة Balance وحدها)
    tran = next((w for w in words if w["text"] == "Tran"), None)
    header_bottom = 0.0
    if tran is not None:
        head = [w for w in words if abs(w["top"] - tran["top"]) < 3]
        header_bottom = max(w["bottom"] for w in head)
        for w in head:
            c = (w["x0"] + w["x1"]) / 2
            if w["text"] == "Debit":
                cols["debit"] = c
            elif w["text"] == "Credit":
                cols["credit"] = c
            elif w["text"] == "Balance":
                cols["balance"] = c

    # التذييل: "© Bank of Khartoum  Page N" — رقم الصفحة يجب ألا يُقرأ كرصيد
    marks = [w["top"] for w in words if w["text"] in ("©", "Page")]
    footer_top = (min(marks) - 2) if marks else page.height
    words = [w for w in words if header_bottom <= w["top"] < footer_top]

    dates = sorted((w for w in words if DATE_RE.match(w["text"]) and w["x0"] < 110),
                   key=lambda w: w["top"])
    if not dates:
        return [], ""
    cols["desc_x0"] = max(d["x1"] for d in dates) + 4
    ys = [d["top"] for d in dates]
    rows = [{"date_str": d["text"], "desc": [], "debit": np.nan, "credit": np.nan,
             "balance": np.nan, "conflict": False} for d in dates]
    split_dc = (cols["debit"] + cols["credit"]) / 2
    split_cb = (cols["credit"] + cols["balance"]) / 2
    date_ids = {id(d) for d in dates}
    lead = []

    for w in words:
        if id(w) in date_ids:
            continue
        if w["top"] < ys[0] - 1:           # نص قبل أول سطر: تكملة وصف من الصفحة السابقة
            if not AMOUNT_RE.match(w["text"]):
                lead.append((w["top"], w["x0"], w["text"]))
            continue
        i = max(k for k in range(len(ys)) if ys[k] <= w["top"] + 1)
        xc = (w["x0"] + w["x1"]) / 2
        if AMOUNT_RE.match(w["text"]) and w["x0"] > cols["debit"] - 45:
            col = "debit" if xc < split_dc else ("credit" if xc < split_cb else "balance")
            if not np.isnan(rows[i][col]):
                rows[i]["conflict"] = True
            else:
                rows[i][col] = _num(w["text"])
        elif w["x0"] >= cols["desc_x0"]:
            rows[i]["desc"].append((w["top"], w["x0"], w["text"]))

    def join(parts):
        t = " ".join(x for _, _, x in sorted(parts, key=lambda p: (round(p[0]), p[1])))
        return re.sub(r"\s+", " ", t.replace("++++ End of Statement ++++", "")).strip()

    for r in rows:
        r["description"] = join(r.pop("desc"))
    return rows, join(lead)


def _dedupe(df: pd.DataFrame):
    """إزالة تكرار الأسطر دون حذف معاملات حقيقية.

    كشوف بنكك تكرر كل سطر مرتين متتاليتين. نعتمد وضعين:
    - paired: عدد الأسطر زوجي وكل زوجين متتاليين متطابقان تماماً في (التاريخ، المدين، الدائن)
      ولا يتعارض معرّف العملية بينهما → نُبقي أول سطر من كل زوج.
    - adjacent: خلاف ذلك، لا نحذف إلا سطراً يطابق السطر السابق مباشرة في
      (التاريخ، المدين، الدائن، معرّف العملية) وله معرّف. الأسطر بلا معرّف لا تُحذف
      أبداً (قد تكون عمليتين حقيقيتين متشابهتين) ويُحذَّر منها.
    """
    warns = []
    n = len(df)
    key = ["date", "debit", "credit"]

    def eq(a, b):
        return (a == b) | (a.isna() & b.isna())

    if n >= 2 and n % 2 == 0:
        a, b = df.iloc[0::2].reset_index(drop=True), df.iloc[1::2].reset_index(drop=True)
        same = eq(a["date"], b["date"]) & eq(a["debit"], b["debit"]) & eq(a["credit"], b["credit"])
        id_conflict = a["tx_id"].notna() & b["tx_id"].notna() & (a["tx_id"] != b["tx_id"])
        ok = same & ~id_conflict
        if ok.all():
            return a, n - len(a), "paired", warns
        if ok.mean() >= 0.8:
            warns.append(f"الكشف يبدو مكرراً لكن {int((~ok).sum())} زوجاً غير متطابق؛ "
                         "لم يُطبَّق حذف الأزواج وجرى استخدام الحذف المحافظ.")
    keep, removed, ambiguous = [], 0, 0
    prev = None
    for idx, r in df.iterrows():
        cur = (r["date"], r["debit"], r["credit"], r["tx_id"])
        same_as_prev = prev is not None and all(
            (x == y) or (pd.isna(x) and pd.isna(y)) for x, y in zip(cur, prev))
        if same_as_prev and pd.notna(r["tx_id"]):
            removed += 1
        else:
            if same_as_prev:
                ambiguous += 1
            keep.append(idx)
        prev = cur
    if ambiguous:
        warns.append(f"{ambiguous} سطراً متطابقاً مع السطر السابق لكن بلا معرّف عملية؛ "
                     "أُبقيت لأنه لا يمكن الجزم أنها مكررة.")
    return df.loc[keep], removed, ("adjacent" if removed else "none"), warns


def read_statement(file, drop_duplicates: bool = True) -> Statement:
    cols = {"debit": 337.0, "credit": 415.0, "balance": 507.0, "desc_x0": 100.0}
    rows, meta, warns = [], {}, []
    try:
        pdf = pdfplumber.open(file)
    except Exception as e:  # noqa: BLE001
        raise ValueError("تعذّر فتح الملف كـ PDF صالح (قد يكون تالفاً أو محمياً بكلمة مرور).") from e
    with pdf:
        for n, page in enumerate(pdf.pages):
            if n == 0:
                meta = _meta(page.extract_text() or "")
            page_rows, lead = _parse_page(page, cols)
            if lead:
                if rows:
                    rows[-1]["description"] = f'{rows[-1]["description"]} {lead}'.strip()
                    warns.append(f"صفحة {n + 1}: وصف مكمّل لآخر معاملة في الصفحة السابقة أُلحق بها.")
                else:
                    warns.append(f"صفحة {n + 1}: نص قبل أول معاملة جرى تجاهله.")
            for r in page_rows:
                r["page"] = n + 1
            rows += page_rows
    if not rows:
        raise ValueError("لم أجد أي معاملات. تأكد أن الملف كشف حساب بنكك بصيغة PDF نصية "
                         "(وليس صورة ممسوحة ضوئياً).")

    df = pd.DataFrame(rows)
    df["date"] = df.pop("date_str").map(_parse_date)
    bad = df["date"].isna()
    rejected = df[bad].copy()
    if bad.any():
        warns.append(f"{int(bad.sum())} سطراً بتاريخ غير صالح استُبعد من التحليل ولم يُحوَّل لقيمة افتراضية.")
        df = df[~bad]
    if df["conflict"].any():
        warns.append(f"{int(df['conflict'].sum())} سطراً فيه أكثر من قيمة في العمود نفسه؛ "
                     "أُخذت القيمة الأولى فقط، راجع الكشف الأصلي.")
    df["tx_id"] = df["description"].str.extract(ID_RE, expand=False)
    df = df.reset_index(drop=True)
    raw = len(df)

    mode, removed = "none", 0
    if drop_duplicates:
        df, removed, mode, dw = _dedupe(df)
        warns += dw
    df = df.reset_index(drop=True)
    return Statement(df, meta, raw, removed, mode, warns, rejected.reset_index(drop=True))


# ------------------------------------------------------------------ التصنيف
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
    """يرجع (المعاملات الأساسية مع رسومها، سجل الرسوم).

    ربط الرسوم بمعرّف العملية فقط؛ إن تكرر المعرّف بين معاملتين أساسيتين تُنسب الرسوم
    للأولى وحدها (لا احتساب مزدوج)، والرسوم التي لا معاملة لها تبقى في سجل الرسوم
    بعلامة linked=False ولا تُحذف.
    """
    df = stmt.df.copy()
    df["kind"] = df["description"].map(_kind)
    df["category"] = df["description"].map(_category)
    dr, cr = df["debit"].fillna(0.0), df["credit"].fillna(0.0)

    tx = df[df["kind"] == "معاملة"].copy()
    fe = df[df["kind"] != "معاملة"].copy()
    tdr, tcr = dr[tx.index], cr[tx.index]
    tx["direction"] = np.select([(tcr > 0) & (tdr == 0), (tdr > 0) & (tcr == 0)],
                                ["مستلم", "مرسل"], UNKNOWN)
    tx["amount"] = np.select([tx.direction == "مستلم", tx.direction == "مرسل"], [tcr, tdr], 0.0)
    tx["tx_id"] = tx["tx_id"].astype("object")

    fe["amount"] = dr[fe.index]
    fe["fee_type"] = fe["kind"]
    fee_sum = fe[fe.tx_id.notna()].groupby("tx_id").amount.sum()
    first = tx.tx_id.notna() & ~tx.tx_id.duplicated(keep="first")
    tx["fees"] = 0.0
    tx.loc[first, "fees"] = tx.loc[first, "tx_id"].map(fee_sum).fillna(0.0)

    firsts = tx[first]
    ids = set(firsts["tx_id"])
    cat_of = dict(zip(firsts["tx_id"], firsts["category"]))
    date_of = dict(zip(firsts["tx_id"], firsts["date"]))
    fe["linked"] = fe["tx_id"].isin(ids)
    fe["tx_category"] = fe["tx_id"].map(cat_of)
    fe["tx_date"] = pd.to_datetime(fe["tx_id"].map(date_of))

    tx["weekday"] = tx["date"].dt.weekday.map(WEEKDAYS_AR)
    tx = tx[["date", "weekday", "direction", "category", "amount", "fees",
             "description", "tx_id"]].sort_values("date", kind="stable").reset_index(drop=True)
    fe = fe[["date", "fee_type", "amount", "tx_category", "tx_id", "linked", "tx_date"]]
    return tx, fe.reset_index(drop=True)


def filter_fees(fees: pd.DataFrame, tx: pd.DataFrame) -> pd.DataFrame:
    """رسوم المعاملات المعروضة + الرسوم غير المرتبطة (لا تُخفى بصمت)."""
    return fees[(~fees["linked"]) | fees["tx_id"].isin(tx["tx_id"])]


# ------------------------------------------------------------------ الحسابات
def summarize(tx: pd.DataFrame, fees: pd.DataFrame) -> dict:
    sent = tx[tx.direction == "مرسل"]
    recv = tx[tx.direction == "مستلم"]
    total_fees = float(fees["amount"].sum())
    s, r = float(sent.amount.sum()), float(recv.amount.sum())
    return {
        "received": r, "received_n": len(recv), "sent": s, "sent_n": len(sent),
        "fees": total_fees,
        "stamp": float(fees.loc[fees.fee_type == "دمغة", "amount"].sum()),
        "service": float(fees.loc[fees.fee_type == "رسوم", "amount"].sum()),
        "net": r - s - total_fees,
        "fee_pct": (total_fees / s * 100) if s else 0.0,
        "avg_sent": float(sent.amount.mean()) if len(sent) else 0.0,
        "avg_recv": float(recv.amount.mean()) if len(recv) else 0.0,
        "unknown_n": int((tx.direction == UNKNOWN).sum()),
    }


def daily(tx: pd.DataFrame, fees: pd.DataFrame) -> pd.DataFrame:
    cols = ["date", "sent", "sent_n", "received", "received_n", "fees", "net", "cum_net", "total_n"]
    if tx.empty:
        return pd.DataFrame(columns=cols)
    idx = pd.date_range(tx.date.min(), tx.date.max())
    s = tx[tx.direction == "مرسل"].groupby("date").amount.agg(sent="sum", sent_n="count")
    r = tx[tx.direction == "مستلم"].groupby("date").amount.agg(received="sum", received_n="count")
    f = fees.groupby("date").amount.sum().rename("fees")
    d = pd.concat([s, r, f], axis=1).reindex(idx).fillna(0.0)
    for c in ("sent", "sent_n", "received", "received_n", "fees"):
        if c not in d:
            d[c] = 0.0
    d.index.name = "date"
    d["net"] = d.received - d.sent - d.fees
    d["cum_net"] = d.net.cumsum()
    d["total_n"] = d.sent_n + d.received_n
    return d.reset_index()[cols]


def monthly(tx: pd.DataFrame, fees: pd.DataFrame) -> pd.DataFrame:
    """ملخص شهري مع السنة."""
    t = tx.assign(ym=tx.date.dt.to_period("M"))
    fe = fees.assign(ym=fees.date.dt.to_period("M"))
    r = t[t.direction == "مستلم"].groupby("ym").amount.sum().rename("received")
    s = t[t.direction == "مرسل"].groupby("ym").amount.sum().rename("sent")
    f = fe.groupby("ym").amount.sum().rename("fees")
    m = pd.concat([r, s, f], axis=1).fillna(0.0).sort_index()
    for c in ("received", "sent", "fees"):
        if c not in m:
            m[c] = 0.0
    m["net"] = m.received - m.sent - m.fees
    m["label"] = [f"{MONTHS_AR[p.month]} {p.year}" for p in m.index]
    return m.reset_index(drop=True)


# ------------------------------------------------------------------ التدقيق
def reconcile(df: pd.DataFrame, tol: float = 0.5) -> dict:
    """مطابقة الرصيد: في كشوف بنكك عمود الرصيد هو الرصيد بعد كل سطر، والأسطر الأحدث أولاً.
    نتحقق من السلسلة bal[i] = bal[i+1] + credit[i] - debit[i] (ونجرب الترتيب المعاكس)،
    ثم من أن (الرصيد الأخير − الافتتاحي) = مجموع الدائن − المدين."""
    if len(df) < 2 or df["balance"].isna().any():
        return {"available": False, "reason": "عمود الرصيد غير مكتمل في الكشف."}
    d = df.reset_index(drop=True)
    cr, dr, bal = d["credit"].fillna(0.0), d["debit"].fillna(0.0), d["balance"]

    def breaks(order):
        o = d.iloc[order].reset_index(drop=True)  # من الأحدث إلى الأقدم
        c, r, b = o["credit"].fillna(0.0), o["debit"].fillna(0.0), o["balance"]
        exp = b.shift(-1) + c - r
        bad = (exp - b).abs() > tol
        bad.iloc[-1] = False
        return o, bad

    asc = list(range(len(d) - 1, -1, -1))
    o_desc, bad_desc = breaks(list(range(len(d))))
    o_asc, bad_asc = breaks(asc)
    orientation, o, bad = (("desc", o_desc, bad_desc) if bad_desc.sum() <= bad_asc.sum()
                           else ("asc", o_asc, bad_asc))
    opening = float(o["balance"].iloc[-1] - o["credit"].fillna(0).iloc[-1] + o["debit"].fillna(0).iloc[-1])
    closing = float(o["balance"].iloc[0])
    expected = opening + float(cr.sum() - dr.sum())
    diff = closing - expected
    return {"available": True, "orientation": orientation, "breaks": int(bad.sum()),
            "opening": opening, "closing": closing, "expected_closing": expected,
            "diff": diff, "ok": int(bad.sum()) == 0 and abs(diff) <= tol}


def audit(stmt: Statement, tx: pd.DataFrame, fees: pd.DataFrame) -> list[dict]:
    """قائمة ملاحظات التدقيق: [{level: info|warn, text}]. لا تُغيّر البيانات."""
    out = []

    def add(level, text):
        out.append({"level": level, "text": text})

    if stmt.dedupe_mode == "paired":
        add("info", f"الكشف يكرر كل سطر مرتين؛ حُسب كل سطر مرة واحدة ({stmt.duplicates_removed} سطراً مكرراً).")
    elif stmt.duplicates_removed:
        add("info", f"أُزيل {stmt.duplicates_removed} سطراً مكرراً بمعرّف عملية مطابق.")
    for w in stmt.warnings:
        add("warn", w)

    unk = tx[tx.direction == UNKNOWN]
    if len(unk):
        add("warn", f"{len(unk)} عملية بلا مدين/دائن واضح (غير محدد الاتجاه) ولا تدخل في المجاميع.")
    other = int((tx.category == "أخرى").sum())
    if other:
        add("warn", f"{other} عملية لم يتعرف عليها المصنِّف وصُنّفت «أخرى».")
    ids = tx.tx_id.dropna()
    dup_ids = ids[ids.duplicated(keep=False)].nunique()
    if dup_ids:
        add("warn", f"{dup_ids} معرّف عملية يتكرر بين معاملات مختلفة؛ نُسبت رسومه للأولى فقط.")
    no_id = int(tx.tx_id.isna().sum())
    if no_id:
        add("warn", f"{no_id} معاملة بلا معرّف عملية؛ لا يمكن ربط رسومها.")
    unl = fees[~fees.linked]
    if len(unl):
        add("warn", f"{len(unl)} سطر رسوم (إجمالي {unl.amount.sum():,.0f}) بلا معاملة مرتبطة؛ "
                    "مُحتسبة في إجمالي الرسوم.")
    mism = fees[fees.linked & (fees.date != fees.tx_date)]
    if len(mism):
        add("warn", f"{len(mism)} سطر رسوم تاريخه يختلف عن تاريخ معاملته.")
    st = stmt.df
    refund = int((st.loc[st.description.map(_kind) != "معاملة", "credit"].fillna(0) > 0).sum())
    if refund:
        add("warn", f"{refund} سطر رسوم فيه مبلغ دائن (استرداد؟) لم يُخصم من الرسوم.")
    dups = int(st.duplicated(subset=["date", "debit", "credit", "description"]).sum())
    if dups:
        add("warn", f"{dups} سطراً ما زال مطابقاً تماماً لسطر آخر في التاريخ والمبلغ والوصف.")

    rec = reconcile(st)
    if not rec["available"]:
        add("info", "تعذّرت مطابقة الرصيد: " + rec["reason"])
    elif rec["ok"]:
        add("info", f"مطابقة الرصيد ناجحة: افتتاحي {rec['opening']:,.0f} ← ختامي {rec['closing']:,.0f}.")
    else:
        add("warn", f"مطابقة الرصيد فشلت: {rec['breaks']} انقطاعاً في سلسلة الأرصدة، "
                    f"والفرق عن المتوقع {rec['diff']:,.0f}. راجع القراءة أو الكشف الأصلي.")
    return out
