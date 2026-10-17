import pandas as pd

import core
from synth import d_in, make_statement, out_group


def _stmt():
    ch = [("2026-12-30", d_in(1), None, 10000)]
    ch += out_group("2026-12-31", 2, 3000, fee=50, stamp=10)
    ch += out_group("2027-01-02", 3, 1000, fee=100, stamp=10)
    ch += [("2027-01-02", d_in(4), None, 500)]
    return make_statement(ch)


def test_summary_numbers_by_hand():
    tx, fees = core.build_transactions(_stmt())
    S = core.summarize(tx, fees)
    assert S["received"] == 10500 and S["received_n"] == 2
    assert S["sent"] == 4000 and S["sent_n"] == 2
    assert S["fees"] == 170 and S["stamp"] == 20 and S["service"] == 150
    assert S["net"] == 10500 - 4000 - 170
    assert abs(S["fee_pct"] - 170 / 4000 * 100) < 1e-9
    assert S["avg_sent"] == 2000 and S["avg_recv"] == 5250


def test_net_equals_balance_change():
    st = _stmt()
    tx, fees = core.build_transactions(st)
    S = core.summarize(tx, fees)
    rec = core.reconcile(st.df)
    assert rec["ok"] and rec["closing"] - rec["opening"] == S["net"]


def test_daily_zero_fills_gaps_and_cumulates():
    tx, fees = core.build_transactions(_stmt())
    d = core.daily(tx, fees)
    assert len(d) == 4                                   # 30,31 ديسمبر و1,2 يناير (1 يناير بلا حركة)
    assert d.loc[d.date == "2027-01-01", "total_n"].iloc[0] == 0
    assert d.net.sum() == d.cum_net.iloc[-1] == 10500 - 4000 - 170
    assert d.sent_n.sum() == 2 and d.received_n.sum() == 2


def test_monthly_splits_year_boundary_with_year_in_label():
    tx, fees = core.build_transactions(_stmt())
    m = core.monthly(tx, fees)
    assert list(m.label) == ["ديسمبر 2026", "يناير 2027"]
    assert list(m.received) == [10000, 500] and list(m.sent) == [3000, 1000]
    assert list(m.fees) == [60, 110]
    assert list(m.net) == [10000 - 3000 - 60, 500 - 1000 - 110]


def test_only_received_has_no_sent_columns_error():
    st = make_statement([("2026-10-01", d_in(1), None, 100)])
    tx, fees = core.build_transactions(st)
    assert fees.empty
    S = core.summarize(tx, fees)
    assert S["sent"] == 0 and S["fees"] == 0 and S["fee_pct"] == 0
    assert core.daily(tx, fees).sent.sum() == 0
    assert core.monthly(tx, fees).sent.sum() == 0


def test_empty_inputs_do_not_crash():
    st = make_statement([("2026-10-01", d_in(1), None, 100)])
    tx, fees = core.build_transactions(st)
    e = tx.iloc[0:0]
    S = core.summarize(e, fees.iloc[0:0])
    assert S["received"] == 0 and S["avg_sent"] == 0
    assert core.daily(e, fees.iloc[0:0]).empty


def test_reconcile_detects_balance_chain_break():
    st = _stmt()
    st.df.loc[3, "balance"] += 777
    rec = core.reconcile(st.df)
    assert not rec["ok"] and rec["breaks"] >= 1
    assert any("فشلت" in a["text"] for a in core.audit(st, *core.build_transactions(st)))


def test_reconcile_ascending_order_supported():
    st = _stmt()
    asc = st.df.iloc[::-1].reset_index(drop=True)
    rec = core.reconcile(asc)
    assert rec["ok"] and rec["orientation"] == "asc"


def test_reconcile_unavailable_without_balances():
    st = make_statement([("2026-10-01", d_in(1), None, 100)], with_balance=False)
    assert core.reconcile(st.df)["available"] is False


def test_nonzero_opening_balance_is_inferred():
    st = make_statement([("2026-10-01", d_in(1), None, 100)] + out_group("2026-10-02", 2, 40, 5, 1), opening=1000)
    rec = core.reconcile(st.df)
    assert rec["ok"] and rec["opening"] == 1000 and rec["closing"] == 1000 + 100 - 46


def test_ar_date_has_year():
    assert core.ar_date(pd.Timestamp("2026-10-12")) == "12 أكتوبر 2026"
