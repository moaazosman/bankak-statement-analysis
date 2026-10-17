import pytest

import core
from synth import FakePage, fake_pdf, row


def _read(*pages, dedupe=False):
    with fake_pdf(*pages):
        return core.read_statement("x.pdf", drop_duplicates=dedupe)


def test_debit_credit_balance_by_column_position():
    st = _read(FakePage([
        row("15-Oct-2026", "Funds Transfer - MB # 20188130001,Transfer ref.1", debit="580,000.00", balance="11,190"),
        row("14-Oct-2026", "TRF EBS BBAN # 20188130002,Transfer ref.2", credit="384,000.00", balance="591,190"),
    ]))
    d = st.df
    assert d.debit[0] == 580000 and d.credit.isna()[0] and d.balance[0] == 11190
    assert d.credit[1] == 384000 and d.debit.isna()[1] and d.balance[1] == 591190
    assert str(d.date[0].date()) == "2026-10-15"


def test_multiline_description_and_transaction_id():
    desc = "Stamp Duty - Prepaid Payment #20488122185 , Transfer ref.#Zain Prepaid 919640534 Transfer ref.#Zain Prepaid 919640534"
    st = _read(FakePage([row("15-Oct-2026", desc, debit="10.00", balance="7,970")]))
    assert st.df.description[0] == desc
    assert st.df.tx_id[0] == "20488122185"      # لا يلتقط رقم الهاتف (9 أرقام)


def test_footer_page_number_is_not_read_as_balance():
    # انحدار: "Page 1" كان يُقرأ كرصيد لآخر سطر في الصفحة
    st = _read(FakePage([row("15-Oct-2026", "Funds Transfer - MB # 20188130001,x", debit="4,000.00")]))
    assert st.df.balance.isna().all()


def test_multipage_uses_columns_from_first_page_header():
    p1 = FakePage([row("02-Oct-2026", "TRF EBS BBAN # 20188130003,Transfer ref.3", credit="500.00", balance="500")], page_no=1)
    p2 = FakePage([row("01-Oct-2026", "Funds Transfer - MB # 20188130004,Transfer ref.4", debit="200.00", balance="300")],
                  header=False, page_no=2)
    st = _read(p1, p2)
    assert list(st.df.page) == [1, 2]
    assert st.df.debit[1] == 200 and st.df.credit.isna()[1]


def test_description_continuation_across_pages_is_attached_with_warning():
    p1 = FakePage([row("02-Oct-2026", "Funds Transfer - MB # 20188130005,Transfer", debit="10.00")])
    cont = [{"text": "ref.999", "x0": 116, "x1": 140, "top": 330.0, "bottom": 338.0}]
    p2 = FakePage([row("01-Oct-2026", "Funds Transfer - MB # 20188130006,x", debit="5.00")], header=False, page_no=2)
    p2.words += cont
    st = _read(p1, p2)
    assert st.df.description[0].endswith("ref.999")
    assert any("مكمّل" in w for w in st.warnings)


def test_invalid_date_is_rejected_and_reported_not_defaulted():
    st = _read(FakePage([
        row("31-Feb-2026", "Funds Transfer - MB # 20188130007,x", debit="10.00"),
        row("01-Oct-2026", "Funds Transfer - MB # 20188130008,x", debit="20.00"),
    ]))
    assert len(st.df) == 1 and len(st.rejected) == 1
    assert st.rejected.debit.iloc[0] == 10
    assert any("تاريخ غير صالح" in w for w in st.warnings)


def test_unknown_month_name_is_rejected():
    st = _read(FakePage([row("01-Xyz-2026", "Funds Transfer - MB # 20188130009,x", debit="1.00"),
                         row("01-Oct-2026", "Funds Transfer - MB # 20188130010,x", debit="2.00")]))
    assert len(st.rejected) == 1


def test_two_values_in_same_column_flagged():
    p = FakePage([row("01-Oct-2026", "Funds Transfer - MB # 20188130011,x", debit="1.00")])
    p.words.append({"text": "2.00", "x0": 326, "x1": 350, "top": 341.0, "bottom": 349.0})
    st = _read(p)
    assert st.df.conflict.iloc[0]
    assert any("أكثر من قيمة" in w for w in st.warnings)


def test_row_without_amount_is_kept_as_nan_not_zero():
    st = _read(FakePage([row("01-Oct-2026", "Funds Transfer - MB # 20188130012,x")]))
    assert st.df.debit.isna().iloc[0] and st.df.credit.isna().iloc[0]


def test_pdf_without_text_raises_clear_error():
    with pytest.raises(ValueError):
        _read(FakePage([], header=False))


def test_corrupt_file_raises_value_error():
    with pytest.raises(ValueError):
        core.read_statement(__import__("io").BytesIO(b"not a pdf"))
