# FaturaKit

**e-Fatura ve e-Arşiv (UBL-TR) XML dosyalarını saniyeler içinde kontrol edip Excel'e aktaran, tamamen bilgisayarınızda çalışan araç.**

Mali müşavirler ve muhasebe ekipleri için yapıldı. Faturalar hiçbir sunucuya gönderilmez, internet gerekmez.

## Ne yapar?

- Bir klasördeki, alt klasörlerdeki ya da ZIP arşivlerindeki tüm fatura XML'lerini okur.
- Tek bir Excel dosyası üretir:
  - **Faturalar:** fatura no, ETTN, tarih, senaryo, tip, satıcı/alıcı VKN-TCKN ve unvan, tüm tutarlar
  - **KDV Dağılımı:** her faturanın her KDV oranı için matrah ve KDV
  - **KDV Özeti:** Satış/Alış ve orana göre toplam matrah ve KDV (mükerrer faturalar hariç)
  - **Kontroller:** bulunan tüm hatalar ve uyarılar
- Kendi VKN'nizi verirseniz faturaları **Satış / Alış** olarak ayırır.

## Kontroller

| Kod | Seviye | Açıklama |
|---|---|---|
| `KDV_HESAP` | HATA | Matrah × oran, faturadaki KDV tutarını tutmuyor |
| `TOPLAM` | HATA | Vergiler hariç tutar + vergiler, vergiler dahil tutarı tutmuyor |
| `MUKERRER` | HATA | Aynı ETTN veya aynı satıcı + fatura no ikinci kez okundu |
| `VKN_EKSIK` | HATA | Satıcı veya alıcı VKN/TCKN yok |
| `VKN_GECERSIZ` | UYARI | VKN/TCKN kontrol hanesi tutmuyor |
| `DONEM` | UYARI | Fatura tarihi seçilen dönemin dışında |
| `OKUNAMADI` | HATA | Dosya bozuk, fatura değil ya da güvenli olmayan XML |

Kuruş yuvarlama farkları için varsayılan tolerans 0,02 TL'dir (`--tolerans` ile değiştirilebilir).

## Kurulum

Python 3.10 veya üstü gerekir.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
```

## Kullanım

```powershell
.\.venv\Scripts\faturakit D:\Faturalar\2026-10 -o ekim.xlsx --vkn 1234567890 --donem 2026-10
```

Birden fazla girdi verilebilir (dosya, klasör, ZIP karışık):

```powershell
.\.venv\Scripts\faturakit gelen.zip giden\ ek-fatura.xml -o rapor.xlsx
```

Çıkış kodları: `0` sorun yok, `1` en az bir HATA bulundu, `2` hatalı parametre veya dosya yazılamadı.

### Örneklerle deneyin

```powershell
.\.venv\Scripts\python examples\make_examples.py
.\.venv\Scripts\faturakit examples\ornek-faturalar -o demo.xlsx --vkn 1234567890 --donem 2026-10
```

Örneklerde bir hatalı KDV ve bir mükerrer fatura bulunur; ikisi de Kontroller sayfasında görünür.

## Python kütüphanesi olarak

```python
from faturakit.loader import load_invoices
from faturakit.validation import validate
from faturakit.exporter import export_excel

invoices, issues = load_invoices(["D:/Faturalar"])
issues += validate(invoices, period="2026-10")
export_excel(invoices, issues, "rapor.xlsx", own_tax_id="1234567890")
```

## Güvenlik

- XML'ler `defusedxml` ile okunur; entity genişletme ve dış kaynak saldırıları engellenir.
- Tek bir XML için 50 MB üst sınır vardır (ZIP bombalarına karşı).
- Hiçbir veri ağ üzerinden gönderilmez.

## Geliştirme

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest
```

## Yol haritası

- [ ] Banka ekstresi (Excel/CSV) ile otomatik mutabakat
- [ ] Masaüstü arayüz (sürükle-bırak)
- [ ] Muhasebe programları için içe aktarma şablonları
- [ ] Fatura satırları (mal/hizmet kalemleri) sayfası
- [ ] Windows kurulum paketi ve GitHub Release otomasyonu

## Lisans

[MIT](LICENSE)
