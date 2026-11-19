"""Veri modelleri. Tutarlar her zaman Decimal tutulur (float yuvarlama hatası olmaması için)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum

ZERO = Decimal("0")

KDV_TAX_CODE = "0015"


@dataclass(frozen=True)
class Party:
    tax_id: str | None  # VKN (10 hane) veya TCKN (11 hane)
    scheme: str | None  # "VKN" / "TCKN"
    name: str | None


@dataclass(frozen=True)
class TaxSubtotal:
    tax_code: str | None  # 0015 = KDV, tevkifatta 6xx kodları
    tax_name: str | None
    percent: Decimal | None
    taxable_amount: Decimal
    tax_amount: Decimal


@dataclass
class Invoice:
    source: str  # okunduğu dosya (zip içiyse "arsiv.zip!fatura.xml")
    number: str | None
    uuid: str | None
    issue_date: date | None
    profile: str | None  # TEMELFATURA, TICARIFATURA, EARSIVFATURA ...
    invoice_type: str | None  # SATIS, IADE, TEVKIFAT, ISTISNA ...
    currency: str | None
    supplier: Party
    customer: Party
    line_extension_amount: Decimal = ZERO
    allowance_total_amount: Decimal = ZERO
    tax_exclusive_amount: Decimal = ZERO
    tax_inclusive_amount: Decimal = ZERO
    payable_amount: Decimal = ZERO
    tax_total: Decimal = ZERO
    tax_subtotals: list[TaxSubtotal] = field(default_factory=list)
    withholding_total: Decimal = ZERO
    withholding_subtotals: list[TaxSubtotal] = field(default_factory=list)

    @property
    def kdv_subtotals(self) -> list[TaxSubtotal]:
        return [s for s in self.tax_subtotals if s.tax_code == KDV_TAX_CODE]

    @property
    def kdv_total(self) -> Decimal:
        return sum((s.tax_amount for s in self.kdv_subtotals), ZERO)


class Severity(str, Enum):
    ERROR = "HATA"
    WARNING = "UYARI"


@dataclass(frozen=True)
class Issue:
    severity: Severity
    check: str
    message: str
    source: str
    invoice_number: str | None = None
