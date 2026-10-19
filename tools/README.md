# Vitpepper Academy — canlı site nasıl üretiliyor

- `src/vitpepper-academy.html` — sitenin kaynak şablonu (Claude'daki düzenleme paneliyle aynı sayfa).
- `tools/build_static.py` — şablonu + veritabanı dışa aktarımını (areas/*.json) alıp kök dizine `index.html`, `404.html`, `CNAME`, `.nojekyll` yazar.
- Ders içeriği Claude'daki Vitpepper Academy sayfasının veritabanında tutulur; saatlik eşitleme görevi orayı okuyup bu depoyu günceller.

Elle çalıştırmak için:
    python3 tools/build_static.py src/vitpepper-academy.html <export-klasörü>/areas .

## Şifre kapısı
Derlerken `ACADEMY_PASSWORD=<şifre>` ortam değişkeni verilirse sayfa gövdesi AES-GCM ile şifrelenir;
ziyaretçi logo + şifre alanı görür, doğru şifreyle içerik tarayıcıda çözülür. Değişken verilmezse site açık yayınlanır.
    ACADEMY_PASSWORD=1234 python3 tools/build_static.py src/vitpepper-academy.html <export>/areas .
