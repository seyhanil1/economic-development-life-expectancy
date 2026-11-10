# Bağımsız Bilimsel Kalite Denetimi — Yayın Öncesi Rapor

**Proje:** Economic Development & Life Expectancy · **Yazar:** Seyhan Anıl Kaya (Department of Statistics, Fırat University) · **Denetim tarihi:** 10 Kasım 2026 · **Denetlenen veri:** WDI, 8 Ekim 2026 sürümü (çekim 10.11.2026 13:46:55 UTC)

Bu denetim yeni bir analiz geliştirmez. Mevcut sonuçları bağımsız hesaplarla, kaynak verinin geçmiş sürümleriyle ve duyarlılık analizleriyle sınar.

**Denetimlerin gerçekten çalıştırıldığının kaydı.** Tüm kontroller `audit/run_audit.py` betiğinde, tekrar çalıştırılabilir biçimde duruyor. Betik 10.11.2026'da `--refetch` seçeneğiyle hatasız çalıştı. Ham çıktılar `reports/audit/` klasöründedir:

- `audit_results.json`
- `caf_life_expectancy_vintages.csv`
- `economies_in_analysis_199.csv`
- `economies_cross_section_2023_197.csv`
- `aggregates_excluded.csv`
- `hand_example_2023.csv`
- `sensitivity_summary.csv`
- `yearly_with_without_caf.csv`

