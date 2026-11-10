# GitHub Yayın Hazırlığı Raporu

**Proje:** `economic-development-life-expectancy` · **Tarih:** 10 Kasım 2026 · **Veri sürümü:** WDI, 8 Ekim 2026

> **Karar: Teknik olarak hazır. Yayın için sizden 2 işlem ve ardından yayın onayı bekleniyor:**
> 1. Yazar bilgisi
> 2. Raporların son okuması
>
> Arşiv kararı uygulandı (Bölüm 4 ve 11). Son bilimsel düzeltmeler ve lisans düzenlemesi yapıldı (Bölüm 12). Yayımlanacak içerik: **70 dosya, 9.577.272 bayt (9,13 MB)**.
>
> ✅ **Güncelleme (Bölüm 14):** `.gitignore` ve `.gitattributes` kuralları yerel `git init` sonrasında gerçek Git komutlarıyla doğrulandı. Aşağıdaki eski not tarihsel kayıt olarak duruyor.
>
> ⚠️ ~~`.gitignore` ve `.gitattributes` kuralları gerçek Git işlemleriyle doğrulanmadı.~~ Hangi dosyaların yayımlanacağı, bu kurallar bir Python betiğiyle taklit edilerek belirlendi. Satır sonu korumasının (`-text`, `binary`) gerçekten uygulandığı ise hiç sınanmadı. Teyit, yayın onayından sonra `git init` ile birlikte yapılmalı (Bölüm 8).
>
> Git deposu oluşturulmadı. `git init`, commit ve push yapılmadı; doğrulama için geçici bir depo bile kurulmadı. Başka projelere dokunulmadı.

---

## 1. Raporlar arası tutarlılık

Kontrol edilen dosyalar: `README.md`, `reports/*.md` (6 dosya), `data/data_dictionary.md`, `DATA_LICENSE.md`.

**Temel sayılar.** Aşağıdaki değerlerin kullanıldığı her dosyada aynı olduğu doğrulandı: 5,27 / 0,742 / 1,55 / 4.916 / 509 / %9,4 / 199 / 38 test.

**Bu aşamada bulunup düzeltilen tutarsızlıklar:**

| Dosya | Sorun | Düzeltme |
|---|---|---|
| `reports/methodology.md` §Sample | "2023, yaşam beklentisinin projeksiyon değil UN tahmini olduğu son yıl" ifadesi doğrulanmamış bir iddiaydı | Gerekçe, doğrulanabilen bilgilerle yeniden yazıldı |
| `README.md` §Limitations | "Sivil kaydı zayıf ülkelerde UN modeller" ifadesi denetimde H2 olarak işaretlenen fazla yorumu tekrar ediyordu | Meta verinin gerçekte söylediğiyle değiştirildi |
| `reports/research_report_tr.md` Özet ve §11.2 | Veri sürümü duyarlılığından söz edilmiyordu | Özete bir cümle, §11.2'ye sürüm ve CAF duyarlılık sonuçları eklendi |
| `reports/technical_report.md` | Denetim betiğinden söz edilmiyordu | "Audit" bölümü eklendi |
| `data/data_dictionary.md` | Arşiv dosyaları tanımlanmamıştı | Eklendi |
| `reports/final_scientific_audit_tr.md` §6 | "Lisans yok" maddesi artık geçerli değildi | Güncelleme notu eklendi |

## 2. README güncellemesi

README yeniden yazıldı. Eklenenler:

- Bilimsel bulgular tablosu: tüm duyarlılık analizlerinde eğim aralıkları (5,25–5,42 ve 1,33–1,84).
- Ayrı bir **"Data-version sensitivity"** bölümü.
- Ayrı bir **"What could not be verified about the 2024 data"** bölümü.
- Lisans bölümü, yazar alanı ve denetim bağlantıları.

## 3. 2024 yaşam beklentisi: doğrulanamayan noktalar

README'de, `data_quality_report.md` §3'te ve araştırma raporu §13'te açıkça yazıldı:

* **Doğrulanabilenler:**
  * WDI Nisan 2026 sürüm notu demografik göstergelerin "2024 verisiyle güncellendiğini" söylüyor.
  * API'deki dipnot ve `obs_status` alanları boş.
  * WDI meta verisi yıllık WPP serilerinin enterpolasyonla üretildiğini belirtiyor.
