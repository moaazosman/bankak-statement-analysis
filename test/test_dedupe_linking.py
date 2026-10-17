import pandas as pd

import core
from synth import d_charge, d_out, d_stamp, make_statement, out_group


def test_paired_doubling_is_collapsed_exactly():
    ch = out_group("2026-10-01", 1, 1000) + out_group("2026-10-02", 2, 2000)
    st = make_statement(ch, doubled=True)
    df, removed, mode, warns = core._dedupe(st.df)
    assert mode == "paired" and removed == 6 and len(df) == 6 and not warns


def test_same_date_and_amount_but_different_ids_are_both_kept():
    ch = out_group("2026-10-01", 1, 5000) + out_group("2026-10-01", 2, 5000)
    st = make_statement(ch)                       # غير مكرر أصلاً
    df, removed, mode, _ = core._dedupe(st.df)
    assert removed == 0 and len(df) == 6


def test_genuine_adjacent_equal_amounts_survive_even_when_statement_is_doubled():
    # عمليتان حقيقيتان متطابقتان في المبلغ واليوم، والكشف مكرر → يبقى 6 أسطر لا 3
    ch = out_group("2026-10-01", 1, 5000) + out_group("2026-10-01", 2, 5000)
    df, removed, mode, _ = core._dedupe(make_statement(ch, doubled=True).df)
    assert mode == "paired" and len(df) == 6
    assert df.tx_id.nunique() == 2


def test_identical_rows_without_id_and_without_balance_are_kept_with_warning():
    ch = [("2026-10-01", "Cash Deposit", None, 100)] * 3
    df = make_statement(ch, with_balance=False).df
    out, removed, mode, warns = core._dedupe(df)
    assert removed == 0 and len(out) == 3 and warns   # لا دليل → لا حذف بصمت


def test_identical_rows_without_id_but_moving_balance_are_real_and_kept():
    ch = [("2026-10-01", "Cash Deposit", None, 100)] * 3
    out, removed, _, warns = core._dedupe(make_statement(ch).df)
    assert removed == 0 and len(out) == 3 and not warns


def test_partial_mismatch_does_not_collapse_pairs_blindly():
    ch = out_group("2026-10-01", 1, 1000) + out_group("2026-10-02", 2, 2000) + out_group("2026-10-03", 3, 3000)
    st = make_statement(ch, doubled=True)
    df = st.df.copy()
    df.loc[1, "debit"] = 999.0                     # زوج واحد غير متطابق
    out, removed, mode, warns = core._dedupe(df)
    assert mode != "paired"
    assert any("غير متطابق" in w for w in warns)
    assert len(out) >= len(df) - removed


def test_polluted_description_still_dedupes_by_amounts_and_id():
    ch = out_group("2026-10-01", 1, 1000)
    st = make_statement(ch, doubled=True)
    st.df.loc[1, "description"] += " stray words"   # وصف مختلف قليلاً بين النسختين
    df, removed, mode, _ = core._dedupe(st.df)
    assert mode == "paired" and len(df) == 3


def test_fees_linked_by_id_once():
    st = make_statement(out_group("2026-10-01", 1, 1000, fee=50, stamp=10))
    tx, fees = core.build_transactions(st)
    assert len(tx) == 1 and tx.fees[0] == 60
    assert fees.amount.sum() == 60 and fees.linked.all()
    assert set(fees.fee_type) == {"دمغة", "رسوم"}


def test_duplicate_main_ids_do_not_double_count_fees():
    ch = [("2026-10-01", d_out(1), 1000, None), ("2026-10-01", d_out(1, "2"), 500, None),
          ("2026-10-01", d_charge(1), 50, None), ("2026-10-01", d_stamp(1), 10, None)]
    tx, fees = core.build_transactions(make_statement(ch))
    assert tx.fees.sum() == 60                      # لا 120
    assert core.summarize(tx, fees)["fees"] == 60
    assert any("يتكرر" in a["text"] for a in core.audit(make_statement(ch), tx, fees))


def test_unlinked_fee_is_kept_in_totals_and_reported():
    ch = out_group("2026-10-01", 1, 1000) + [("2026-10-02", d_stamp(99), 10, None)]
    st = make_statement(ch)
    tx, fees = core.build_transactions(st)
    assert core.summarize(tx, fees)["fees"] == 70
    assert (~fees.linked).sum() == 1
    assert any("بلا معاملة" in a["text"] for a in core.audit(st, tx, fees))
    # الفلترة حسب التصنيف لا تُخفي الرسوم غير المرتبطة
    only_other = tx[tx.category == "لا يوجد"]
    assert (~core.filter_fees(fees, only_other).linked).sum() == 1


def test_fees_follow_category_filter():
    ch = out_group("2026-10-01", 1, 1000) + [("2026-10-02", "Prepaid Payment # 20188130002,Transfer ref.#Zain Prepaid 919", 100, None)]
    tx, fees = core.build_transactions(make_statement(ch))
    sub = tx[tx.category == "شحن رصيد زين"]
    assert core.filter_fees(fees, sub).amount.sum() == 0   # رسوم التحويل لا تنتمي لشحن زين