WDI arşiv yanıtları `data/raw/archive/` klasöründe saklandı. Ayrıca şunlar yapıldı: API dipnot sorgusu, cinsiyete göre yaşam beklentisi serileri, WDI Nisan 2025 ve Nisan 2026 sürüm notları ve BM WPP veri portalı denemesi. BM WPP portalı HTTP 401 döndürdü (erişim anahtarı gerekiyor). Denetimden sonra `pytest --run-network` yeniden çalıştırıldı (sonuç Bölüm 6'da).

---

## 1. Doğrulanan bulgular

| # | Kontrol | Sonuç | Kanıt |
|---|---|---|---|
| D1 | Model A, B ve C aynı gözlemlerle mi kuruldu? | **Evet.** Üçü de n = 197 ve satır kümeleri birebir aynı | `audit_results.json → same_sample`; `src/statistical_analysis.py` `fit_models` (s.153–156): tüm modeller tek veri çerçevesi `prepare_cs` (s.145) üzerinde kuruluyor |
| D2 | HC3 standart hataları doğru mu? | **Evet.** (XᵀX)⁻¹ Xᵀ diag(eᵢ²/(1−hᵢ)²) X (XᵀX)⁻¹ formülüyle elle hesaplanan SH ile statsmodels arasındaki en büyük fark 3,5·10⁻¹⁴. Model B eğim SH = 0,21068 | `hc3_check` |
| D3 | İki yönlü sabit etkiler tasarım matrisi | 4.916 × 224 matris, tam rank (224). 1 sabit, 1 eğim, 198 ülke kuklası (referans ülke: ABW, Aruba), 24 yıl kuklası (referans yıl: 2000). Beklenen sütun sayısıyla aynı | `fe_design` |
| D4 | Sabit etkiler eğimi bağımsız yöntemle aynı mı? | **Evet.** Frisch–Waugh–Lovell ile hesaplandı: dengesiz panel iki yönlü ortalamadan arındırma (alternating projections). Eğim 1,549416, fark 3·10⁻¹⁴ | `fe_cluster_check` |
| D5 | Kümelenmiş SH doğru mu? | **Evet.** Elle hesaplanan CR1 sandviç SH = 0,538663, statsmodels ile birebir aynı. G = 199 küme | `fe_cluster_check` |
| D6 | Korelasyonlar ve katsayılar ikinci yöntemle aynı mı? | **Evet.** Yalnızca NumPy ile (Pearson formülü, ortalama sıra ile Spearman, `lstsq` ile EKK) aynı sonuçlar çıktı. Farklar ≤ 1,4·10⁻¹⁴ | Bölüm C, `independent` |
| D7 | Toplulaştırma sınıflandırması | 296 kayıt = 217 ekonomi + 79 toplulaştırma. Toplulaştırma tanımı (`region == "Aggregates"`) ile `incomeLevel == "Aggregates"` 79 kaydın tamamında örtüşüyor, hiçbir ekonominin gelir grubu boş değil. Boş ISO3 kodlu 5 gelir grubu toplulaştırması 2 harfli kodla eşleştirilip dışlanıyor | `clean_data.py` `classify_entities` (s.81, kural s.93), `resolve_iso3` (s.102–108); `aggregates_excluded.csv` |
| D8 | 509 eksik gözlem ve %9,4 | **Doğru.** Payda 217 ekonomi × 25 yıl = 5.425 ülke-yılı (toplulaştırmalar hariç). 509 / 5.425 = %9,38. Bunun 450'si hiç GSYH verisi olmayan 18 ekonomiden (18 × 25), 59'u kısmen kapsanan ekonomilerden geliyor. Analizdeki 199 ekonomi için eksiklik oranı yalnızca %1,2 | `missing_arithmetic` |
| D9 | 199 / 197 farkı | 2023 kesitinde olmayan 2 ekonomi var: Suriye (SYR) ve ABD Virjin Adaları (VIR). İkisinin de son GSYH yılı 2022 | `economies_in_analysis_199.csv`, `economies_cross_section_2023_197.csv` |
| D10 | Uzun fark modellerinde n | 2000→2019 için n = 192. Analizdeki 199 ekonominin 7'sinde 2000 verisi yok (CYM, DJI, FRO, SXM, TCA, VIR, XKX). 2000→2023 için n = 191: aynı 7 ekonomiye ek olarak 2023'te verisi olmayan SYR düşüyor (VIR zaten ilk listede) | `long_diff_counts` |
| D11 | Zaman içinde eğim değişiminin p-değeri | Model: LE = α_yıl + (b + c·(yıl−2000))·lnGSYH, ülke düzeyinde kümelenmiş SH. ĉ = −0,04079, SH = 0,01208, z = ĉ/SH = −3,378. p = 2·(1−Φ(3,378)) = 0,00073 (normal dağılım, raporlanan değer). t(198) dağılımıyla p = 0,00088. Eğimin 24 yıllık toplam değişimi −0,98 | `statistical_analysis.py` `slope_trend_test` (s.346); `slope_trend_steps` |
| D12 | 2009, 2019 ve 2022'deki "çukurların" CAF kaynaklı olduğu iddiası | **Doğrulandı.** CAF çıkarılınca güven aralığı genişliği 2009'da 1,68'den 1,05'e, 2019'da 1,36'dan 0,87'ye, 2022'de 1,81'den 0,88'e düşüyor. Pearson r (ln) de bu yıllarda normale dönüyor | `yearly_with_without_caf.csv` |
| D13 | log₁₀ ile ln arasında fark | Eğimler tam olarak ln 10 = 2,3026 oranında farklı, R² aynı (0,7419). Logaritma tabanı sonucu değil, yalnızca birimi değiştirir | `transform` |

**Elle doğrulanabilir küçük örnek (2023, 5 ekonomi).** x = ln(GSYH), y = yaşam beklentisi:

| Ekonomi | GSYH ($) | x | y | x−x̄ | y−ȳ | (x−x̄)(y−ȳ) | (x−x̄)² | (y−ȳ)² |
|---|---|---|---|---|---|---|---|---|
| Burundi | 1.033,0 | 6,940 | 63,651 | −2,363 | −6,012 | 14,206 | 5,584 | 36,140 |
| Nijerya | 7.843,0 | 8,967 | 54,462 | −0,336 | −15,201 | 5,106 | 0,113 | 231,061 |
| Hindistan | 8.870,6 | 9,090 | 72,003 | −0,213 | 2,340 | −0,498 | 0,045 | 5,477 |
| Türkiye | 35.069,2 | 10,465 | 77,156 | 1,162 | 7,493 | 8,706 | 1,350 | 56,150 |
| Almanya | 63.140,2 | 11,053 | 81,041 | 1,750 | 11,379 | 19,911 | 3,062 | 129,476 |
| **Toplam / ortalama** | | x̄ = 9,303 | ȳ = 69,663 | | | **Sxy = 47,431** | **Sxx = 10,154** | **Syy = 458,305** |

* b₁ = Sxy / Sxx = 47,431 / 10,154 = **4,671**, b₀ = ȳ − b₁x̄ = **26,205**. statsmodels sonucu: 4,671212 (aynı).
* r = Sxy / √(Sxx·Syy) = 47,431 / √(10,154 × 458,305) = **0,6953**. SciPy sonucu: 0,695291 (aynı).
* Spearman: GSYH sıraları (1,2,3,4,5), yaşam beklentisi sıraları (2,1,3,4,5). Σd² = 2. ρ = 1 − 6·2 / (5·24) = **0,90**. SciPy sonucu: 0,90 (aynı).
* Bu örnekte Nijerya'nın gelirine göre düşük yaşam beklentisi Pearson r'yi 0,70'e çeker. Sıralamaya dayanan Spearman ise 0,90'da kalır. Bu, tek bir uç gözlemin Pearson'ı ne kadar etkileyebildiğini gösterir.

## 2. Tespit edilen hatalar

Hesaplamalarda hata bulunmadı: tüm sayılar bağımsız yöntemlerle birebir yeniden üretildi. Hatalar **raporlardaki yorum ve belgeleme** düzeyindeydi. Hepsi bu denetimde düzeltildi.

| # | Hata | Konum (önceki sürüm) | Düzeltme |
|---|---|---|---|
| H1 | **Orta Afrika Cumhuriyeti (CAF) değerleri "BM'nin kriz ölüm modellemesiyle tutarlı resmî değerler" olarak sunulmuştu.** Bu yorum kanıtsızdı. Asıl önemli bilgi eksikti: WDI'nin Temmuz 2024, Aralık 2024 ve Mart 2025 sürümlerinde CAF serisi **düzgündü** (2009: 48,6; 2019: 55,0; 2022: 54,5). 14,7 / 31,5 / 18,8 değerleri ilk kez **Nisan 2025** sürümünde yer aldı | `reports/data_quality_report.md` §5; `reports/research_report_tr.md` §5 | Revizyon geçmişi eklendi, kanıtsız yorum kaldırıldı |
| H2 | "Sivil kaydı zayıf ülkelerde yaşam beklentisi modellenir, WDI meta verisi bunu açıkça belirtir" ifadesi meta veriyi fazla yorumluyordu. Meta veri yalnızca yıllık WPP serilerinin **enterpolasyonla** üretildiğini söyler | `research_report_tr.md` §13 | Meta verinin gerçekte söylediğiyle değiştirildi. GSYH meta verisindeki SGP dışdeğerleme ve regresyonla tahmin bilgisi eklendi |
| H3 | "WPP 2024: 1950–2023 tahmin, 2024 sonrası projeksiyon" bilgisi kaynak gösterilmeden yazılmıştı. BM'nin WPP 2024 sayfası projeksiyonların hangi yıl başladığını belirtmiyor | `data_quality_report.md` §3 | Doğrulanabilen bilgilerle değiştirildi (bkz. B1) |
| H4 | Breusch–Pagan testinin hangi sürümü kullanıldığı belirtilmemişti. statsmodels'in varsayılanı studentize edilmiş Koenker sürümüdür. Klasik sürüm Model B için p = 0,072 verir (Koenker: 0,160) | `methodology.md` §3–4; `statistical_analysis.py` `diagnostics` s.191 | Belgelendi |
| H5 | HC3 ve kümelenmiş SH çıkarımının **normal dağılımla** yapıldığı (`use_t=False`) ve kümelenmiş SH'nin küçük örneklem düzeltmesine sabit etki kuklalarının da dahil edildiği belirtilmemişti | `methodology.md`; `_clustered` s.312–315 | Belgelendi. Etkisi: GA [0,494; 2,605] (z) ile [0,487; 2,612] (t) arasında. SH, Stata `xtreg` sonucundan %2 büyük, yani ihtiyatlı |
| H6 | "Geçici şok" bayrağı CAF'ın iki kriz arasındaki **normal** yıllarını da işaretliyor (ör. 2018 = 52,3). Bayrak "kriz yılı" olarak sunulmuştu | `clean_data.py` `add_flags` s.175; `data_quality_report.md` | Belgede kaba bir oynaklık bayrağı olduğu açıklandı. Kod değiştirilmedi. CAF'ın tamamen çıkarıldığı ayrı bir duyarlılık analizi eklendi (Bölüm 5) |
| H7 | Veri sürümüne duyarlılık ölçülmemişti. README ve rapor bu riski yalnızca genel olarak anıyordu | README, rapor §13 | Ölçüldü ve eklendi (bkz. Bölüm 5) |

Düzeltilen belgeler: `reports/data_quality_report.md`, `reports/research_report_tr.md`, `reports/methodology.md`, `README.md`. Kaynak kod ve analiz sonuçları **değişmedi**: `results.json` SHA-256 = c87acc37…, önceki çalıştırmayla aynı.

## 3. Çözülemeyen belirsizlikler

* **B1 — 2024 yaşam beklentisi verisinin niteliği.** Doğrulanabilenler şunlar:
  * WDI Nisan 2026 sürüm notu demografik göstergelerin "2024 verisiyle güncellendiğini" söylüyor, ama tahmin mi projeksiyon mu olduğunu ve WPP baskısını belirtmiyor.
  * API'de dipnot ve `obs_status` alanları boş.
  * Değerlerin sayısal biçimi iki kaynağa işaret ediyor. 52 ekonominin değeri erkek ve kadın değerlerinden türetilmiş görünüyor (ulusal istatistik kurumu veya Eurostat yolu, ör. DEU 80,79268…). 165'i ise 3 ondalıklı WPP biçiminde. Bu ayrım bir çıkarımdır, kaynakta yazmıyor.
  * 2023→2024 değişimleri olağandışı düzgün: standart sapma 0,35 yıl (2022→2023 için 2,82). Bu, değerlerin çoğunun model veya projeksiyon kaynaklı olduğuna işaret eder ama kanıtlamaz.
  * BM WPP veri portalı API'si erişim anahtarı istediği için çapraz kontrol yapılamadı.
* **B2 — Nisan 2025 revizyonunun nedeni.** Bu sürümde 212 ekonominin 196'sının yaşam beklentisi değişti (ortalama mutlak değişim 0,60 yıl; değişimlerin %18'i 1 yıldan büyük). Yeni bir WPP baskısının benimsenmesi en olası açıklama, ancak Nisan 2025 sürüm notu yaşam beklentisinden söz etmiyor. Neden doğrulanamadı.
* **B3 — CAF değerlerinin gerçekliği.** Erkek ve kadın serileri aynı düşüşleri gösteriyor (ör. 2009: erkek 12,4, kadın 20,0), yani seri kendi içinde tutarlı. Bu düşüşlerin gerçek ölüm olaylarını mı yoksa modelleme varsayımlarını mı yansıttığı WDI'den belirlenemez.
* **B4 — Dışlanan 18 ekonominin etkisi.** Yemen, Venezuela, Güney Sudan, Kuzey Kore gibi ekonomiler dışlandı. Seçilim yanlılığının yönü ve büyüklüğü bilinmiyor.
* **B5 — Ülke içi değişimin ölçümü.** WPP kaynaklı serilerde yıllık değişimler kısmen modelle üretiliyor. Bu yüzden iki yönlü sabit etkiler eğimi, gerçek ölüm değişimi kadar BM'nin düzleştirme varsayımlarını da yansıtıyor olabilir. Bu iki etki birbirinden ayrıştırılamıyor.

