"""Dosya, klasör ve ZIP girdilerinden faturaları yükler.

Okunamayan dosyalar işlemi durdurmaz; "OKUNAMADI" kontrol kaydına dönüşür.
"""

from __future__ import annotations

import zipfile
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

from faturakit.models import Invoice, Issue, Severity
from faturakit.parser import InvoiceParseError, parse_invoice

Source = tuple[str, Callable[[], bytes]]
MAX_XML_BYTES = 50 * 1024 * 1024  # tek fatura için makul üst sınır (zip bombasına karşı)


def load_invoices(paths: Iterable[str | Path]) -> tuple[list[Invoice], list[Issue]]:
    invoices: list[Invoice] = []
    issues: list[Issue] = []
    for source, read in _iter_sources(paths, issues):
        try:
            invoices.append(parse_invoice(read(), source=source))
        # RuntimeError: şifreli ZIP üyesi
        except (InvoiceParseError, OSError, zipfile.BadZipFile, RuntimeError) as exc:
            issues.append(_unreadable(source, str(exc)))
    return invoices, issues


def _unreadable(source: str, message: str) -> Issue:
    return Issue(Severity.ERROR, "OKUNAMADI", message, source)


def _iter_sources(paths: Iterable[str | Path], issues: list[Issue]) -> Iterator[Source]:
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            for child in sorted(p for p in path.rglob("*") if p.is_file()):
                yield from _file_sources(child, issues, explicit=False)
        elif path.is_file():
            yield from _file_sources(path, issues, explicit=True)
        else:
            issues.append(_unreadable(str(path), "Dosya veya klasör bulunamadı"))


def _file_sources(path: Path, issues: list[Issue], explicit: bool) -> Iterator[Source]:
    suffix = path.suffix.lower()
    if suffix == ".xml" or (explicit and suffix != ".zip"):
        yield str(path), lambda p=path: _read_limited(p)
    elif suffix == ".zip":
        yield from _zip_sources(path, issues)


def _read_limited(path: Path) -> bytes:
    if path.stat().st_size > MAX_XML_BYTES:
        raise OSError(f"Dosya çok büyük (> {MAX_XML_BYTES // (1024 * 1024)} MB)")
    return path.read_bytes()


def _zip_sources(path: Path, issues: list[Issue]) -> Iterator[Source]:
    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        issues.append(_unreadable(str(path), f"ZIP açılamadı: {exc}"))
        return
    with archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".xml"):
                continue
            source = f"{path}!{info.filename}"
            if info.file_size > MAX_XML_BYTES:
                issues.append(_unreadable(source, "ZIP içindeki dosya çok büyük"))
                continue
            # okuma, load_invoices içindeki try bloğunda yapılır (bozuk CRC vb. yakalanır)
            yield source, lambda i=info: archive.read(i)
