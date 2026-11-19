"""Testler için UBL-TR fatura XML'i üreten yardımcı."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Sub:
    taxable: str
    amount: str
    percent: str
    code: str = "0015"
    name: str = "KDV"


@dataclass
class Spec:
    number: str = "ABC2026000000001"
    uuid: str = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    issue_date: str = "2026-10-15"
    profile: str = "TICARIFATURA"
    invoice_type: str = "SATIS"
    currency: str = "TRY"
    supplier_id: str | None = "1234567890"
    supplier_scheme: str = "VKN"
    supplier_name: str = "Örnek Yazılım A.Ş."
    customer_id: str | None = "10000000146"
    customer_scheme: str = "TCKN"
    customer_first: str = "Ayşe"
    customer_family: str = "Yılmaz"
    line_extension: str = "1000.00"
    allowance: str = "0.00"
    tax_exclusive: str = "1000.00"
    tax_inclusive: str = "1200.00"
    payable: str = "1200.00"
    subtotals: list[Sub] = field(default_factory=lambda: [Sub("1000.00", "200.00", "20")])
    withholding: list[Sub] = field(default_factory=list)


def _party_id(tax_id: str | None, scheme: str) -> str:
    if tax_id is None:
        return ""
    return (
        "<cac:PartyIdentification>"
        f'<cbc:ID schemeID="{scheme}">{tax_id}</cbc:ID>'
        "</cac:PartyIdentification>"
    )


def _subtotal(s: Sub, cur: str) -> str:
    return (
        "<cac:TaxSubtotal>"
        f'<cbc:TaxableAmount currencyID="{cur}">{s.taxable}</cbc:TaxableAmount>'
        f'<cbc:TaxAmount currencyID="{cur}">{s.amount}</cbc:TaxAmount>'
        f"<cbc:Percent>{s.percent}</cbc:Percent>"
        "<cac:TaxCategory><cac:TaxScheme>"
        f"<cbc:Name>{s.name}</cbc:Name><cbc:TaxTypeCode>{s.code}</cbc:TaxTypeCode>"
        "</cac:TaxScheme></cac:TaxCategory>"
        "</cac:TaxSubtotal>"
    )


def _total(tag: str, subs: list[Sub], cur: str) -> str:
    if not subs:
        return ""
    total = sum(float(s.amount) for s in subs)
    inner = "".join(_subtotal(s, cur) for s in subs)
    return f'<cac:{tag}><cbc:TaxAmount currencyID="{cur}">{total:.2f}</cbc:TaxAmount>{inner}</cac:{tag}>'


def build(spec: Spec | None = None, **overrides) -> bytes:
    s = spec or Spec()
    for key, value in overrides.items():
        setattr(s, key, value)
    cur = s.currency
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
<cbc:UBLVersionID>2.1</cbc:UBLVersionID>
<cbc:CustomizationID>TR1.2</cbc:CustomizationID>
<cbc:ProfileID>{s.profile}</cbc:ProfileID>
<cbc:ID>{s.number}</cbc:ID>
<cbc:CopyIndicator>false</cbc:CopyIndicator>
<cbc:UUID>{s.uuid}</cbc:UUID>
<cbc:IssueDate>{s.issue_date}</cbc:IssueDate>
<cbc:InvoiceTypeCode>{s.invoice_type}</cbc:InvoiceTypeCode>
<cbc:DocumentCurrencyCode>{cur}</cbc:DocumentCurrencyCode>
<cac:AccountingSupplierParty><cac:Party>
{_party_id(s.supplier_id, s.supplier_scheme)}
<cac:PartyName><cbc:Name>{s.supplier_name}</cbc:Name></cac:PartyName>
</cac:Party></cac:AccountingSupplierParty>
<cac:AccountingCustomerParty><cac:Party>
{_party_id(s.customer_id, s.customer_scheme)}
<cac:Person><cbc:FirstName>{s.customer_first}</cbc:FirstName><cbc:FamilyName>{s.customer_family}</cbc:FamilyName></cac:Person>
</cac:Party></cac:AccountingCustomerParty>
{_total("TaxTotal", s.subtotals, cur)}
{_total("WithholdingTaxTotal", s.withholding, cur)}
<cac:LegalMonetaryTotal>
<cbc:LineExtensionAmount currencyID="{cur}">{s.line_extension}</cbc:LineExtensionAmount>
<cbc:TaxExclusiveAmount currencyID="{cur}">{s.tax_exclusive}</cbc:TaxExclusiveAmount>
<cbc:TaxInclusiveAmount currencyID="{cur}">{s.tax_inclusive}</cbc:TaxInclusiveAmount>
<cbc:AllowanceTotalAmount currencyID="{cur}">{s.allowance}</cbc:AllowanceTotalAmount>
<cbc:PayableAmount currencyID="{cur}">{s.payable}</cbc:PayableAmount>
</cac:LegalMonetaryTotal>
</Invoice>"""
    return xml.encode("utf-8")
