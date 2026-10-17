import pytest

pytest.importorskip("plotly")

import charts  # noqa: E402
import core  # noqa: E402
from synth import d_in, make_statement, out_group  # noqa: E402


def _data():
    ch = [("2026-10-01", d_in(1), None, 9000)] + out_group("2026-10-02", 2, 1000)
    tx, fees = core.build_transactions(make_statement(ch))
    return tx, fees, core.daily(tx, fees), core.monthly(tx, fees)


def test_all_charts_build_with_data_in_both_themes():
    tx, fees, d, m = _data()
    for mode in ("dark", "light"):
        for fig in (charts.flow_chart(d, mode), charts.count_chart(d, mode),
                    charts.weekday_chart(tx, list(core.WEEKDAYS_AR.values()), mode),
                    charts.fee_donut(fees, mode), charts.fee_by_category(fees.dropna(subset=["tx_category"]), mode),
                    charts.category_chart(tx, "مرسل", mode), charts.category_chart(tx, "مستلم", mode),
                    charts.size_hist(tx, mode), charts.fee_trend(d, mode), charts.monthly_chart(m, mode)):
            assert fig.data is not None


def test_flow_chart_directions_and_totals():
    _, _, d, _ = _data()
    fig = charts.flow_chart(d, "dark")
    recv, sent, cum = fig.data
    assert sum(recv.y) == 9000 and sum(sent.y) == -1000       # المرسل للأسفل
    assert cum.y[-1] == 9000 - 1000 - 60


def test_charts_survive_empty_data():
    tx, fees, d, m = _data()
    e_tx, e_fees, e_d, e_m = tx.iloc[0:0], fees.iloc[0:0], d.iloc[0:0], m.iloc[0:0]
    for mode in ("dark", "light"):
        for fig in (charts.flow_chart(e_d, mode), charts.count_chart(e_d, mode),
                    charts.weekday_chart(e_tx, [], mode), charts.fee_donut(e_fees, mode),
                    charts.fee_by_category(e_fees, mode), charts.category_chart(e_tx, "مرسل", mode),
                    charts.size_hist(e_tx, mode), charts.fee_trend(e_d, mode),
                    charts.monthly_chart(e_m, mode)):
            assert fig is not None
