"""UBL-TR (e-Fatura / e-Arşiv) XML ayrıştırıcı.

Güvenlik: XML'ler dışarıdan gelen dosyalardır; entity genişletme ve dış
kaynak saldırılarına karşı defusedxml kullanılır.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from xml.etree.ElementTree import Element, ParseError

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring

from musavirkit_core.models import ZERO, Invoice, Party, TaxSubtotal

INVOICE_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
NS = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}
TAX_ID_SCHEMES = {"VKN", "TCKN"}


class InvoiceParseError(ValueError):
    """Dosya geçerli bir UBL-TR faturası olarak okunamadı."""


def parse_invoice(data: bytes, source: str) -> Invoice:
    root = _parse_xml(data)
    el = _find_invoice_element(root)
    return Invoice(
        source=source,
        number=_text(el, "cbc:ID"),
        uuid=_text(el, "cbc:UUID"),
        issue_date=_date(_text(el, "cbc:IssueDate")),
        profile=_text(el, "cbc:ProfileID"),
        invoice_type=_text(el, "cbc:InvoiceTypeCode"),
        currency=_text(el, "cbc:DocumentCurrencyCode"),
        supplier=_party(el.find("cac:AccountingSupplierParty/cac:Party", NS)),
        customer=_party(el.find("cac:AccountingCustomerParty/cac:Party", NS)),
        line_extension_amount=_amount(el, "cac:LegalMonetaryTotal/cbc:LineExtensionAmount"),
        allowance_total_amount=_amount(el, "cac:LegalMonetaryTotal/cbc:AllowanceTotalAmount"),
        tax_exclusive_amount=_amount(el, "cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount"),
        tax_inclusive_amount=_amount(el, "cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount"),
        payable_amount=_amount(el, "cac:LegalMonetaryTotal/cbc:PayableAmount"),
        tax_total=_sum_totals(el, "cac:TaxTotal"),
        tax_subtotals=_subtotals(el, "cac:TaxTotal"),
        withholding_total=_sum_totals(el, "cac:WithholdingTaxTotal"),
        withholding_subtotals=_subtotals(el, "cac:WithholdingTaxTotal"),
    )


def _parse_xml(data: bytes) -> Element:
    try:
        return fromstring(data, forbid_dtd=False, forbid_entities=True, forbid_external=True)
    except DefusedXmlException as exc:
        raise InvoiceParseError(f"Güvenli olmayan XML içeriği: {exc}") from exc
    except ParseError as exc:
        raise InvoiceParseError(f"XML okunamadı: {exc}") from exc


def _find_invoice_element(root: Element) -> Element:
    tag = f"{{{INVOICE_NS}}}Invoice"
    for el in root.iter(tag):
        return el
    raise InvoiceParseError("Dosyada UBL-TR <Invoice> öğesi bulunamadı")


def _text(el: Element | None, path: str) -> str | None:
    if el is None:
        return None
    found = el.find(path, NS)
    if found is None or found.text is None:
        return None
    value = found.text.strip()
    return value or None


def _to_decimal(raw: str | None, field: str) -> Decimal:
    if raw is None:
        return ZERO
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise InvoiceParseError(f"Geçersiz tutar ({field}): {raw!r}") from exc


def _amount(el: Element, path: str) -> Decimal:
    return _to_decimal(_text(el, path), path)


def _date(raw: str | None) -> date | None:
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise InvoiceParseError(f"Geçersiz tarih: {raw!r}") from exc


def _party(el: Element | None) -> Party:
    if el is None:
        return Party(tax_id=None, scheme=None, name=None)
    tax_id = scheme = None
    for ident in el.findall("cac:PartyIdentification/cbc:ID", NS):
        id_scheme = (ident.get("schemeID") or "").upper()
        if id_scheme in TAX_ID_SCHEMES and ident.text and ident.text.strip():
            tax_id, scheme = ident.text.strip(), id_scheme
            break
    return Party(tax_id=tax_id, scheme=scheme, name=_party_name(el))


def _party_name(el: Element) -> str | None:
    name = _text(el, "cac:PartyName/cbc:Name")
    if name:
        return name
    parts = [_text(el, "cac:Person/cbc:FirstName"), _text(el, "cac:Person/cbc:FamilyName")]
    joined = " ".join(p for p in parts if p)
    return joined or None


def _sum_totals(el: Element, path: str) -> Decimal:
    return sum((_amount(t, "cbc:TaxAmount") for t in el.findall(path, NS)), ZERO)


def _subtotals(el: Element, path: str) -> list[TaxSubtotal]:
    result = []
    for sub in el.findall(f"{path}/cac:TaxSubtotal", NS):
        percent_raw = _text(sub, "cbc:Percent")
        result.append(
            TaxSubtotal(
                tax_code=_text(sub, "cac:TaxCategory/cac:TaxScheme/cbc:TaxTypeCode"),
                tax_name=_text(sub, "cac:TaxCategory/cac:TaxScheme/cbc:Name"),
                percent=_to_decimal(percent_raw, "Percent") if percent_raw else None,
                taxable_amount=_amount(sub, "cbc:TaxableAmount"),
                tax_amount=_amount(sub, "cbc:TaxAmount"),
            )
        )
    return result
