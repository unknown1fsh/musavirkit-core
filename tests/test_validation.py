from decimal import Decimal

from ubl_builder import Spec, Sub, build

from musavirkit_core.models import Severity
from musavirkit_core.parser import parse_invoice
from musavirkit_core.validation import validate


def _inv(source="a.xml", **kw):
    return parse_invoice(build(spec=Spec(), **kw), source=source)


def _checks(issues):
    return sorted(i.check for i in issues)


def test_clean_invoice_has_no_issues():
    assert validate([_inv()]) == []


def test_kdv_calculation_mismatch():
    inv = _inv(subtotals=[Sub("1000.00", "180.00", "20")], tax_inclusive="1180.00")
    issues = validate([inv])
    assert _checks(issues) == ["KDV_HESAP"]
    assert issues[0].severity is Severity.ERROR
    assert issues[0].invoice_number == "ABC2026000000001"


def test_kdv_rounding_within_tolerance_is_ok():
    inv = _inv(subtotals=[Sub("1000.00", "200.01", "20")], tax_inclusive="1200.01")
    assert validate([inv]) == []


def test_total_mismatch():
    inv = _inv(tax_inclusive="1250.00")
    assert _checks(validate([inv])) == ["TOPLAM"]


def test_duplicate_by_uuid_and_by_number():
    a = _inv("a.xml")
    b = _inv("b.xml")  # aynı ETTN, aynı numara
    c = _inv("c.xml", uuid="11111111-2222-3333-4444-555555555555")  # sadece numara aynı

    issues = validate([a, b, c])
    dup = [i for i in issues if i.check == "MUKERRER"]
    assert sorted(i.source for i in dup) == ["b.xml", "c.xml"]


def test_missing_and_invalid_tax_ids():
    missing = _inv(supplier_id=None)
    invalid = _inv("b.xml", uuid="u2", number="ABC2026000000002", customer_id="12345678901")

    issues = validate([missing, invalid])
    assert _checks(issues) == ["VKN_EKSIK", "VKN_GECERSIZ"]
    assert {i.severity for i in issues} == {Severity.ERROR, Severity.WARNING}


def test_period_mismatch():
    inv = _inv(issue_date="2026-09-30")
    assert _checks(validate([inv], period="2026-10")) == ["DONEM"]
    assert validate([inv], period="2026-09") == []


def test_custom_tolerance():
    inv = _inv(subtotals=[Sub("1000.00", "200.05", "20")], tax_inclusive="1200.05")
    assert _checks(validate([inv])) == ["KDV_HESAP"]
    assert validate([inv], tolerance=Decimal("0.10")) == []
