import io

import pandas as pd
import streamlit as st

import charts
import core

st.set_page_config(page_title="محلل كشف بنكك", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&display=swap');
html, body, [class*="css"], .stMarkdown, .stDataFrame { font-family:'Cairo',sans-serif; }
.block-container { direction: rtl; padding-top: 2rem; max-width: 1250px; }
h1,h2,h3,p,li,label { text-align: right; }
.hero { background: linear-gradient(135deg,#1e3a8a 0%,#6d28d9 55%,#be185d 100%);
        padding: 28px 32px; border-radius: 22px; margin-bottom: 18px; }
.hero h1 { margin:0; font-weight:800; color:#fff; }
.hero p { margin:6px 0 0; color:#e0e7ff; }
.kpi { background:#111827; border:1px solid rgba(255,255,255,.08); border-radius:18px;
       padding:16px 18px; }
.kpi .l { color:#9ca3af; font-size:.85rem; }
.kpi .v { font-size:1.55rem; font-weight:800; margin-top:2px; }
.kpi .s { color:#6b7280; font-size:.78rem; }
.insight { background:#0f172a; border-right:4px solid #60a5fa; padding:10px 14px;
           border-radius:10px; margin:6px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""<div class="hero"><h1>📊 محلل كشف حساب بنكك</h1>
<p>ارفع كشف الحساب (PDF) واحصل على تحليل كامل للإرسال والاستلام والرسوم وأكثر الأيام نشاطاً — كل الأرقام بالجنيه السوداني.</p></div>""",
            unsafe_allow_html=True)


def money(x):
    return f"{x:,.0f}"


def kpi(col, label, value, sub="", color="#e5e7eb"):
    col.markdown(f'<div class="kpi"><div class="l">{label}</div>'
                 f'<div class="v" style="color:{color}">{value}</div>'
                 f'<div class="s">{sub}</div></div>', unsafe_allow_html=True)


with st.sidebar:
    st.header("⚙️ الإعدادات")
    dedupe = st.toggle("إزالة الأسطر المكررة", value=True,
                       help="كشوف بنكك تكرر كل سطر مرتين؛ هذا الخيار يحسب كل عملية مرة واحدة.")
    st.caption("🔒 الملف يُعالج في الذاكرة فقط ولا يُحفظ.")

up = st.file_uploader("اختر ملف PDF لكشف الحساب", type="pdf")
if not up:
    st.info("ارفع الكشف لبدء التحليل.")
    st.stop()


@st.cache_data(show_spinner="جارٍ قراءة الكشف...")
def load(data: bytes, dd: bool):
    stmt = core.read_statement(io.BytesIO(data), dd)
    tx, fees = core.build_transactions(stmt)
    return stmt, tx, fees


try:
    stmt, tx, fees = load(up.getvalue(), dedupe)
except Exception as e:  # noqa: BLE001
    st.error(f"تعذّرت قراءة الملف: {e}")
    st.stop()

if tx.empty:
    st.warning("لم أجد معاملات في هذا الكشف.")
    st.stop()

with st.sidebar:
    lo, hi = tx.date.min().date(), tx.date.max().date()
    rng = st.date_input("الفترة", (lo, hi), min_value=lo, max_value=hi)
    cats = st.multiselect("نوع العملية", sorted(tx.category.unique()),
                          default=sorted(tx.category.unique()))
if isinstance(rng, tuple) and len(rng) == 2:
    a, b = pd.Timestamp(rng[0]), pd.Timestamp(rng[1])
    tx = tx[(tx.date >= a) & (tx.date <= b) & tx.category.isin(cats)]
    fees = fees[(fees.date >= a) & (fees.date <= b)]
    fees = fees[fees.tx_id.isin(tx.tx_id) | fees.tx_id.isna()]
if tx.empty:
    st.warning("لا توجد بيانات ضمن هذا الفلتر.")
    st.stop()

m = stmt.meta
st.caption(f"👤 {m.get('name','')} · رقم العميل {m.get('customer_no','')} · {m.get('account_type','')} · "
           f"{lo:%Y-%m-%d} → {hi:%Y-%m-%d}"
           + (f" · أُزيل {stmt.duplicates_removed} سطر مكرر" if dedupe else ""))

S = core.summarize(tx, fees)
D = core.daily(tx, fees)

c = st.columns(4)
kpi(c[0], "المستلم", money(S["received"]), f"{S['received_n']} عملية", "#34d399")
kpi(c[1], "المرسل", money(S["sent"]), f"{S['sent_n']} عملية", "#f87171")
kpi(c[2], "الرسوم والدمغة", money(S["fees"]), f"{S['fee_pct']:.2f}% من المرسل", "#fbbf24")
kpi(c[3], "الصافي", money(S["net"]), "مستلم − مرسل − رسوم",
    "#34d399" if S["net"] >= 0 else "#f87171")

st.markdown("### 💡 أبرز النقاط")
busiest = D.loc[D.total_n.idxmax()]
top_sent = D.loc[D.sent.idxmax()]
top_recv = D.loc[D.received.idxmax()]
big = tx.loc[tx.amount.idxmax()]
notes = [
    f"أكثر الأيام نشاطاً: <b>{busiest.date:%d %b}</b> بـ {int(busiest.total_n)} عملية.",
    f"أكثر يوم صرفاً: <b>{top_sent.date:%d %b}</b> بمبلغ {money(top_sent.sent)}.",
]
if top_recv.received > 0:
    notes.append(f"أكثر يوم استلاماً: <b>{top_recv.date:%d %b}</b> بمبلغ {money(top_recv.received)}.")
notes += [
    f"أكبر عملية: {big.direction} {money(big.amount)} ({big.category}) في {big.date:%d %b}.",
    f"متوسط العملية المرسلة {money(S['avg_sent'])} ومتوسط المستلمة {money(S['avg_recv'])}.",
]
for n in notes:
    st.markdown(f'<div class="insight">{n}</div>', unsafe_allow_html=True)

st.plotly_chart(charts.flow_chart(D), use_container_width=True)

t1, t2, t3, t4 = st.tabs(["📅 الأيام", "💸 الرسوم", "🗂️ التصنيفات", "🧾 المعاملات"])

with t1:
    a, b = st.columns(2)
    a.plotly_chart(charts.count_chart(D), use_container_width=True)
    order = list(core.WEEKDAYS_AR.values())
    b.plotly_chart(charts.weekday_chart(tx, order), use_container_width=True)
    x, y = st.columns(2)
    x.markdown("**أعلى 5 أيام إرسالاً**")
    x.dataframe(D.nlargest(5, "sent")[["date", "sent", "sent_n"]]
                .rename(columns={"date": "التاريخ", "sent": "المبلغ", "sent_n": "العدد"}),
                hide_index=True, use_container_width=True)
    y.markdown("**أعلى 5 أيام استلاماً**")
    y.dataframe(D.nlargest(5, "received")[["date", "received", "received_n"]]
                .rename(columns={"date": "التاريخ", "received": "المبلغ", "received_n": "العدد"}),
                hide_index=True, use_container_width=True)

with t2:
    a, b = st.columns(2)
    a.plotly_chart(charts.fee_donut(fees), use_container_width=True)
    b.plotly_chart(charts.fee_by_category(fees.dropna(subset=["tx_category"])),
                   use_container_width=True)
    st.plotly_chart(charts.fee_trend(D), use_container_width=True)
    k = st.columns(3)
    kpi(k[0], "رسوم الخدمة", money(S["service"]))
    kpi(k[1], "رسوم الدمغة", money(S["stamp"]))
    kpi(k[2], "الرسوم إلى المرسل", f"{S['fee_pct']:.2f}%")

with t3:
    a, b = st.columns(2)
    a.plotly_chart(charts.category_chart(tx, "مرسل", "#f87171"), use_container_width=True)
    b.plotly_chart(charts.category_chart(tx, "مستلم", "#34d399"), use_container_width=True)
    st.plotly_chart(charts.size_hist(tx), use_container_width=True)

with t4:
    show = tx.rename(columns={"date": "التاريخ", "weekday": "اليوم", "direction": "الاتجاه",
                              "category": "النوع", "amount": "المبلغ", "fees": "الرسوم",
                              "description": "الوصف", "tx_id": "رقم العملية"})
    st.dataframe(show, hide_index=True, use_container_width=True)
    st.download_button("⬇️ تحميل CSV", show.to_csv(index=False).encode("utf-8-sig"),
                       "bankak_transactions.csv", "text/csv")
