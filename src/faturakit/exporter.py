"""Faturaları ve kontrol sonuçlarını Excel çalışma kitabına aktarır."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from faturakit.models import ZERO, Invoice, Issue, Severity
from faturakit.validation import DUPLICATE_CHECK

MONEY_FORMAT = "#,##0.00"
DATE_FORMAT = "DD.MM.YYYY"
HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
ERROR_FILL = PatternFill("solid", fgColor="F8CBAD")
WARNING_FILL = PatternFill("solid", fgColor="FFE699")

NO_DIRECTION = "-"

INVOICE_COLUMNS = [
    "Yön", "Fatura No", "ETTN", "Tarih", "Senaryo", "Tip", "Para Birimi",
    "Satıcı VKN/TCKN", "Satıcı Unvan", "Alıcı VKN/TCKN", "Alıcı Unvan",
    "Mal/Hizmet Toplam", "İskonto", "Vergiler Hariç", "Toplam KDV", "Toplam Vergi",
    "Vergiler Dahil", "Tevkifat", "Ödenecek", "Dosya",
]
INVOICE_MONEY_COLUMNS = {
    "Mal/Hizmet Toplam", "İskonto", "Vergiler Hariç", "Toplam KDV", "Toplam Vergi",
    "Vergiler Dahil", "Tevkifat", "Ödenecek",
}
KDV_LINE_COLUMNS = ["Yön", "Fatura No", "Tarih", "Karşı Taraf", "KDV Oranı (%)", "Matrah", "KDV"]
KDV_SUMMARY_COLUMNS = ["Yön", "KDV Oranı (%)", "Fatura Sayısı", "Matrah", "KDV"]
ISSUE_COLUMNS = ["Seviye", "Kontrol", "Fatura No", "Dosya", "Açıklama"]


def direction(inv: Invoice, own_tax_id: str | None) -> str:
    """Kendi VKN'sine göre faturanın satış mı alış mı olduğunu bulur."""
    if not own_tax_id:
        return NO_DIRECTION
    if inv.supplier.tax_id == own_tax_id:
        return "Satış"
    if inv.customer.tax_id == own_tax_id:
        return "Alış"
    return NO_DIRECTION


def export_excel(
    invoices: Sequence[Invoice],
    issues: Sequence[Issue],
    path: str | Path,
    own_tax_id: str | None = None,
) -> Path:
    wb = Workbook()
    _write_invoices(wb.active, invoices, own_tax_id)
    _write_kdv_lines(wb.create_sheet("KDV Dağılımı"), invoices, own_tax_id)
    # Mükerrer faturalar listelenir ama KDV toplamlarını şişirmemesi için özete katılmaz.
    duplicate_sources = {i.source for i in issues if i.check == DUPLICATE_CHECK}
    unique = [inv for inv in invoices if inv.source not in duplicate_sources]
    _write_kdv_summary(wb.create_sheet("KDV Özeti"), unique, own_tax_id)
    _write_issues(wb.create_sheet("Kontroller"), issues)
    out = Path(path)
    wb.save(out)
    return out


def _num(value: Decimal | None) -> float | None:
    # Excel'in Decimal tipi yok; hesaplar Decimal ile yapılır, yalnızca yazarken float'a çevrilir.
    return None if value is None else float(value)


def _counterparty(inv: Invoice, side: str) -> str | None:
    party = inv.customer if side != "Alış" else inv.supplier
    return party.name


def _write_invoices(ws: Worksheet, invoices: Sequence[Invoice], own: str | None) -> None:
    ws.title = "Faturalar"
    ws.append(INVOICE_COLUMNS)
    for inv in invoices:
        ws.append([
            direction(inv, own), inv.number, inv.uuid, inv.issue_date, inv.profile,
            inv.invoice_type, inv.currency,
            inv.supplier.tax_id, inv.supplier.name, inv.customer.tax_id, inv.customer.name,
            _num(inv.line_extension_amount), _num(inv.allowance_total_amount),
            _num(inv.tax_exclusive_amount), _num(inv.kdv_total), _num(inv.tax_total),
            _num(inv.tax_inclusive_amount), _num(inv.withholding_total),
            _num(inv.payable_amount), inv.source,
        ])
    money_cols = {i + 1 for i, name in enumerate(INVOICE_COLUMNS) if name in INVOICE_MONEY_COLUMNS}
    _format(ws, money_cols=money_cols, date_cols={INVOICE_COLUMNS.index("Tarih") + 1})


def _write_kdv_lines(ws: Worksheet, invoices: Sequence[Invoice], own: str | None) -> None:
    ws.append(KDV_LINE_COLUMNS)
    for inv in invoices:
        side = direction(inv, own)
        for sub in inv.kdv_subtotals:
            ws.append([
                side, inv.number, inv.issue_date, _counterparty(inv, side),
                _num(sub.percent), _num(sub.taxable_amount), _num(sub.tax_amount),
            ])
    _format(ws, money_cols={6, 7}, date_cols={3})


def _write_kdv_summary(ws: Worksheet, invoices: Sequence[Invoice], own: str | None) -> None:
    totals: dict[tuple[str, Decimal], dict[str, Any]] = defaultdict(
        lambda: {"invoices": set(), "taxable": ZERO, "tax": ZERO}
    )
    for idx, inv in enumerate(invoices):
        side = direction(inv, own)
        for sub in inv.kdv_subtotals:
            bucket = totals[(side, sub.percent or ZERO)]
            bucket["invoices"].add(idx)
            bucket["taxable"] += sub.taxable_amount
            bucket["tax"] += sub.tax_amount

    ws.append(KDV_SUMMARY_COLUMNS)
    for (side, rate), b in sorted(totals.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        ws.append([side, _num(rate), len(b["invoices"]), _num(b["taxable"]), _num(b["tax"])])
    _format(ws, money_cols={4, 5}, date_cols=set())


def _write_issues(ws: Worksheet, issues: Sequence[Issue]) -> None:
    ws.append(ISSUE_COLUMNS)
    if not issues:
        ws.append(["Sorun bulunamadı"])
    ordered = sorted(issues, key=lambda i: (i.severity is not Severity.ERROR, i.source, i.check))
    for issue in ordered:
        ws.append([issue.severity.value, issue.check, issue.invoice_number, issue.source, issue.message])
        fill = ERROR_FILL if issue.severity is Severity.ERROR else WARNING_FILL
        ws.cell(row=ws.max_row, column=1).fill = fill
    _format(ws, money_cols=set(), date_cols=set())


def _format(ws: Worksheet, money_cols: set[int], date_cols: set[int]) -> None:
    for cell in ws[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
    ws.freeze_panes = "A2"
    if ws.max_row > 1:
        ws.auto_filter.ref = ws.dimensions
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            if cell.column in money_cols:
                cell.number_format = MONEY_FORMAT
            elif cell.column in date_cols:
                cell.number_format = DATE_FORMAT
    for col_idx, column in enumerate(ws.columns, start=1):
        width = max((len(str(c.value)) for c in column if c.value is not None), default=8)
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max(width + 2, 10), 60)
