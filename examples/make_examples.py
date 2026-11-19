"""Demo için örnek UBL-TR faturaları üretir: python examples/make_examples.py"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

from ubl_builder import Sub, build  # noqa: E402

out = ROOT / "examples" / "ornek-faturalar"
out.mkdir(parents=True, exist_ok=True)

(out / "01-satis-temel.xml").write_bytes(build())
(out / "02-satis-iki-oran.xml").write_bytes(
    build(
        number="ABC2026000000002",
        uuid="2b1e0c4a-1111-4c2e-9b7a-000000000002",
        subtotals=[Sub("500.00", "100.00", "20"), Sub("500.00", "50.00", "10")],
        tax_inclusive="1150.00",
        payable="1150.00",
    )
)
(out / "03-alis-hatali-kdv.xml").write_bytes(
    build(
        number="XYZ2026000000010",
        uuid="2b1e0c4a-1111-4c2e-9b7a-000000000003",
        supplier_id="10000000146",
        supplier_scheme="TCKN",
        supplier_name="Tedarikçi Ltd.",
        customer_id="1234567890",
        customer_scheme="VKN",
        subtotals=[Sub("2000.00", "360.00", "20")],
        line_extension="2000.00",
        tax_exclusive="2000.00",
        tax_inclusive="2360.00",
        payable="2360.00",
    )
)
(out / "04-mukerrer.xml").write_bytes(build())
print(f"Örnekler yazıldı: {out}")
