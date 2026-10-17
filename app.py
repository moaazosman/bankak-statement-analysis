import hashlib
import io

import pandas as pd
import streamlit as st

import charts
import core
import ui

st.set_page_config(page_title="محلل كشف بنكك", page_icon="📊", layout="wide",
                   initial_sidebar_state="collapsed")


def _system_dark() -> bool:
    try:
        return st.context.theme.type != "light"
    except Exception:  # noqa: BLE001
        return True


if "dark" not in st.session_state:
    st.session_state["dark"] = _system_dark()

dark = st.toggle("الوضع الداكن", key="dark")
mode = "dark" if dark else "light"
st.markdown(ui.css(mode), unsafe_allow_html=True)
st.markdown(ui.hero(), unsafe_allow_html=True)

CFG = {"displayModeBar": False, "responsive": True}


def plot(fig):
    try:
        st.plotly_chart(fig, width="stretch", config=CFG)
    except Exception:  # noqa: BLE001  (إصدارات أقدم من Streamlit)
        st.plotly_chart(fig, use_container_width=True, config=CFG)


def card(icon, title, sub, fig):
    with st.container(border=True):
        st.markdown(ui.head(icon, title, sub), unsafe_allow_html=True)
        plot(fig)


def money(x):
    return f"{x:,.0f}"


up = st.file_uploader("اختر ملف PDF لكشف الحساب", type="pdf")
if not up:
    st.info("ارفع كشف حسابك من بنكك لبدء التحليل.")
    st.stop()


def load(data: bytes):
    """القراءة تُحفظ في session_state فقط (تُحذف بانتهاء الجلسة)؛ لا cache مشترك بين المستخدمين."""
    key = hashlib.sha256(data).hexdigest()
    cached = st.session_state.get("_parsed")
    if cached and cached[0] == key:
        return cached[1]
    stmt = core.read_statement(io.BytesIO(data), True)
    tx, fees = core.build_transactions(stmt)
    res = (stmt, tx, fees, core.audit(stmt, tx, fees))
    st.session_state["_parsed"] = (key, res)
    return res


try:
    with st.spinner("جارٍ قراءة الكشف..."):
        stmt, tx, fees, audit_notes = load(up.getvalue())
except Exception as e:  # noqa: BLE001
    st.error(f"تعذّرت قراءة الملف: {e}")
    st.stop()
if tx.empty:
    st.warning("لم أجد معاملات في هذا الكشف.")
    st.stop()

lo, hi = tx.date.min().date(), tx.date.max().date()
with st.expander("تصفية النتائج"):
    rng = st.date_input("الفترة", (lo, hi), min_value=lo, max_value=hi)
    all_cats = sorted(tx.category.unique())
    cats = st.multiselect("نوع العملية", all_cats, default=all_cats)
    all_years = sorted(tx.date.dt.year.unique())
    years = (st.multiselect("السنة", all_years, default=all_years)
             if len(all_years) > 1 else all_years)

if isinstance(rng, tuple) and len(rng) == 2:
    a, b = pd.Timestamp(rng[0]), pd.Timestamp(rng[1])
    tx = tx[(tx.date >= a) & (tx.date <= b) & tx.category.isin(cats)
            & tx.date.dt.year.isin(years)]
    fees = fees[(fees.date >= a) & (fees.date <= b) & fees.date.dt.year.isin(years)]
    fees = core.filter_fees(fees, tx)
if tx.empty:
    st.warning("لا توجد بيانات ضمن هذا الفلتر.")
    st.stop()

m = stmt.meta
st.markdown(
    '<div class="meta">'
    f'<span>{ui.svg("user", 14)}{ui.esc(m.get("name", ""))}</span>'
    f'<span>{ui.svg("file", 14)}رقم العميل {ui.esc(m.get("customer_no", ""))}</span>'
    f'<span>{ui.svg("calendar", 14)}{core.ar_date(pd.Timestamp(lo))} – {core.ar_date(pd.Timestamp(hi))}</span>'
    f'<span>{ui.svg("layers", 14)}{len(tx)} عملية بعد إزالة {stmt.duplicates_removed} سطراً مكرراً</span>'
    '</div>', unsafe_allow_html=True)

warn_n = sum(1 for n in audit_notes if n["level"] == "warn")
with st.expander(f"تدقيق البيانات — {warn_n} تنبيه" if warn_n else "تدقيق البيانات — لا تنبيهات",
                 expanded=bool(warn_n)):
    for n in audit_notes:
        (st.warning if n["level"] == "warn" else st.info)(n["text"])

S = core.summarize(tx, fees)
D = core.daily(tx, fees)

st.markdown(ui.kpis([
    ("down", "المستلم", money(S["received"]), f"{S['received_n']} عملية", "green"),
    ("up", "المرسل", money(S["sent"]), f"{S['sent_n']} عملية", "red"),
    ("receipt", "الرسوم والدمغة", money(S["fees"]), f"{S['fee_pct']:.2f}% من المرسل", "amber"),
    ("wallet", "الصافي", money(S["net"]), "مستلم − مرسل − رسوم",
     "green" if S["net"] >= 0 else "red"),
]), unsafe_allow_html=True)

