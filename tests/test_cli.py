from openpyxl import load_workbook
from ubl_builder import build

from faturakit.cli import main


def test_cli_converts_folder(tmp_path, capsys):
    src = tmp_path / "faturalar"
    src.mkdir()
    (src / "a.xml").write_bytes(build())
    out = tmp_path / "rapor.xlsx"

    code = main([str(src), "-o", str(out), "--vkn", "1234567890", "--donem", "2026-10"])

    assert code == 0
    assert out.exists()
    assert load_workbook(out)["Faturalar"].max_row == 2
    printed = capsys.readouterr().out
    assert "1 fatura" in printed


def test_cli_returns_1_when_errors_found(tmp_path):
    (tmp_path / "a.xml").write_bytes(build(tax_inclusive="999.00"))
    out = tmp_path / "r.xlsx"

    assert main([str(tmp_path / "a.xml"), "-o", str(out)]) == 1
    assert out.exists()


def test_cli_rejects_bad_period(tmp_path, capsys):
    (tmp_path / "a.xml").write_bytes(build())
    code = main([str(tmp_path), "--donem", "2026/10", "-o", str(tmp_path / "r.xlsx")])
    assert code == 2