## 4. Düzeltilmesi gereken metodolojik noktalar

Bunlar düzeltilmedi. Denetim kapsamında yeni analiz eklenmedi; aşağıdakiler öneri olarak duruyor.

1. **Veri sürümü sabitlenmeli ve raporlanmalı.** Ülke içi bulgu, veri sürümüne ülkeler arası bulgudan çok daha duyarlı (Bölüm 5). Sonuçlar "WDI 2026-10-08 sürümü" etiketiyle sunulmalı. Eski sürümle elde edilen tahmin, ana metinde duyarlılık sonucu olarak gösterilmeli. Şu an yalnızca README ve sınırlılıklar bölümünde geçiyor.
2. **Bayrak kuralları iyileştirilmeli.** "Geçici şok" kuralı (`add_flags`, s.175) normal değerleri de yakalıyor. Seriler arası revizyon farkına dayanan bir kural veya CAF'ı açıkça dışlayan bir ana duyarlılık analizi daha savunulabilir olur.
3. **Etkili gözlem tanımı birleşik.** `diagnostics` (s.216–217) Cook D > 4/n ölçütünü ve |studentize artık| > 3 ölçütünü "veya" ile birleştiriyor. Kaldıraç ve DFBETAS hesaplanıyor ama seçimde kullanılmıyor. Bu kural keyfî, raporda bir kural seçimi olduğu açıkça yazılmalı.
4. **t dağılımı tercihi.** n = 197 ve G = 199 için z ile t arasındaki fark ihmal edilebilir. Yine de kümelenmiş çıkarımda `use_t=True` (t(G−1) dağılımı) daha yaygın bir standarttır.
5. **Nüfus ağırlıklı analiz yok.** Eşit ağırlık açıkça belirtildi, ancak nüfus ağırlıklı karşılaştırma hâlâ eksik.
6. **Eğim değişimi testi doğrusal bir zaman eğilimi varsayıyor.** Eğimin yıllara göre doğrusal olmayan biçimde değişmesi bu testle yakalanmaz. Yıllık kesit grafiği (Şekil 6) bunu görsel olarak destekliyor, ama ayrıca test edilmedi.
7. **Gecikmeli etkiler incelenmedi.** Ülke içi modeller gelirin aynı yıldaki ilişkisini ölçüyor. Etki birikerek ortaya çıkıyorsa, aynı yıl ilişkisi onu küçümser.