* **Doğrulanamayanlar:**
  * 2024 değerlerinin tahmin mi projeksiyon mu olduğu.
  * Hangi WPP baskısından geldikleri.
  * 2023 değerlerinin niteliği.
  * BM veri portalı API'si erişim anahtarı istediği için (HTTP 401) çapraz kontrol yapılamadı.
* **Dolaylı kanıt (kesin değil):**
  * 165 ekonominin 2024 değeri WPP biçiminde, 52'si erkek ve kadın değerlerinden türetilmiş biçimde.
  * 2023→2024 değişimleri olağandışı düzgün (SS 0,35 yıl; 2022→2023 için 2,82).
* **Önlem:** Ana analiz 2023 yılına dayanıyor. 2024 kesiti aynı sonucu veriyor (5,26 vs 5,27).

## 4. `data/raw/archive/`: uygulanan karar

Kararınız uygulandı:

- 202503 ve 202504 kayıpsız gzip ile sıkıştırıldı ve yayımlanacak.
- 202412 yalnızca yerel yedekte, yayın dışında. Hiçbir dosya silinmedi.

| Dosya | Durum | Boyut | Orijinal JSON SHA-256 |
|---|---|---|---|
| `data/raw/archive/SP.DYN.LE00.IN_v202503.json.gz` | **Yayımlanacak** | 183.516 B (orijinal 6.101.459 B) | `14f3e77a47a1f223f34f954d69f5449b6712f227b38b6be4a66eedf2556b049a` |
| `data/raw/archive/SP.DYN.LE00.IN_v202504.json.gz` | **Yayımlanacak** | 186.796 B (orijinal 6.105.205 B) | `fe9ec342e12c9f1660bd830912a27a523c8e91205b198c61a506af4f3496f9b7` |
| `data/raw/archive/ARCHIVE_MANIFEST.json` | **Yayımlanacak** | 1,4 KB | Orijinal ve gz özetlerini içerir |
| `local_backup/archive_original/SP.DYN.LE00.IN_v202412.json` | Yerel, `.gitignore` ile dışlandı | 6.101.459 B | `21ae7938fead875ed48696c4e2a12c2142fcf73fbbda49dc0ef7e9e15151197f` (manifest'te `not_published` altında) |
| `local_backup/archive_original/SP.DYN.LE00.IN_v202503.json` | Yerel yedek (orijinal), dışlandı | 6.101.459 B | `14f3e77a…b049a` |
| `local_backup/archive_original/SP.DYN.LE00.IN_v202504.json` | Yerel yedek (orijinal), dışlandı | 6.105.205 B | `fe9ec342…f9b7` |

**Sıkıştırılmış .gz dosyalarının SHA-256 değerleri:**
- 202503: `73dc049fb7ea44b78dd9b10186cd02e32eb050fc30a401e21d77ebae931ef898`
- 202504: `4605b033d5315a91ee98004379dac46ce56a3bbd5b42d016c25e87c9496893a3`

**Bayt düzeyinde doğrulama (dört yoldan):**
1. Sıkıştırma sırasında Python'da açılıp orijinalle karşılaştırıldı.
2. Bağımsız olarak `gzip -dc … | cmp` komutuyla karşılaştırıldı: iki dosya da aynı.
3. `python audit/archive_io.py verify` çalıştırıldı: ikisi de OK.
4. Sıkıştırma aynı girdiyle tekrarlandığında aynı .gz baytları üretiliyor (deterministik).

**Ek koruma:** Denetim her çalıştığında açılan veriyi manifest'teki orijinal SHA-256 ile karşılaştırıyor. Uyuşmazlıkta duruyor. Bunu test eden bir test de var (`tests/test_archive.py`).

## 5. Lisans

* **Kod için MIT uygun.**
  * Bağımlılıkların hepsi izin veren lisanslı: pandas, NumPy, SciPy, statsmodels, ipykernel, nbconvert ve nbformat BSD; Matplotlib PSF tabanlı; requests Apache-2.0; pytest MIT.
  * Bağımlılıklar depoda dağıtılmıyor, yalnızca `requirements.txt` içinde adları geçiyor. Çelişen bir lisans yok.
* **Veri MIT kapsamında değil.**
  * Dünya Bankası verisi CC BY 4.0 lisanslı (API meta verisinden okundu).
  * İşlenmiş veri, tablolar, grafikler ve notebook çıktıları bu verinin uyarlamasıdır. Atıf ve "yapılan değişiklikler" bildirimi gerektirir.
* **Oluşturulan taslaklar:**
  * `LICENSE`: MIT, yalnızca kod ve yapılandırma dosyaları. Telif sahibi: Seyhan Anıl Kaya.
  * `LICENSE-DOCS.md`: CC BY 4.0, projenin özgün metinleri (README, raporlar, veri sözlüğü, notebook metin hücreleri).
  * `DATA_LICENSE.md`: Dünya Bankası verisi ve türetilmiş dosyalar. Kaynaklar, değişiklik listesi ve atıf metni burada.
  * Kapsamlar örtüşmüyor. README'deki lisans tablosu her klasörü tek bir lisansa bağlıyor.
* **Belirsiz nokta:** Arşiv kaynağının (API source 57) lisansının WDI ile aynı olduğu *varsayıldı*, ayrıca doğrulanmadı. Bu `DATA_LICENSE.md` içinde açıkça yazıyor.

## 6. Yazar bilgisi

**Güncellendi.** Yazar: **Seyhan Anıl Kaya**, Department of Statistics, Fırat University. Ayrıntılar Bölüm 13'te.

Bu turdan sonra kalan tek yer tutucu, `LICENSE-DOCS.md` içindeki atıf metninde yer alan `[REPOSITORY URL]` alanı. Depo oluşturulduktan sonra doldurulacak.

## 7. Temiz ortamda yeniden üretim (gerçekten çalıştırıldı)

Proje geçici bir klasöre kopyalandı, böylece yeni klonlanmış bir depo taklit edildi. Tüm üretilmiş çıktılar silindi: `data/processed`, `reports/tables`, `reports/audit`, `figures`.

| Adım | Sonuç |
|---|---|
| `python -m venv` + `pip install -r requirements.txt` (Python 3.14.4, sistem paketleri olmadan, kullanıcı site-packages kapalı) | ✅ Sabitlenen sürümlerin hepsi kuruldu. Jupyter çekirdeği sanal ortamın Python'unu kullandı |
| `python src/run_pipeline.py --offline` | ✅ Hatasız. 18 veri ve tablo dosyası ile 7 PNG, orijinalleriyle **bayt düzeyinde aynı** |
| `pytest` | ✅ 37 geçti, 1 atlandı (ağ testi). Arşiv değişikliğinden sonra: 43 geçti, 1 atlandı |
| `pytest --run-network` | ✅ 38/38 geçti. Arşiv değişikliğinden sonra: **44/44** |
| `python audit/run_audit.py` (önbellekteki arşivle) | ✅ Hatasız. `audit_results.json` ve tüm denetim CSV'leri orijinalleriyle aynı |
| `jupyter nbconvert --execute` notebook | ✅ 27 hücre, 0 hata |

**Kapsam sınırı:** Testler yalnızca Windows 11 + Python 3.14.4 üzerinde yapıldı. Linux, macOS ve eski Python sürümleri denenmedi.

## 8. GitHub'a yüklenecek dosyalar (güncel)

**Yayımlanacak: 70 dosya, 9.577.272 bayt (9,13 MB).** Arşiv kararından önce 26,2 MB'tı. Bölüm 12'de `LICENSE-DOCS.md` eklendi.
- Yerelde kalan, `.gitignore` ile dışlanan dosyalar: 3 dosya, 17,46 MB (`local_backup/`).
- En büyük dosya 2,26 MB. (Bu raporda MB = 1.048.576 bayt.) GitHub'ın dosya başına 100 MB sınırına yakın dosya yok.

Liste `.gitignore` kuralları uygulanarak çıkarıldı. Git kurulmadığı için bu kurallar bir Python betiğiyle taklit edildi. Kesin liste `git init` sonrasında `git status --ignored` ile teyit edilmeli.

| Klasör | Dosya | Boyut |
|---|---|---|
| Kök (`README.md`, `LICENSE`, `LICENSE-DOCS.md`, `DATA_LICENSE.md`, `requirements.txt`, `pytest.ini`, `.gitignore`, `.gitattributes`) | 9 | ~45 KB |
| `src/` | 5 | 59,3 KB |
| `audit/` (`run_audit.py`, `archive_io.py`) | 2 | 33,0 KB |
| `tests/` (`conftest.py` + 4 test dosyası) | 5 | 20,8 KB |
| `data/raw/` (API yanıtları, manifest, meta veri, 2 arşiv `.gz` + `ARCHIVE_MANIFEST.json`) | 8 | 4,91 MB |
| `data/processed/` | 6 | 1,45 MB |
| `data/data_dictionary.md` | 1 | 4,5 KB |
| `figures/` | 7 | 0,97 MB |
| `notebooks/01_analysis.ipynb` | 1 | 1,38 MB |
| `reports/*.md` | 6 | 90,7 KB |
| `reports/tables/` | 12 | 123,0 KB |
| `reports/audit/` | 8 | 63,2 KB |

Dosya bazında en büyükler:

| Dosya | Boyut |
|---|---|
| `data/raw/NY.GDP.PCAP.PP.KD.json` | 2,26 MB |
| `data/raw/SP.DYN.LE00.IN.json` | 2,12 MB |
| `notebooks/01_analysis.ipynb` | 1,38 MB |
| `data/processed/country_year_panel.csv` | 0,75 MB |
| `data/processed/analysis_sample.csv` | 0,66 MB |
| `figures/fig05_regression_diagnostics.png` | 0,20 MB |
| `data/raw/archive/SP.DYN.LE00.IN_v202504.json.gz` | 0,18 MB |
| `data/raw/archive/SP.DYN.LE00.IN_v202503.json.gz` | 0,17 MB |

**`.gitignore` ve `.gitattributes` uyumu:**
- `.gitignore`, `local_backup/` klasörünü ve `data/raw/archive/` içindeki açılmış `*.json` dosyalarını dışlıyor. `ARCHIVE_MANIFEST.json` bir istisna kuralıyla dahil ediliyor.
- `.gitattributes`, `data/raw/**` için `-text` ve `*.gz` için `binary` tanımlıyor. Ham veri ve arşivler satır sonu dönüşümüne uğramaz, SHA-256 özetleri her platformda geçerli kalır.
- Git ile teyit henüz yapılmadı. `git init` onayınızdan sonra şu iki komut çalıştırılmalı: `git status --ignored` ve `git check-attr -a data/raw/archive/*.gz`.

## 9. Gizli bilgi, kişisel bilgi ve geçici dosya taraması

| Kontrol | Sonuç |
|---|---|
| API anahtarı, token, parola ve benzeri desenler | ✅ Bulunmadı. Tek eşleşme, "UN portalı token istiyor" diyen bir not metni |
| E-posta adresi | ✅ Bulunmadı |
| **Kişisel dosya yolu** | ⚠️ → ✅ **Bulundu ve düzeltildi.** Notebook çıktısında `C:\Users\<kullanıcı adı>\AppData\...` yolu vardı (`make_figures.py`'deki bir `print`). Benzer `print`'ler `download_data.py` ve `audit/run_audit.py` içinde de vardı. Üçü de göreli yol yazacak biçimde değiştirildi ve notebook temiz ortamda yeniden çalıştırıldı. Yeniden yapılan taramada yol veya kullanıcı adı kalmadı |
| `__pycache__`, `.pytest_cache`, `.ipynb_checkpoints`, `*.pyc`, geçici dosyalar | ✅ Yok (temizlendi). `.gitignore` bunları dışlıyor |
| `.venv` | ✅ Proje klasöründe yok (temiz ortam geçici klasörde kuruldu) |
| **Satır sonları** | ⚠️ → ✅ **Bulundu ve önlem alındı.** Bu bilgisayarda Git `core.autocrlf=true` ayarlı ve tüm dosyalar CRLF ile yazılmış. Commit sırasında ham veri dosyalarının satır sonları değişirdi ve `download_manifest.json`'daki SHA-256 özetleri başka platformlarda tutmazdı. `.gitattributes` eklenerek `data/raw/**` dosyaları satır sonu dönüşümünden muaf tutuldu |

## 10. Sunumda açıklanması gereken beş sonuç (sade Türkçe)

1. **Zengin ülkelerde insanlar daha uzun yaşıyor, ama ek gelirin getirisi azalıyor.** 2023'te geliri iki katı olan bir ülkenin yaşam beklentisi ortalama 3,7 yıl daha yüksek. Ancak 1.000 dolarlık fark yoksul bir ülkede yaklaşık 2 yıl, zengin bir ülkede yalnızca 0,1 yıl fark ediyor. Bu yüzden gelirin logaritmasıyla kurulan model, düz çizgi modelinden çok daha iyi uyuyor: açıklanan değişkenlik %74'e karşı %56.
2. **İlişki güçlü ve sıralama açısından neredeyse kusursuz, ama düz bir çizgi değil.** Spearman korelasyonu 0,87, gelirin kendisiyle hesaplanan Pearson korelasyonu 0,75. Fark, ilişkinin eğri olmasından kaynaklanıyor. Logaritma alınınca iki katsayı birbirine yaklaşıyor (0,86 ve 0,87).
3. **Sonuç tek tük ülkelere bağlı değil.** Etkili 9 ülke çıkarılınca, toprak birimleri ve en zengin 10 ülke dışlanınca, 2023 yerine 2024 kullanılınca eğim hep 5,25 ile 5,42 arasında kalıyor.
4. **Ülkeler arasındaki fark, bir ülkenin zamanla zenginleşmesinin etkisi değildir.** Ülkeleri karşılaştırınca eğim yaklaşık 6. Aynı ülkeyi zaman içinde izleyip dünya genelindeki ortak iyileşmeyi çıkarınca eğim yaklaşık 1,5, yani dörtte bir. Bu nedenle "gelir artarsa ömür şu kadar uzar" denemez. Bu çalışma nedensellik iddia etmiyor.
5. **Verinin kendisi de değişebilir ve bu sonucu etkiler.** Dünya Bankası Nisan 2025'te yaşam beklentisi verilerini revize etti. Örneğin Orta Afrika Cumhuriyeti'nin 2019 değeri 55,0'dan 31,5'e indi. Ülkeler arası sonuç bundan etkilenmiyor (5,53 ve 5,52). Ülke içi sonuç ise 1,55'ten 1,84'e kayıyor. İyi bir araştırma hangi veri sürümünü kullandığını yazar ve bu duyarlılığı raporlar.

---

## Yayından önce yapılması gerekenler

**Sizin kararınız veya işleminiz gerekiyor:**

1. ☑ Yazar bilgisi dolduruldu (Seyhan Anıl Kaya). ☐ `LICENSE-DOCS.md` içindeki `[REPOSITORY URL]` alanı depo oluşturulduktan sonra doldurulacak.
2. ☑ Arşiv kararı uygulandı (gzip, 202412 yerelde). Bkz. Bölüm 4 ve 11.
3. ☐ Düzeltilmiş raporları okumak. Özellikle `research_report_tr.md` (Özet, §11.2, §13), `data_quality_report.md` §3 ve §5, `final_scientific_audit_tr.md`.
4. ☐ Depo adını, açıklamasını ve görünürlüğünü (public veya private) belirlemek.
5. ☐ `git init`, ardından `git status --ignored` ve `git check-attr` ile `.gitignore` ve `.gitattributes` teyidi, ilk commit ve GitHub deposunun oluşturulması. **Yalnızca açık onayınızla yapılacak.**

**İsteğe bağlı iyileştirmeler** (yayını engellemez):

6. ☐ `CITATION.cff` dosyası eklemek, böylece GitHub "Cite this repository" düğmesini gösterir.
7. ☐ GitHub Actions ile otomatik `pytest`. Linux üzerinde de test etmeyi sağlar; şu an yalnızca Windows'ta denendi.
8. ☐ Denetimde önerilen ama uygulanmayan metodolojik iyileştirmeler (`final_scientific_audit_tr.md` §4): kümelenmiş çıkarımda t dağılımı, nüfus ağırlıklı analiz, gecikmeli modeller, daha iyi bir bayrak kuralı.

**Bilinen ve çözülemeyen sınırlılıklar** (yayında açıkça yazılı kalmalı):

* 2024 yaşam beklentisi verilerinin niteliği (Bölüm 3).
* Nisan 2025 revizyonunun nedeni.
* Arşiv verisinin lisansının WDI ile aynı olduğu varsayımı.
* Yalnızca tek platformda yapılmış testler.

---

## 11. Arşiv değişikliği: önce ve sonra karşılaştırması

**Değişiklikten önce tüm çıktılar yedeklendi:** 33 veri, tablo, denetim ve grafik dosyası ile notebook. Sonra her şey yeniden çalıştırıldı ve dosyalar tek tek karşılaştırıldı.

| Kontrol | Sonuç |
|---|---|
| `data/processed/*`, `reports/tables/*` (`results.json` dahil), `figures/*.png`, 8 denetim dosyasından 6'sı | **31 dosya bayt düzeyinde aynı.** `results.json` SHA-256 = `c87acc37…` (önceki ile aynı) |
| `reports/audit/caf_life_expectancy_vintages.csv` | **Değişti, beklenen biçimde.** Yalnızca `archive_202412` sütunu kalktı. Bu sütun 202503 sütunuyla birebir aynıydı. Kalan sütunlar aynı |
| `reports/audit/audit_results.json` | **Değişti, beklenen biçimde.** `caf_vintages` içinden yalnızca 202412 değerleri çıktı; geri kalanı aynı. İzlenebilirlik için iki alan eklendi: `archive_versions_used` = [202503, 202504] ve `archive_original_sha256`. **Hiçbir sayısal sonuç değişmedi** |

**Temel bilimsel sonuçlar (önce = sonra):**

| Sonuç | Değer |
|---|---|
| Model B eğimi 2023 | 5,267 [4,854; 5,680] |
| R² (B) | 0,742 |
| Spearman ρ 2023 | 0,872 |
| İki yönlü FE (2000–2024) | 1,549 [0,494; 2,605] |
| Eğimin yıllık değişimi | −0,041 (p = 0,0007) |
| Sürüm duyarlılığı, 2000–2022 FE | 1,836 (güncel) ve 1,546 (202503) |
| Nisan 2025 revizyonu | 196/212 ekonomi, ortalama mutlak değişim 0,604 yıl |
| CAF 2009 / 2019 / 2022 (202503 → 202504) | 48,6 → 14,7 / 55,0 → 31,5 / 54,5 → 18,8 |

**v202412 olmadan yeniden üretim (gerçekten çalıştırıldı):**
- Yalnızca yayımlanacak 69 dosya geçici bir klasöre kopyalandı. Bu kopyada 202412 dosyası ve `local_backup/` klasörü yoktu. Üretilmiş tüm çıktılar silindi.
- Temiz sanal ortamda sırasıyla şunlar çalıştırıldı: `archive_io.py verify` (OK), `run_pipeline.py --offline`, `run_audit.py`, `pytest`, `pytest --run-network` ve notebook.
- **Sonuç:** 44/44 test geçti, notebook'ta 0 hata. Yeniden üretilen **33 dosyanın 33'ü** projedekiyle bayt düzeyinde aynı.

**Yerel yedekler:**
- `local_backup/archive_original/`: üç orijinal JSON dosyası. SHA-256 özetleri ilk indirmeyle aynı.
- Değişiklik öncesi tüm çıktıların kopyası, proje dışında geçici klasörde duruyor (`%TEMP%\baseline_174458`). Yayımlanmayacak.

---

## 12. Son bilimsel düzeltmeler ve lisans düzenlemesi

Bu turda yeni analiz yapılmadı ve hiçbir sayısal sonuç değişmedi. Analiz yeniden çalıştırıldı; `results.json` SHA-256 değeri önceki çalıştırmayla aynı.

| # | İstek | Yapılan |
|---|---|---|
| 1 | Sonuç bölümüne veri sürümü paragrafı | `research_report_tr.md` §14'e paragraf eklendi. Ülkeler arası eğim sürümler arasında kararlı (5,53 vs 5,52). Ülke içi eğim daha duyarlı (1,84 vs 1,55). Ülke içi eğimin daha az kesin biçimde yorumlanması gerektiği belirtildi |
| 2 | Guyana, Brunei ve İrlanda ifadesi | **İrlanda için birincil kaynak bulundu:** Honohan (2021), *Central Bank of Ireland Economic Letter*, Vol. 2021 No. 1. Bu kaynağa göre CSO'nun GNI* ölçüsü 2019'da GSYH'nin yaklaşık %40 altındaydı. **Guyana ve Brunei için resmî veya akademik bir birincil kaynak bulunamadı**; bulunanlar haber ve yorum yazılarıydı. Bu iki ülke §13'teki ifadeden çıkarıldı ve ifade genel bir metodolojik sınırlılık olarak yeniden yazıldı. §10'daki "petrol üretimi GSYH'yi yükseltti" gibi kaynaksız nedensel ifade de kaldırıldı. Bu ülkeler artık yalnızca model artıklarıyla, yani veriden okunan betimsel bilgiyle anılıyor |
| 3 | Sivil kayıt açıklamasının kaynağı | **Doğrulandı:** Chao, Williams, Zeifman ve Gerland (2024), UN DESA/POP/2024/TP/No.9. Dünya ülkelerinin yaklaşık yarısında yaşa ve cinsiyete göre ayrıntılı ve doğru ölçüm verisi yok; bu ülkelerde model tabanlı yöntemler kullanılıyor. Hangi ülkelerin bu gruba girdiği bu çalışmada belirlenmedi; metin bunu açıkça söylüyor |
| 4 | Preston sonucunu sınırlandırmak | §14 ve §11.1 yalnızca test edilen örüntüyle sınırlandırıldı: ülkeler arası örüntü ve eğimin düzleşmesi. "Eğri yukarı kaydı" ifadesi kaldırıldı ve "bu çalışmada test edilmedi" notu eklendi. README'deki ilgili cümle de düzeltildi. Girişte bu özellik yalnızca literatür bilgisi olarak, kaynağıyla birlikte duruyor |
| 5 | Özgün metinler için CC BY 4.0 | `LICENSE-DOCS.md` oluşturuldu. `LICENSE` ve `DATA_LICENSE.md` dosyalarının kapsam açıklamaları güncellendi. README'ye üç kapsamlı bir lisans tablosu eklendi. Kalan tek hukuki nüans: MIT'nin standart metni "associated documentation files" ifadesini içeriyor, ancak `LICENSE` dosyasının başındaki kapsam notu belgeleri açıkça dışarıda bırakıyor |
| 6 | Yer tutucular | Korundu. Hiçbir kimlik bilgisi girilmedi |
| 7 | Tutarlılık ve testler | Tüm `.md` dosyaları tarandı. Guyana, Brunei, "yukarı kayma" ve sivil kayıt ifadelerinde artık kaynaksız bir iddia kalmadı. Testler: `pytest --run-network` **44/44**, çevrimdışı 43 geçti ve 1 atlandı. `archive_io.py verify` OK. Kod değişmediği için notebook yeniden çalıştırılmadı |
| 8 | Git doğrulaması | Yapılmadı. Belgenin başında ve Bölüm 8'de açıkça yazıyor |

**Yeni kaynaklar:**
- Honohan, P. (2021). Is Ireland really the most prosperous country in Europe? *Central Bank of Ireland Economic Letter*, Vol. 2021, No. 1.
- Chao, F., Williams, I., Zeifman, L., & Gerland, P. (2024). *Estimating age-sex-specific adult mortality in the World Population Prospects: A Bayesian modelling approach*. UN DESA/POP/2024/TP/No.9.

---

## 13. Yazar bilgisi ve kişisel veri kontrolü

**Güncellenen yazar alanları:**

| Dosya | Yeni değer |
|---|---|
| `LICENSE` | `Copyright (c) 2026 Seyhan Anıl Kaya` |
| `LICENSE-DOCS.md` | Telif satırı ve atıf metni: Seyhan Anıl Kaya |
| `README.md` | `**Author:** Seyhan Anıl Kaya · Department of Statistics, Fırat University` |
| `reports/research_report_tr.md` | Yazar satırı eklendi: Seyhan Anıl Kaya · İstatistik Bölümü, Fırat Üniversitesi (Department of Statistics, Fırat University) |
| `reports/student_learning_guide_tr.md` | Yazar satırı eklendi |
| `reports/final_scientific_audit_tr.md` | Başlık satırına yazar eklendi |

**Kişisel veri taraması:**
- Taranan dosyalar: yayımlanacak 70 dosya ve `local_backup/`. İkili dosyalar da içerik olarak tarandı (`grep -a`). Arşivler açılarak tarandı. PNG dosyalarının meta verisine de bakıldı.
- Aranan desenler: Windows kullanıcı adı, kullanıcı klasörünün tam yolu, `AppData`, geçici klasör adları, e-posta adresleri.
- Sonuç: **Bulunmadı.** Tek eşleşme, bu raporun 9. bölümündeki anonimleştirilmiş genel örnek (`C:\Users\<kullanıcı adı>\AppData\...`). PNG meta verisinde yalnızca `Software: Matplotlib` bilgisi var.
- Kod ve belgelerde kullanıcıya özel mutlak dosya yolu yok. Tüm yollar göreli (`data/raw/`, `figures/` vb.). Programlar yolları çalışma anında projenin kökünden (`Path(__file__)`) hesaplıyor ve ekrana göreli yol yazıyor.

**Git yapılandırması** (yalnızca okundu, hiçbir ayar değiştirilmedi):
- Sistem düzeyi: `user.name` ve `user.email` ayarlı değil.
- Global düzey (`~/.gitconfig`): `user.name = seyhanil1`. Bu, istenen yazar adı "Seyhan Anıl Kaya"dan **farklı**. `user.email` ayarlı.
- **Öneri:** Yayın onayından sonra, yalnızca bu depo için ve `git init`'ten hemen sonra, ilk commit'ten önce aşağıdaki komut çalıştırılmalı. Bu komut yalnızca `.git/config` dosyasını değiştirir; global ayara dokunmaz.

  ```bash
  git config user.name "Seyhan Anıl Kaya"
  ```

  İsterseniz aynı şekilde yalnızca bu depo için `git config user.email "<adres>"` da ayarlanabilir. GitHub'da gizli kalması için bir `noreply` adresi tercih edilebilir.

---

## 14. Yerel Git hazırlığı

**Yapılanlar** (yalnızca proje klasöründe, yerel olarak):
- `git init -b main` çalıştırıldı.
- Yerel kullanıcı adı ayarlandı: `git config --local user.name "Seyhan Anıl Kaya"`. Global ayar (`seyhanil1`) değiştirilmedi.

**Henüz yapılmayanlar:** `git add`, commit, push, uzak depo (remote) tanımı, GitHub deposu. Git index'i bile oluşmadı. `user.email` yerel olarak ayarlanmadı (onay bekleniyor).

**E-posta:**
- Global Git e-postası bir Gmail adresi; Claude oturumunuzun e-postasıyla aynı.
- Herkese açık bir depoda bu adres commit geçmişinde görünür.
- Önerilen GitHub noreply adresi: `281358325+seyhanil1@users.noreply.github.com`. GitHub'ın herkese açık API'sinde `seyhanil1` hesabının kimlik numarası 281358325.
- Bu hesabın size ait olduğu ve adresin doğru olduğu GitHub → Settings → Emails sayfasından teyit edilmeli. Adres onayınızdan sonra yalnızca bu depo için ayarlanacak.

**Gerçek Git ile doğrulama:**

| Kontrol | Komut | Sonuç |
|---|---|---|
| İzlenecek dosyalar | `git ls-files --others --exclude-standard` | **70 dosya.** Python taklidinin listesiyle birebir aynı |
| Dışlanan dosyalar | `git status --ignored` | 3 dosya: `local_backup/archive_original/*.json` (`.gitignore:13`) |
| Kural sınaması | `git check-ignore -v --no-index` | `.venv/`, `venv/`, `__pycache__/`, `.pytest_cache/`, `.ipynb_checkpoints/`, `.env`, `Thumbs.db`, `.DS_Store`, `data/raw/archive/*.json` dışlanıyor. `ARCHIVE_MANIFEST.json` istisna kuralıyla (`.gitignore:16`) dahil |
| Satır sonu koruması | `git check-attr text binary diff` | `data/raw/**`: `text: unset`, yani dönüşüm yok ve SHA-256 korunur. `*.gz` ve `*.png`: `binary: set`. Diğer metin dosyaları: `unspecified` |

**Not:**
- `core.autocrlf=true` (Git for Windows sistem ayarı) nedeniyle README, kod, CSV ve notebook gibi metin dosyaları commit sırasında CRLF'den LF'ye çevrilecek. `git add` sırasında bunun için uyarı görülmesi beklenir.
- Bu çevrim, SHA-256 özeti kayıtlı olan hiçbir dosyayı etkilemiyor; o dosyalar `data/raw/**` altında ve korunuyor.
- Linux veya macOS'ta pipeline LF ile yeniden üreteceği için çıktılar depodaki sürümle eşleşir.
- Git'te index olmadığı için bu çevrim henüz fiilen sınanmadı. İlk `git add`'den sonra `git ls-files --eol` ile kontrol edilmeli.
