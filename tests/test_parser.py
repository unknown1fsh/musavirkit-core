from datetime import date
from decimal import Decimal

import pytest
from ubl_builder import Spec, Sub, build

from musavirkit_core.parser import InvoiceParseError, parse_invoice


def test_parses_header_fields():
    inv = parse_invoice(build(), source="a.xml")

    assert inv.source == "a.xml"
    assert inv.number == "ABC2026000000001"
    assert inv.uuid == "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    assert inv.issue_date == date(2026, 10, 15)
    assert inv.profile == "TICARIFATURA"
    assert inv.invoice_type == "SATIS"
    assert inv.currency == "TRY"


def test_parses_parties_company_and_person():
    inv = parse_invoice(build(), source="a.xml")

    assert inv.supplier.tax_id == "1234567890"
    assert inv.supplier.scheme == "VKN"
    assert inv.supplier.name == "Örnek Yazılım A.Ş."
    assert inv.customer.tax_id == "10000000146"
    assert inv.customer.scheme == "TCKN"
    assert inv.customer.name == "Ayşe Yılmaz"


def test_parses_monetary_totals_as_decimal():
    inv = parse_invoice(build(), source="a.xml")

    assert inv.line_extension_amount == Decimal("1000.00")
    assert inv.tax_exclusive_amount == Decimal("1000.00")
    assert inv.tax_inclusive_amount == Decimal("1200.00")
    assert inv.payable_amount == Decimal("1200.00")
    assert inv.tax_total == Decimal("200.00")


def test_parses_multiple_kdv_rates():
    xml = build(
        subtotals=[Sub("500.00", "100.00", "20"), Sub("500.00", "50.00", "10")],
        tax_inclusive="1150.00",
        payable="1150.00",
    )
    inv = parse_invoice(xml, source="a.xml")

    rates = [(s.percent, s.taxable_amount, s.tax_amount) for s in inv.kdv_subtotals]
    assert rates == [
        (Decimal("20"), Decimal("500.00"), Decimal("100.00")),
        (Decimal("10"), Decimal("500.00"), Decimal("50.00")),
    ]
    assert inv.kdv_total == Decimal("150.00")


def test_parses_withholding_tevkifat():
    xml = build(
        invoice_type="TEVKIFAT",
        withholding=[Sub("200.00", "100.00", "50", code="624", name="Yük taşımacılığı")],
        payable="1100.00",
    )
    inv = parse_invoice(xml, source="a.xml")

    assert inv.withholding_total == Decimal("100.00")
    assert inv.withholding_subtotals[0].tax_code == "624"


def test_finds_invoice_inside_envelope():
    inner = build().decode("utf-8").split("?>", 1)[1]
    envelope = f"<Zarf xmlns='urn:ornek'><Icerik>{inner}</Icerik></Zarf>".encode()

    inv = parse_invoice(envelope, source="zarf.xml")
    assert inv.number == "ABC2026000000001"


def test_missing_party_id_is_none():
    inv = parse_invoice(build(spec=Spec(supplier_id=None)), source="a.xml")
    assert inv.supplier.tax_id is None


@pytest.mark.parametrize(
    "data",
    [b"bu bir xml degil", b"<root><child/></root>"],
    ids=["bozuk-xml", "fatura-yok"],
)
def test_invalid_input_raises(data):
    with pytest.raises(InvoiceParseError):
        parse_invoice(data, source="x.xml")


def test_rejects_entity_expansion():
    bomb = b"""<?xml version="1.0"?>
<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;">]>
<Invoice>&lol2;</Invoice>"""
    with pytest.raises(InvoiceParseError):
        parse_invoice(bomb, source="bomb.xml")
