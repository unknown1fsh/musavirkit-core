from decimal import Decimal

from openpyxl import load_workbook
from ubl_builder import Spec, Sub, build

from musavirkit_core.exporter import export_excel
from musavirkit_core.parser import parse_invoice
from musavirkit_core.validation import validate


def _rows(ws):
    return [list(r) for r in ws.iter_rows(values_only=True)]


def test_export_creates_sheets_with_data(tmp_path):
    sale = parse_invoice(
        build(
            spec=Spec(),
            subtotals=[Sub("500.00", "100.00", "20"), Sub("500.00", "50.00", "10")],
            tax_inclusive="1150.00",
            payable="1150.00",
        ),
        source="satis.xml",
    )
    purchase = parse_invoice(
        build(
            spec=Spec(),
            number="XYZ2026000000009",
            uuid="u-alis",
            supplier_id="10000000146",
            supplier_scheme="TCKN",
            customer_id="1234567890",
            customer_scheme="VKN",
            tax_inclusive="1300.00",  # hatalı toplam
        ),
        source="alis.xml",
    )
    issues = validate([sale, purchase])
    out = tmp_path / "rapor.xlsx"

    export_excel([sale, purchase], issues, out, own_tax_id="1234567890")

    wb = load_workbook(out)
    assert wb.sheetnames == ["Faturalar", "KDV Dağılımı", "KDV Özeti", "Kontroller"]

    faturalar = _rows(wb["Faturalar"])
    header = faturalar[0]
    assert header[0] == "Yön"
    by_no = {r[header.index("Fatura No")]: r for r in faturalar[1:]}
    assert by_no["ABC2026000000001"][0] == "Satış"
    assert by_no["XYZ2026000000009"][0] == "Alış"
    assert by_no["ABC2026000000001"][header.index("Toplam KDV")] == 150.0

    ozet = _rows(wb["KDV Özeti"])
    assert ozet[0][:5] == ["Yön", "KDV Oranı (%)", "Fatura Sayısı", "Matrah", "KDV"]
    assert ["Satış", 10.0, 1, 500.0, 50.0] in [r[:5] for r in ozet[1:]]
    assert ["Satış", 20.0, 1, 500.0, 100.0] in [r[:5] for r in ozet[1:]]
    assert ["Alış", 20.0, 1, 1000.0, 200.0] in [r[:5] for r in ozet[1:]]

    kontroller = _rows(wb["Kontroller"])
    assert any(r[1] == "TOPLAM" for r in kontroller[1:])


def test_duplicates_are_excluded_from_kdv_summary(tmp_path):
    first = parse_invoice(build(), source="a.xml")
    dup = parse_invoice(build(), source="b.xml")
    out = tmp_path / "r.xlsx"

    export_excel([first, dup], validate([first, dup]), out)

    ozet = _rows(load_workbook(out)["KDV Özeti"])
    assert [r[:5] for r in ozet[1:]] == [["-", 20, 1, 1000, 200]]


def test_export_without_own_tax_id_has_no_direction(tmp_path):
    inv = parse_invoice(build(), source="a.xml")
    out = tmp_path / "r.xlsx"

    export_excel([inv], [], out)

    rows = _rows(load_workbook(out)["Faturalar"])
    assert rows[1][0] == "-"
    assert _rows(load_workbook(out)["Kontroller"])[1][0] == "Sorun bulunamadı"


def test_amount_cells_use_number_format(tmp_path):
    inv = parse_invoice(build(), source="a.xml")
    out = tmp_path / "r.xlsx"
    export_excel([inv], [], out)

    ws = load_workbook(out)["Faturalar"]
    header = [c.value for c in ws[1]]
    cell = ws.cell(row=2, column=header.index("Vergiler Dahil") + 1)
    assert cell.value == float(Decimal("1200.00"))
    assert cell.number_format == "#,##0.00"
