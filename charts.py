"""رسوم Plotly: نظيفة، بلا عناوين داخلية (العناوين في الواجهة) ومناسبة للموبايل."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PAL = {
    "dark": dict(text="#e5e7eb", muted="#9ca3af", grid="rgba(255,255,255,.07)",
                 green="#34d399", red="#f87171", amber="#fbbf24", blue="#60a5fa",
                 violet="#a78bfa", tip="#1f2937"),
    "light": dict(text="#0f172a", muted="#64748b", grid="rgba(15,23,42,.08)",
                  green="#10b981", red="#ef4444", amber="#f59e0b", blue="#3b82f6",
                  violet="#7c3aed", tip="#ffffff"),
}
FONT = "Cairo, Tajawal, sans-serif"


def _style(fig, mode, height=320, legend=True, top=8):
    p = PAL[mode]
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=p["text"], size=12),
        margin=dict(l=4, r=8, t=top + (30 if legend else 0), b=8),
        showlegend=legend, dragmode=False, hovermode="x unified",
        legend=dict(orientation="h", y=1.0, yanchor="bottom", x=0.5, xanchor="center",
                    font=dict(size=12), title=None),
        hoverlabel=dict(bgcolor=p["tip"], font=dict(family=FONT, color=p["text"])),
    )
    fig.update_xaxes(gridcolor=p["grid"], zeroline=False, fixedrange=True,
                     tickfont=dict(color=p["muted"], size=11), automargin=True)
    fig.update_yaxes(gridcolor=p["grid"], zeroline=False, fixedrange=True,
                     tickfont=dict(color=p["muted"], size=11), automargin=True)
    return fig


def _dates(fig):
    fig.update_xaxes(tickformat="%d/%m", nticks=7, title=None)
    return fig


def flow_chart(d: pd.DataFrame, mode):
    p = PAL[mode]
    fig = go.Figure()
    fig.add_bar(x=d.date, y=d.received, name="مستلم", marker_color=p["green"],
                marker_cornerradius=4)
    fig.add_bar(x=d.date, y=-d.sent, name="مرسل", marker_color=p["red"],
                marker_cornerradius=4, customdata=d.sent,
                hovertemplate="%{customdata:,.0f}<extra>مرسل</extra>")
    fig.add_scatter(x=d.date, y=d.cum_net, name="الصافي التراكمي", mode="lines",
                    line=dict(color=p["amber"], width=3),
                    hovertemplate="%{y:,.0f}<extra>الصافي التراكمي</extra>")
    fig.update_layout(barmode="relative", bargap=.25)
    fig.update_yaxes(tickformat="~s", title=None)
    return _dates(_style(fig, mode, 340))


def count_chart(d: pd.DataFrame, mode):
    p = PAL[mode]
    fig = go.Figure()
    fig.add_bar(x=d.date, y=d.sent_n, name="إرسال", marker_color=p["red"],
                marker_cornerradius=4)
    fig.add_bar(x=d.date, y=d.received_n, name="استلام", marker_color=p["green"],
                marker_cornerradius=4)
    fig.update_layout(barmode="stack", bargap=.25)
    fig.update_yaxes(title=None)
    return _dates(_style(fig, mode, 300))


def weekday_chart(tx: pd.DataFrame, order, mode):
    p = PAL[mode]
    g = tx.groupby(["weekday", "direction"]).amount.sum().reset_index()
    fig = px.bar(g, y="weekday", x="amount", color="direction", barmode="group",
                 orientation="h", category_orders={"weekday": order},
                 color_discrete_map={"مستلم": p["green"], "مرسل": p["red"]})
    fig.update_traces(marker_cornerradius=4)
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(tickformat="~s", title=None)
    fig.update_layout(hovermode="closest", bargap=.3)
    return _style(fig, mode, 360)


def fee_donut(fees: pd.DataFrame, mode):
    p = PAL[mode]
    g = fees.groupby("fee_type").amount.sum().reset_index()
    g["fee_type"] = g.fee_type.map({"دمغة": "رسوم الدمغة", "رسوم": "رسوم الخدمة"})
    fig = go.Figure(go.Pie(labels=g.fee_type, values=g.amount, hole=.64, sort=False,
                           marker=dict(colors=[p["amber"], p["blue"]],
                                       line=dict(width=0)),
                           textinfo="percent", textfont=dict(size=13)))
    fig = _style(fig, mode, 300, legend=True)
    fig.update_layout(hovermode="closest",
                      legend=dict(orientation="h", y=-0.02, yanchor="top", x=0.5,
                                  xanchor="center"),
                      margin=dict(l=4, r=4, t=8, b=40))
    return fig


def fee_by_category(fees: pd.DataFrame, mode):
    p = PAL[mode]
    g = fees.groupby("tx_category").amount.sum().sort_values().reset_index()
    fig = px.bar(g, x="amount", y="tx_category", orientation="h",
                 color_discrete_sequence=[p["amber"]])
    fig.update_traces(marker_cornerradius=4)
    fig.update_xaxes(tickformat="~s", title=None)
    fig.update_yaxes(title=None)
    fig.update_layout(hovermode="closest")
    return _style(fig, mode, 300, legend=False)


def category_chart(tx: pd.DataFrame, direction, mode):
    p = PAL[mode]
    color = p["red"] if direction == "مرسل" else p["green"]
    g = (tx[tx.direction == direction].groupby("category").amount.sum()
         .sort_values().reset_index())
    fig = px.bar(g, x="amount", y="category", orientation="h",
                 color_discrete_sequence=[color])
    fig.update_traces(marker_cornerradius=4)
    fig.update_xaxes(tickformat="~s", title=None)
    fig.update_yaxes(title=None)
    fig.update_layout(hovermode="closest")
    return _style(fig, mode, 280, legend=False)


def size_hist(tx: pd.DataFrame, mode):
    p = PAL[mode]
    fig = px.histogram(tx, x="amount", color="direction", nbins=24, log_x=True,
                       color_discrete_map={"مستلم": p["green"], "مرسل": p["red"]})
    fig.update_xaxes(title=None, tickformat="~s")
    fig.update_yaxes(title=None)
    fig.update_layout(hovermode="closest", bargap=.1)
    return _style(fig, mode, 300)


def fee_trend(d: pd.DataFrame, mode):
    p = PAL[mode]
    fig = go.Figure(go.Scatter(x=d.date, y=d.fees, fill="tozeroy", mode="lines",
                               line=dict(color=p["amber"], width=2.5),
                               fillcolor="rgba(251,191,36,.18)",
                               hovertemplate="%{y:,.0f}<extra>الرسوم</extra>"))
    fig.update_yaxes(title=None)
    return _dates(_style(fig, mode, 260, legend=False))