def test_missing_id_main_tx_reported():
    ch = [("2026-10-01", "Funds Transfer - MB no id", 100, None)]
    st = make_statement(ch)
    tx, fees = core.build_transactions(st)
    assert any("بلا معرّف" in a["text"] for a in core.audit(st, tx, fees))


def test_classification_kinds_and_categories():
    cases = {
        "Stamp Duty - Funds Transfer - MB #20188130001": ("دمغة", "تحويل بنكك"),
        "Charges - MB.P2P #20188130001 , Transfer ref.#Other Bank Transfer 15": ("رسوم", "تحويل لبنك آخر"),
        "20188130001 Bankak Fees Transfer ref.#Esali 2026": ("رسوم", "إيصالي (فواتير)"),
        "Bankak Fees - Prepaid Payment #20188130001 , Transfer ref.#Zain Prepaid 9": ("رسوم", "شحن رصيد زين"),
        "bankak sudani # 20188130001,Transfer ref.#SudaniTopUp 1": ("معاملة", "شحن رصيد سوداني"),
        "20188130001 Bankak Esaly Transfer ref.#Esali 2026": ("معاملة", "إيصالي (فواتير)"),
        "MB.P2P # 20188130001,Transfer ref.#Other Bank Transfer 15": ("معاملة", "تحويل لبنك آخر"),
        "TRF EBS BBAN # 20188130001,Transfer ref.3": ("معاملة", "تحويل عبر EBS"),
        "Funds Transfer - MB # 20188130001,Transfer": ("معاملة", "تحويل بنكك"),
        "ATM Withdrawal 5000": ("معاملة", "أخرى"),
    }
    for desc, (kind, cat) in cases.items():
        assert core._kind(desc) == kind, desc
        assert core._category(desc) == cat, desc


def test_unknown_category_and_undefined_direction_are_flagged():
    st = make_statement([("2026-10-01", "ATM Withdrawal", 100, None)])
    st.df.loc[0, "credit"] = 50.0                    # مدين ودائن معاً → غير محدد
    tx, fees = core.build_transactions(st)
    assert tx.direction[0] == core.UNKNOWN
    S = core.summarize(tx, fees)
    assert S["sent"] == 0 and S["received"] == 0 and S["unknown_n"] == 1
    texts = " ".join(a["text"] for a in core.audit(st, tx, fees))
    assert "غير محدد" in texts and "أخرى" in texts


def _repeat(df, copies):
    """يكرر كل سطر copies[i] مرة (محاكاة نسخ مطبوعة متفاوتة كما في كشوف بنكك)."""
    import pandas as pd
    rows = [r for (_, r), k in zip(df.iterrows(), copies) for _ in range(k)]
    return pd.DataFrame(rows).reset_index(drop=True)


def test_triple_copies_then_single_rows_like_real_statement():
    ch = out_group("2026-10-01", 1, 1000) + out_group("2026-10-02", 2, 2000)
    base = make_statement(ch).df
    df = _repeat(base, [3, 3, 3, 1, 1, 1])
    out, removed, mode, warns = core._dedupe(df)
    assert len(out) == 6 and removed == 6 and not warns


def test_two_real_transactions_same_amount_without_id_are_kept_via_balance():
    # عمليتان حقيقيتان 5000 بلا معرّف: الرصيد يتحرك بينهما فلا تُدمجان
    ch = [("2026-10-01", "Cash Deposit", None, 5000), ("2026-10-01", "Cash Deposit", None, 5000)]
    df = make_statement(ch).df
    out, removed, mode, warns = core._dedupe(df)
    assert len(out) == 2 and removed == 0 and not warns


def test_printed_copies_without_id_are_collapsed_when_balance_does_not_move():
    ch = [("2026-10-01", "Cash Deposit", None, 5000)]
    df = _repeat(make_statement(ch).df, [3])
    out, removed, _, warns = core._dedupe(df)
    assert len(out) == 1 and removed == 2 and not warns


def test_same_id_but_different_balance_is_kept_with_warning():
    df = _repeat(make_statement([("2026-10-01", d_out(1), 1000, None)]).df, [2])
    df.loc[1, "balance"] += 1000
    out, removed, _, warns = core._dedupe(df)
    assert len(out) == 2 and removed == 0 and any("رصيد مختلف" in w for w in warns)


def test_real_twins_with_ids_survive_triple_printing():
    # عمليتان حقيقيتان بنفس المبلغ واليوم وبمعرّفين مختلفين، كل منهما مطبوعة 3 مرات
    ch = out_group("2026-10-01", 1, 5000) + out_group("2026-10-01", 2, 5000)
    df = _repeat(make_statement(ch).df, [3] * 6)
    out, removed, _, _ = core._dedupe(df)
    tx, fees = core.build_transactions(core.Statement(df=out))
    assert len(out) == 6 and tx.amount.tolist() == [5000, 5000]
    assert core.summarize(tx, fees)["sent"] == 10000