## 5. Duyarlılık analizi sonuçları

Kaynak: `reports/audit/sensitivity_summary.csv`. Model B eğimi ve iki yönlü sabit etkiler (FE) eğimi, %95 GA ile.

| Analiz | n (2023) | Model B eğimi 2023 [GA] | R² (B) | Spearman | Between | İki yönlü FE [GA] | Eğim değişimi / yıl (p) |
|---|---|---|---|---|---|---|---|
| Temel | 197 | 5,27 [4,85; 5,68] | 0,742 | 0,872 | 6,06 | 1,55 [0,49; 2,61] | −0,041 (0,001) |
| CAF tamamen çıkarılmış | 196 | 5,25 [4,82; 5,67] | 0,735 | 0,870 | 5,96 | 1,49 [0,43; 2,55] | −0,045 (<0,001) |
| İşaretli değerler çıkarılmış | 197 | 5,27 | 0,742 | 0,872 | 6,01 | 1,44 [0,38; 2,50] | −0,047 (<0,001) |
| 24 egemen olmayan ekonomi çıkarılmış¹ | 184 | 5,32 [4,90; 5,74] | 0,744 | 0,878 | 6,20 | 1,54 [0,39; 2,68] | −0,044 (0,001) |
| 9 etkili ülke çıkarılmış | 188 | 5,42 [5,09; 5,75] | 0,789 | 0,894 | – | – | – |
| Dengeli panel (189 ekonomi) | 189 | 5,31 [4,90; 5,72] | 0,749 | 0,881 | 6,14 | 1,33 [0,31; 2,35] | −0,042 (0,001) |
| 2020–2022 çıkarılmış | – | – | – | – | 6,09 | 1,60 [0,49; 2,72] | −0,041 (<0,001) |
| 2023 yerine 2024 kesiti | 195 | 5,26 [4,84; 5,67] | 0,744 | 0,877 | – | – | – |
| En zengin 10 ekonomi çıkarılmış | 187 | 5,38 [4,92; 5,84] | 0,725 | 0,863 | – | – | – |

