"""رسوم Plotly بتصميم داكن حديث."""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

BG = "rgba(0,0,0,0)"
GREEN, RED, AMBER, BLUE, VIOLET = "#34d399", "#f87171", "#fbbf24", "#60a5fa", "#a78bfa"
FONT = dict(family="Cairo, Tajawal, sans-serif", color="#e5e7eb")
SEQ = [BLUE, VIOLET, GREEN, AMBER, RED, "#f472b6", "#2dd4bf"]


def _style(fig, height=380, legend=True):
    fig.update_layout(
        height=height, paper_bgcolor=BG, plot_bgcolor=BG, font=FONT,
        margin=dict(l=10, r=10, t=40, b=10), showlegend=legend,
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
        hoverlabel=dict(font=dict(family="Cairo, sans-serif")),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,.06)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,.06)", zeroline=False)
    return fig


def flow_chart(d: pd.DataFrame):
    fig = go.Figure()
    fig.add_bar(x=d.date, y=d.received, name="مستلم", marker_color=GREEN)
    fig.add_bar(x=d.date, y=-d.sent, name="مرسل", marker_color=RED,
                customdata=d.sent, hovertemplate="%{customdata:,.0f}<extra>مرسل</extra>")
    fig.add_scatter(x=d.date, y=d.cum_net, name="صافي تراكمي", mode="lines+markers",
                    line=dict(color=AMBER, width=3, shape="spline"))
    fig.update_layout(barmode="relative", title="حركة الأموال اليومية والصافي التراكمي")
    return _style(fig, 420)


def weekday_chart(tx: pd.DataFrame, order):
    g = tx.groupby(["weekday", "direction"]).amount.sum().reset_index()
    fig = px.bar(g, x="weekday", y="amount", color="direction", barmode="group",
                 category_orders={"weekday": order},
                 color_discrete_map={"مستلم": GREEN, "مرسل": RED},
                 labels={"weekday": "", "amount": "المبلغ", "direction": ""},
                 title="المبالغ حسب يوم الأسبوع")
    return _style(fig)


def count_chart(d: pd.DataFrame):
    fig = go.Figure()
    fig.add_bar(x=d.date, y=d.sent_n, name="عمليات إرسال", marker_color=RED)
    fig.add_bar(x=d.date, y=d.received_n, name="عمليات استلام", marker_color=GREEN)
    fig.update_layout(barmode="stack", title="عدد العمليات اليومي")
    return _style(fig)


def fee_donut(fees: pd.DataFrame):
    g = fees.groupby("fee_type").amount.sum().reset_index()
    g["fee_type"] = g.fee_type.map({"دمغة": "رسوم الدمغة", "رسوم": "رسوم الخدمة"})
    fig = go.Figure(go.Pie(labels=g.fee_type, values=g.amount, hole=.62,
                           marker=dict(colors=[AMBER, BLUE]), textinfo="percent+label"))
    fig.update_layout(title="توزيع الرسوم")
    return _style(fig, 340, legend=False)


def fee_by_category(fees: pd.DataFrame):
    g = fees.groupby("tx_category").amount.sum().sort_values().reset_index()
    fig = px.bar(g, x="amount", y="tx_category", orientation="h",
                 labels={"amount": "الرسوم", "tx_category": ""},
                 title="الرسوم حسب نوع العملية", color_discrete_sequence=[AMBER])
    return _style(fig, 340, legend=False)


def category_chart(tx: pd.DataFrame, direction: str, color: str):
    g = (tx[tx.direction == direction].groupby("category").amount.sum()
         .sort_values().reset_index())
    fig = px.bar(g, x="amount", y="category", orientation="h",
                 labels={"amount": "المبلغ", "category": ""},
                 title=f"{direction}: حسب النوع", color_discrete_sequence=[color])
    return _style(fig, 320, legend=False)


def size_hist(tx: pd.DataFrame):
    fig = px.histogram(tx, x="amount", color="direction", nbins=30, log_x=True,
                       color_discrete_map={"مستلم": GREEN, "مرسل": RED},
                       labels={"amount": "حجم العملية (مقياس لوغاريتمي)", "direction": ""},
                       title="توزيع أحجام العمليات")
    return _style(fig, 340)


def fee_trend(d: pd.DataFrame):
    fig = go.Figure(go.Scatter(x=d.date, y=d.fees, fill="tozeroy", mode="lines",
                               line=dict(color=AMBER, width=2, shape="spline")))
    fig.update_layout(title="الرسوم اليومية")
    return _style(fig, 300, legend=False)