busiest = D.loc[D.total_n.idxmax()]
top_sent = D.loc[D.sent.idxmax()]
top_recv = D.loc[D.received.idxmax()]
big = tx.loc[tx.amount.idxmax()]
notes = [
    f"أكثر الأيام نشاطاً: <b>{core.ar_date(busiest.date)}</b> بـ {int(busiest.total_n)} عملية.",
    f"أكثر يوم صرفاً: <b>{core.ar_date(top_sent.date)}</b> بمبلغ {money(top_sent.sent)}.",
]
if top_recv.received > 0:
    notes.append(f"أكثر يوم استلاماً: <b>{core.ar_date(top_recv.date)}</b> بمبلغ {money(top_recv.received)}.")
notes += [
    f"أكبر عملية: {big.direction} {money(big.amount)} ({ui.esc(big.category)}) في {core.ar_date(big.date)}.",
    f"متوسط العملية المرسلة {money(S['avg_sent'])}، ومتوسط المستلمة {money(S['avg_recv'])}.",
]
with st.container(border=True):
    st.markdown(ui.head("bulb", "أبرز النقاط") + ui.insights(notes), unsafe_allow_html=True)

card("trend", "حركة الأموال اليومية", "المستلم للأعلى والمرسل للأسفل مع الصافي التراكمي",
     charts.flow_chart(D, mode))

t1, t2, t3, t4 = st.tabs(["الأيام", "الرسوم", "التصنيفات", "المعاملات"])

with t1:
    M = core.monthly(tx, fees)
    if len(M) > 1:
        card("calendar", "الملخص الشهري", "المستلم والمرسل والصافي لكل شهر وسنة",
             charts.monthly_chart(M, mode))
        mv = pd.DataFrame({"الشهر": M.label, "المستلم": M.received.map(money),
                           "المرسل": M.sent.map(money), "الرسوم": M.fees.map(money),
                           "الصافي": M.net.map(money)})
        with st.container(border=True):
            st.markdown(ui.head("list", "جدول الأشهر") + ui.table(mv), unsafe_allow_html=True)
    card("calendar", "عدد العمليات اليومي", "إرسال واستلام", charts.count_chart(D, mode))
    card("chart", "المبالغ حسب يوم الأسبوع", "",
         charts.weekday_chart(tx, list(core.WEEKDAYS_AR.values()), mode))
    for icon, title, col, n, key in [("up", "أعلى 5 أيام إرسالاً", "sent", "sent_n", "red"),
                                     ("down", "أعلى 5 أيام استلاماً", "received", "received_n", "green")]:
        top = D.nlargest(5, col)
        top = top[top[col] > 0]
        view = pd.DataFrame({"التاريخ": top.date.map(core.ar_date),
                             "المبلغ": top[col].map(money), "العدد": top[n].astype(int)})
        with st.container(border=True):
            st.markdown(ui.head(icon, title) + ui.table(view), unsafe_allow_html=True)

with t2:
    card("pie", "توزيع الرسوم", "دمغة مقابل رسوم الخدمة", charts.fee_donut(fees, mode))
    card("receipt", "الرسوم حسب نوع العملية", "",
         charts.fee_by_category(fees.dropna(subset=["tx_category"]), mode))
    card("trend", "الرسوم اليومية", "", charts.fee_trend(D, mode))
    st.markdown(ui.kpis([
        ("receipt", "رسوم الخدمة", money(S["service"]), "", "amber"),
        ("coins", "رسوم الدمغة", money(S["stamp"]), "", "amber"),
        ("chart", "الرسوم إلى المرسل", f"{S['fee_pct']:.2f}%", "", "blue"),
    ]), unsafe_allow_html=True)

with t3:
    card("up", "المرسل حسب النوع", "", charts.category_chart(tx, "مرسل", mode))
    card("down", "المستلم حسب النوع", "", charts.category_chart(tx, "مستلم", mode))
    card("layers", "توزيع أحجام العمليات", "مقياس لوغاريتمي", charts.size_hist(tx, mode))

with t4:
    v = tx.copy()
    v["التاريخ"] = v.date.map(core.ar_date)
    v["الاتجاه"] = v.direction.map(
        lambda d: f'<span class="pill {({"مستلم": "in", "مرسل": "out"}).get(d, "")}">{d}</span>')
    v["المبلغ"] = v.amount.map(money)
    v["الرسوم"] = v.fees.map(money)
    v["الوصف"] = v.description.map(lambda s: ui.esc(s[:48]))
    view = v.rename(columns={"weekday": "اليوم", "category": "النوع"})[
        ["التاريخ", "اليوم", "الاتجاه", "النوع", "المبلغ", "الرسوم", "الوصف"]]
    with st.container(border=True):
        st.markdown(ui.head("list", "كل المعاملات", f"{len(view)} عملية") +
                    ui.table(view, escape=False), unsafe_allow_html=True)
    csv = tx.rename(columns={"date": "التاريخ", "weekday": "اليوم", "direction": "الاتجاه",
                             "category": "النوع", "amount": "المبلغ", "fees": "الرسوم",
                             "description": "الوصف", "tx_id": "رقم العملية"})
    st.download_button("تحميل CSV", csv.to_csv(index=False).encode("utf-8-sig"),
                       "bankak_transactions.csv", "text/csv")