¹ Liste elle derlendi: Aruba, Bermuda, Hong Kong, Makao, Porto Riko, Grönland, Kosova, Batı Şeria ve Gazze vb. Bunların 14'ü analiz örnekleminde. Liste API'den gelmiyor, `audit/run_audit.py` dosyasında açıkça yazılı.

**Veri sürümü duyarlılığı** (yaşam beklentisi için Mart 2025 sürümü ile güncel sürüm karşılaştırması, GSYH aynı tutuldu):

| | Güncel sürüm | Mart 2025 sürümü |
|---|---|---|
| 2022 kesiti Model B eğimi [GA], n = 194 | 5,53 [4,62; 6,45] | 5,52 [5,05; 5,99] |
| 2022 kesiti R² (B) | 0,649 | 0,698 |
| 2000–2022 iki yönlü FE eğimi [GA], n = 4.436 | **1,84 [0,67; 3,00]** | **1,55 [0,40; 2,69]** |

**Uzun farklar, CAF ile ve CAF olmadan:**

| Dönem | Örneklem | n | Eğim [GA] | p | R² |
|---|---|---|---|---|---|
| 2000–2019 | tümü | 192 | 2,25 [0,59; 3,91] | 0,008 | 0,042 |
| 2000–2019 | CAF hariç | 191 | 1,83 [0,38; 3,29] | 0,014 | 0,033 |
| 2000–2023 | tümü | 191 | 1,27 [−0,15; 2,69] | 0,080 | 0,015 |
| 2000–2023 | CAF hariç | 190 | 1,36 [−0,06; 2,78] | 0,061 | 0,017 |

