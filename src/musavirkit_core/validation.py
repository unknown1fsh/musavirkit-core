"""Fatura kontrolleri: KDV hesabı, toplamlar, mükerrer kayıt, VKN/TCKN, dönem."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from decimal import Decimal

from musavirkit_core.models import Invoice, Issue, Party, Severity
from musavirkit_core.tax_ids import is_valid_tax_id

DEFAULT_TOLERANCE = Decimal("0.02")
DUPLICATE_CHECK = "MUKERRER"
PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

InvoiceCheck = Callable[[Invoice, Decimal], list[Issue]]


def is_valid_period(period: str) -> bool:
    return bool(PERIOD_RE.match(period))


def validate(
    invoices: Iterable[Invoice],
    period: str | None = None,
    tolerance: Decimal = DEFAULT_TOLERANCE,
) -> list[Issue]:
    invoices = list(invoices)
    if period is not None and not is_valid_period(period):
        raise ValueError(f"Dönem YYYY-AA biçiminde olmalı: {period!r}")

    issues: list[Issue] = []
    for inv in invoices:
        for check in INVOICE_CHECKS:
            issues.extend(check(inv, tolerance))
        if period is not None:
            issues.extend(_check_period(inv, period))
    issues.extend(_check_duplicates(invoices))
    return issues


def _issue(inv: Invoice, severity: Severity, check: str, message: str) -> Issue:
    return Issue(severity, check, message, inv.source, inv.number)


def _check_kdv(inv: Invoice, tolerance: Decimal) -> list[Issue]:
    issues = []
    for sub in inv.kdv_subtotals:
        if sub.percent is None:
            continue
        expected = (sub.taxable_amount * sub.percent / 100).quantize(Decimal("0.01"))
        if abs(expected - sub.tax_amount) > tolerance:
            issues.append(
                _issue(
                    inv,
                    Severity.ERROR,
                    "KDV_HESAP",
                    f"%{sub.percent} KDV: matrah {sub.taxable_amount} için beklenen "
                    f"{expected}, faturada {sub.tax_amount}",
                )
            )
    return issues


def _check_totals(inv: Invoice, tolerance: Decimal) -> list[Issue]:
    expected = inv.tax_exclusive_amount + inv.tax_total
    if abs(expected - inv.tax_inclusive_amount) > tolerance:
        return [
            _issue(
                inv,
                Severity.ERROR,
                "TOPLAM",
                f"Vergiler hariç ({inv.tax_exclusive_amount}) + vergiler ({inv.tax_total}) = "
                f"{expected}, ancak vergiler dahil tutar {inv.tax_inclusive_amount}",
            )
        ]
    return []


def _check_party_ids(inv: Invoice, _tolerance: Decimal) -> list[Issue]:
    issues = []
    for role, party in (("Satıcı", inv.supplier), ("Alıcı", inv.customer)):
        issues.extend(_check_party(inv, role, party))
    return issues


def _check_party(inv: Invoice, role: str, party: Party) -> list[Issue]:
    if not party.tax_id:
        return [_issue(inv, Severity.ERROR, "VKN_EKSIK", f"{role} VKN/TCKN bilgisi yok")]
    if not is_valid_tax_id(party.tax_id):
        return [
            _issue(
                inv,
                Severity.WARNING,
                "VKN_GECERSIZ",
                f"{role} VKN/TCKN kontrol hanesi tutmuyor: {party.tax_id}",
            )
        ]
    return []


def _check_period(inv: Invoice, period: str) -> list[Issue]:
    if inv.issue_date is None:
        return [_issue(inv, Severity.WARNING, "DONEM", "Fatura tarihi yok")]
    if inv.issue_date.strftime("%Y-%m") != period:
        return [
            _issue(
                inv,
                Severity.WARNING,
                "DONEM",
                f"Fatura tarihi {inv.issue_date.isoformat()} seçilen dönem ({period}) dışında",
            )
        ]
    return []


def _check_duplicates(invoices: list[Invoice]) -> list[Issue]:
    seen_uuid: dict[str, Invoice] = {}
    seen_number: dict[tuple[str | None, str], Invoice] = {}
    issues = []
    for inv in invoices:
        original = None
        if inv.uuid:
            original = seen_uuid.get(inv.uuid.lower())
            seen_uuid.setdefault(inv.uuid.lower(), inv)
        if inv.number:
            key = (inv.supplier.tax_id, inv.number)
            original = original or seen_number.get(key)
            seen_number.setdefault(key, inv)
        if original is not None:
            issues.append(
                _issue(
                    inv,
                    Severity.ERROR,
                    DUPLICATE_CHECK,
                    f"Aynı fatura daha önce okundu: {original.source}",
                )
            )
    return issues


INVOICE_CHECKS: tuple[InvoiceCheck, ...] = (_check_kdv, _check_totals, _check_party_ids)
