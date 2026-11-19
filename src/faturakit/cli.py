"""Komut satırı: faturakit <dosya/klasör/zip ...> -o rapor.xlsx [--vkn ...] [--donem YYYY-AA]"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation

from faturakit import __version__
from faturakit.exporter import export_excel
from faturakit.loader import load_invoices
from faturakit.models import Severity
from faturakit.validation import DEFAULT_TOLERANCE, is_valid_period, validate

EXIT_OK, EXIT_ISSUES, EXIT_USAGE = 0, 1, 2


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="faturakit",
        description="e-Fatura / e-Arşiv XML dosyalarını kontrol edip Excel'e aktarır.",
    )
    p.add_argument("girdiler", nargs="+", help="XML dosyası, ZIP arşivi veya klasör")
    p.add_argument("-o", "--cikti", default="faturalar.xlsx", help="Excel dosyası (varsayılan: faturalar.xlsx)")
    p.add_argument("--vkn", help="Kendi VKN/TCKN'niz: faturalar Satış/Alış olarak ayrılır")
    p.add_argument("--donem", help="Beklenen dönem, YYYY-AA (ör. 2026-10)")
    p.add_argument(
        "--tolerans",
        default=str(DEFAULT_TOLERANCE),
        help=f"Kuruş yuvarlama toleransı (varsayılan: {DEFAULT_TOLERANCE})",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.donem and not is_valid_period(args.donem):
        print(f"Hata: --donem YYYY-AA biçiminde olmalı (ör. 2026-10), verilen: {args.donem}", file=sys.stderr)
        return EXIT_USAGE
    try:
        tolerance = Decimal(args.tolerans)
    except InvalidOperation:
        print(f"Hata: --tolerans sayı olmalı, verilen: {args.tolerans}", file=sys.stderr)
        return EXIT_USAGE

    invoices, load_issues = load_invoices(args.girdiler)
    issues = load_issues + validate(invoices, period=args.donem, tolerance=tolerance)
    try:
        out = export_excel(invoices, issues, args.cikti, own_tax_id=args.vkn)
    except PermissionError:
        print(f"Hata: {args.cikti} yazılamadı (dosya Excel'de açık olabilir)", file=sys.stderr)
        return EXIT_USAGE

    errors = sum(1 for i in issues if i.severity is Severity.ERROR)
    warnings = len(issues) - errors
    print(f"{len(invoices)} fatura okundu, {errors} hata, {warnings} uyarı -> {out}")
    return EXIT_ISSUES if errors else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