**Duyarlılık analizlerinin özeti:**

* **Kesitsel bulgular çok sağlam.** Hiçbir senaryoda Model B eğimi 5,25–5,42 aralığının dışına çıkmıyor. Log modelin doğrusal modele üstünlüğü de her senaryoda korunuyor.
* **Eğimin zamanla azalması sağlam.** Tüm senaryolarda yılda −0,041 ile −0,047 arası, p ≤ 0,001.
* **Ülke içi eğim her zaman küçük ve pozitif** (1,33–1,84), ama belirsizliği büyük ve veri sürümüne duyarlı. Sürüm değişikliği tek başına eğimi yaklaşık 0,3 kaydırıyor; bu, kendi standart hatasının yarısı kadar.
* **2000–2019 uzun fark eğiminin bir kısmı CAF'tan geliyor.** CAF çıkarılınca 2,25'ten 1,83'e iniyor. Bunun nedeni, CAF'ın 2019 değerinin (31,5) revizyonla sonradan eklenmiş bir değer olması. "Ülke içi ilişki, ülkeler arası ilişkinin küçük bir kesridir" yorumu ise değişmiyor.

## 6. GitHub'a yayımlanmaya hazır olma değerlendirmesi

**Karar: Koşullu olarak hazır.** Hesaplama hatası bulunmadı. Yorum ve belgeleme hataları düzeltildi. Yayından önce şunlar gerekli:

| Durum | Madde |
|---|---|
| ✅ | Tüm ana sayılar bağımsız yöntemlerle birebir yeniden üretildi |
| ✅ | `pytest --run-network`: 38/38 başarılı (denetim sonrası yeniden çalıştırıldı). *Güncelleme: arşiv testleriyle birlikte 44/44.* |
| ✅ | Raporlardaki hatalı ifadeler düzeltildi (H1–H7) |
| ⚠️ | Düzeltilen raporları sizin okumanız gerekiyor. Özellikle CAF ve veri sürümü ile ilgili bölümler |
| ⚠️ | Kod lisansı ve yazar bilgisi: *Güncelleme. `LICENSE` (MIT, kod), `LICENSE-DOCS.md` (CC BY 4.0, özgün metinler) ve `DATA_LICENSE.md` (Dünya Bankası verisi) taslakları eklendi. Yazar alanı hâlâ boş, bkz. `reports/release_readiness_report_tr.md`.* |
| ✅ | *Güncelleme: Arşiv kararı uygulandı. 202503 ve 202504 kayıpsız gzip olarak saklanıyor (0,37 MB) ve SHA-256 ile doğrulanıyor. 202412 yalnızca yerel yedekte duruyor. CAF tablosunda artık 202412 sütunu yok; o sütunun değerleri 202503 ile aynıydı.* Önceki not: `data/raw/archive/` klasörü (yaklaşık 18 MB) depoya eklenecek mi, karar verilmeli. Denetimin tekrar üretilmesi için gerekli; dışarıda bırakılırsa betik `--refetch` ile yeniden indirir |
| ⚠️ | Notebook denetim bulgularını içermiyor. Bu bir tutarsızlık değil, ama notebook'a denetim raporuna bir bağlantı eklenebilir |
| ⚠️ | Temiz bir sanal ortamda kurulum hâlâ denenmedi |
| ❌ | Bölüm 4'teki metodolojik öneriler uygulanmadı. Yayını engellemezler, ama "bilinen sınırlılıklar" olarak açıkça yazılı kalmalılar |

## 7. Öğrencinin anlaması gereken beş temel istatistiksel kavram

1. **Ülkeler arası ve ülke içi varyasyon farklı sorular yanıtlar.** Ülkeler arası eğim yaklaşık 6, ülke içi eğim yaklaşık 1,5. "Zengin ülkeler daha uzun yaşar" ile "bir ülke zenginleşince daha uzun yaşar" aynı cümle değildir. Birinciden ikincisini çıkarmak bir ekolojik çıkarım hatasıdır.
2. **Gözlemler bağımsız değilse standart hatalar yanıltır.** Aynı ülke 25 kez gözlemlendiğinde 4.916 bağımsız gözleminiz yoktur, yaklaşık 199 bağımsız kümeniz vardır. Kümelenmiş standart hatalar bu yüzden kullanılır. Denetimde bu hesap elle yeniden yapıldı ve statsmodels sonucuyla birebir tuttu.
3. **Ortak eğilimler sahte ilişki üretir.** Yıl etkileri olmayan ülke sabit etkili modelin eğimi 7,05, yıl etkileri eklendiğinde 1,55. Birlikte artan iki seri, aralarında bağ olmasa da güçlü biçimde ilişkili görünür.
4. **Dönüşüm yorumu değiştirir, sıralamayı değiştirmez.** Logaritma Pearson r'yi 0,75'ten 0,86'ya çıkarır, Spearman ρ'yu değiştirmez. Log tabanı (ln veya log₁₀) yalnızca eğimin birimini değiştirir (oran = ln 10), R² aynı kalır.
5. **Veri de bir tahmindir ve değişir.** Aynı ülkenin aynı yılı için "resmî" yaşam beklentisi bir sürümde 55,0, sonraki sürümde 31,5 olabilir. Tekrar üretilebilir bir araştırma, verinin hangi sürümünün kullanıldığını kaydeder ve sonuçların bu sürüme ne kadar duyarlı olduğunu raporlar.
