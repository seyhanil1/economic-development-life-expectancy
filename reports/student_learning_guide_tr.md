# Öğrenci Rehberi: Bu Araştırmadan Ne Öğrenebiliriz?

**Yazar:** Seyhan Anıl Kaya · İstatistik Bölümü, Fırat Üniversitesi

*İkinci sınıf istatistik öğrencileri için hazırlanmıştır. Örneklerdeki sayılar bu projenin gerçek sonuçlarıdır (2023 kesiti, 197 ülke).*

---

## 1. Bu araştırmada Pandas ne yaptı?

Pandas, Python'da tablo biçimindeki verilerle çalışmayı sağlayan bir kütüphanedir. Excel'deki satır ve sütunlara benzeyen bu tabloya **DataFrame** denir. Bu projede Pandas şu işleri yaptı:

| İş | Pandas'ta karşılığı | Projedeki örnek |
|---|---|---|
| API'den gelen iç içe JSON kayıtlarını düz tabloya çevirmek | `pd.DataFrame(...)` | `clean_data.records_to_frame` |
| Veri tiplerini düzeltmek (yıl metin değil tam sayı olmalı) | `pd.to_numeric`, `.astype` | `"2023"` → `2023` |
| Tekrarlanan kayıtları bulmak | `.duplicated(["iso3","year"])` | Gelir gruplarının boş ISO3 kodları 104 sahte tekrar üretiyordu |
| İki göstergeyi ülke-yıl anahtarıyla birleştirmek | `pd.merge(..., on=["iso3","year"], validate="one_to_one")` | GSYH ve yaşam beklentisi tek tabloda |
| Eksik değerleri saymak | `.isna().sum()` | 509 ülke-yılda GSYH eksik |
| Gruplara göre özet çıkarmak | `.groupby("year").agg(...)` | Yıllara göre ülke sayısı |
| Filtrelemek | `df[df["in_analysis"]]` | Analiz örneklemi |

**Önemli ders:** `validate="one_to_one"` gibi küçük bir parametre, birleştirme sırasında bir ülkenin yanlışlıkla iki kez sayılmasını engeller. Veri temizliğindeki hatalar çoğunlukla sessizdir: kod hata vermeden çalışır, sonuç yine de yanlış olur. Bu yüzden her adımda sayıları kontrol etmek gerekir.

## 2. API'den veri çekmek ne anlama geliyor?

**API** (Application Programming Interface, uygulama programlama arayüzü), bir programın başka bir sistemden belirli kurallarla veri istemesini sağlayan bir arayüzdür. Web sitesine girip "CSV indir" düğmesine basmak yerine, kod şu adrese bir istek gönderir:

```
https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.IN?format=json&date=2000:2025&page=1
```

Sunucu da yapılandırılmış bir yanıt (JSON) döndürür. Dikkat edilmesi gerekenler:

* **Sayfalandırma:** Sunucu 6.916 kaydı tek seferde göndermez, örneğin 1.000'erlik sayfalara böler. Tüm sayfaları istemek ve toplam kayıt sayısının tuttuğunu doğrulamak gerekir.
* **Hata yönetimi:** İnternet kesilebilir, sunucu geçici olarak yanıt vermeyebilir (HTTP 503). Kod birkaç kez yeniden denemeli, kalıcı hatalarda ise açıkça durmalıdır.
* **Tekrar üretilebilirlik:** Aynı kodu bir yıl sonra çalıştıran kişi, Dünya Bankası verileri revize ettiği için farklı sayılar alabilir. Bu nedenle ham yanıtlar, indirme tarihi ve sürüm bilgisi saklanır.

## 3. Pearson ve Spearman arasındaki fark nedir?

* **Pearson r** iki değişken arasındaki **doğrusal** ilişkinin gücünü ölçer. Değerlerin kendisini kullanır. Bu yüzden uç değerlerden ve eğri ilişkilerden etkilenir.
* **Spearman ρ** önce değerleri sıralamaya çevirir (en küçüğe 1, sonrakine 2, ...), sonra bu sıralar arasında Pearson korelasyonunu hesaplar. **Monoton** ilişkiyi ölçer: "biri artınca diğeri de artıyor mu?" sorusunu yanıtlar, ama ilişkinin düz bir çizgi olmasını gerektirmez.

Bu projede (2023):

| | Pearson r | Spearman ρ |
|---|---|---|
| GSYH – yaşam beklentisi | 0,749 | 0,872 |
| ln(GSYH) – yaşam beklentisi | 0,861 | 0,872 |

Spearman iki satırda da aynıdır, çünkü logaritma sıralamayı değiştirmez: en yoksul ülke yine en yoksul kalır. Pearson ise logaritmadan sonra artar, çünkü ilişki logaritmik ölçekte düz bir çizgiye çok daha yakındır. **İki katsayının birbirinden belirgin biçimde farklı olması, ilişkinin monoton ama doğrusal olmadığına dair bir işarettir.**

## 4. Logaritmik dönüşüm neden kullanıldı?

Üç nedeni var:

1. **Çarpıklık:** Kişi başına GSYH 1.033 \$ (Burundi) ile 130.297 \$ (Singapur) arasında değişir. Dağılım sağa çarpıktır: birkaç çok zengin ülke ortalamayı yukarı çeker. Logaritma bu uzun kuyruğu sıkıştırır.
2. **Doğrusallık:** Saçılım grafiğinde ilişki, düzey ölçeğinde bükülür. Önce dik yükselir, sonra yataylaşır. Log ölçeğinde neredeyse düz bir çizgiye dönüşür.
3. **Anlamlı yorum:** Logaritmik modelde katsayı, *mutlak* değil *oransal* farklara karşılık gelir. 1.000 \$ ek gelir yoksul bir ülke için çok büyük, zengin bir ülke için çok küçük bir değişimdir. Yüzde değişim ise iki ülke için de aynı anlama gelir.

**Uyarı:** Logaritma yalnızca pozitif sayılar için tanımlıdır. ln(0) tanımsızdır (−∞), ln(−5) gerçek sayılarda yoktur. Bu nedenle kod, sıfır veya negatif değerleri logaritma almadan önce ayırır.

## 5. Regresyon katsayıları nasıl yorumlanır?

**Model A (doğrusal):** LE = 68,08 + 0,197 × (GSYH / 1.000)

→ Kişi başına GSYH'si 1.000 \$ daha yüksek olan ülkelerin yaşam beklentisi *ortalama olarak* 0,197 yıl (yaklaşık 2,4 ay) daha yüksektir. Bu model, bu farkın her gelir düzeyinde aynı olduğunu varsayar.

**Model B (log-doğrusal):** LE = 22,57 + 5,267 × ln(GSYH)

→ ln(GSYH)'deki 1 birimlik fark, gelirin yaklaşık 2,72 katı olması demektir. Daha kullanışlı bir çeviri şudur:
* Gelir %10 daha yüksek → 5,267 × ln(1,10) ≈ **0,50 yıl** daha yüksek yaşam beklentisi
* Gelir iki katı → 5,267 × ln(2) ≈ **3,65 yıl** daha yüksek yaşam beklentisi

**Sabit terim (22,57):** ln(GSYH) = 0, yani GSYH = 1 \$ olduğunda beklenen değerdir. Böyle bir ülke yoktur, dolayısıyla sabit terimin tek başına bir anlamı yoktur. Çizginin yüksekliğini ayarlayan teknik bir parametredir.

**Güven aralığı [4,85; 5,68]:** Aynı yöntem birçok örneklemde tekrarlansaydı, bu şekilde kurulan aralıkların %95'i gerçek eğimi içerirdi. Sıfırdan çok uzak olması, ilişkinin rastlantısal olma olasılığının çok düşük olduğunu gösterir.

**Unutmayın:** "Yaşam beklentisi 3,65 yıl artar" demek yanlıştır. Doğru ifade şudur: "Geliri iki katı olan ülkelerin yaşam beklentisi ortalama 3,65 yıl daha yüksektir." Birincisi bir müdahalenin etkisinden söz eder, ikincisi ülkeleri karşılaştırır.

## 6. R² neyi anlatır ve neyi anlatmaz?

**Anlattığı:** Bağımlı değişkendeki toplam değişkenliğin modelce açıklanan payı. Model B'de R² = 0,742: ülkeler arasındaki yaşam beklentisi farklarının %74'ü ln(GSYH) ile doğrusal olarak ilişkilidir. Basit regresyonda R², Pearson r'nin karesidir (0,861² ≈ 0,742).

**Anlatmadığı:**
* **Nedensellik:** Yüksek R², gelirin yaşam süresini *belirlediği* anlamına gelmez.
* **Doğru model:** R²'si yüksek bir model de yanlış biçimde kurulmuş olabilir. Artık grafikleri yine de incelenmelidir.
* **Tahmin doğruluğu:** R² = 0,74 iken bile tipik tahmin hatası (RMSE) 3,6 yıldır. Tek bir ülkenin yaşam beklentisini tahmin etmek için bu oldukça büyük bir hatadır.
* **Farklı bağımlı değişkenler veya örneklemler arasında karşılaştırma:** R² ancak aynı bağımlı değişkene sahip, aynı gözlemler üzerinde kurulmuş modeller arasında karşılaştırılabilir. Bu projede Model A ve B bu yüzden aynı 197 ülke üzerinde kuruldu.
* **Zaman içinde değişim:** Uzun fark modelinde R² = 0,04'tür. Gelir değişimi, yaşam beklentisi değişimlerinin çok küçük bir kısmını açıklar. Bu, ülkeler arası R²'den bambaşka bir sonuçtur.

## 7. Bir modelin varsayımları nasıl kontrol edilir?

| Varsayım | Neden önemli? | Nasıl kontrol edilir? | Bu projede |
|---|---|---|---|
| Doğrusallık (doğru fonksiyon biçimi) | Yanlış biçim, katsayıları sistematik olarak yanıltır | Artık–tahmin grafiği; RESET testi | Model A: ters U örüntüsü, RESET p < 10⁻¹⁷. Model B: örüntü yok, p = 0,36 |
| Sabit varyans | İhlal edilirse standart hatalar yanlış olur | Artıkların yayılımına bakmak; Breusch–Pagan; White testi | Model B: p ≈ 0,15–0,16. Yine de dayanıklı (HC3) standart hata kullanıldı |
| Hataların normalliği | Küçük örneklemlerde testler ve aralıklar buna dayanır | Q-Q grafiği; Shapiro–Wilk; Jarque–Bera | Normal değil (sola çarpık). n = 197 olduğundan katsayı çıkarımı büyük ölçüde etkilenmez |
| Gözlemlerin bağımsızlığı | İhlal edilirse standart hatalar çok küçük çıkar | Veri yapısını düşünmek: aynı ülke birçok yılda var mı? | Panelde aynı ülke 25 kez yer alır → standart hatalar ülke düzeyinde kümelendi |
| Etkili gözlemler | Birkaç nokta sonucu belirleyebilir | Kaldıraç, Cook uzaklığı; o noktalar çıkarılarak yeniden kestirim | 9 etkili ülke; çıkarıldıklarında eğim 5,27 → 5,42 |

Testler tek başına yeterli değildir. Büyük örneklemlerde önemsiz sapmalar da "anlamlı" çıkar, küçük örneklemlerde önemli sapmalar gözden kaçabilir. **Grafiklere her zaman bakın.**

## 8. Bu analizden neden doğrudan nedensel sonuç çıkaramayız?

1. **Karıştırıcı değişkenler:** Eğitim, kurumlar, coğrafya ve hastalık yükü hem geliri hem sağlığı etkileyebilir. İkisi de bu ortak nedenlerden dolayı birlikte hareket ediyor olabilir.
2. **Ters nedensellik:** Sağlıklı insanlar daha üretken olabilir. Bu durumda gelir sağlığın bir *sonucu* olur.
3. **Ekolojik yanılgı:** Ülke ortalamaları arasındaki ilişki bireyler için geçerli olmayabilir.
4. **Gözlemsel veri:** Ülkelere rastgele gelir atayan bir deney yapmadık (yapılamaz da).
5. **Bu projedeki somut kanıt:** Ülkeler arası eğim yaklaşık 6'dır. Ülkelerin kendi gelir artışlarına bakıldığında, ortak küresel eğilim arındırıldıktan sonra eğim yalnızca yaklaşık 1,5'tir. Ülkeler arası ilişki nedensel etkiyi doğrudan yansıtsaydı, bu iki sayının birbirine çok daha yakın olması beklenirdi.

---

## Alıştırmalar

*Bu alıştırmaların cevapları bu dosyada verilmemiştir. Proje dosyalarını kullanarak kendiniz çözün.*

**Alıştırma 1 — Veri tanıma.**
`data/processed/coverage_by_country.csv` dosyasını Pandas ile açın. 2000–2024 döneminin tamamında (25 yıl) kullanılabilir veriye sahip ülke sayısını bulun. Kaç ülkenin en az bir yılı eksik? Eksik yılı olan ülkelerin bölgelere (`region`) göre dağılımını, `country_year_panel.csv` dosyasıyla birleştirerek çıkarın.

**Alıştırma 2 — Korelasyonu elle hesaplama.**
`data/processed/analysis_sample.csv` dosyasından 2010 yılı verilerini seçin. Pearson korelasyonunu yalnızca NumPy ile ve formülü kullanarak (kovaryans / standart sapmaların çarpımı) hesaplayın. Sonucu `scipy.stats.pearsonr` çıktısıyla karşılaştırın. Ardından Spearman ρ'yu önce `rank()` ile sıralar oluşturup sonra Pearson uygulayarak hesaplayın.

**Alıştırma 3 — Katsayı yorumu.**
Model B'nin 2023 eğimini kullanarak şunu hesaplayın: kişi başına geliri 4.000 \$ olan bir ülke ile 12.000 \$ olan bir ülke arasında beklenen yaşam beklentisi farkı nedir? Aynı hesabı Model A ile yapın. İki sonuç neden farklı? Hangisine neden daha çok güvenirsiniz?

**Alıştırma 4 — Duyarlılık analizi.**
2000 yılı kesitinde Model B'yi kurun ve Cook uzaklığı 4/n'yi aşan ülkeleri bulun. Bu ülkeler 2023'teki listeyle aynı mı? Bu ülkeler çıkarıldığında eğim yüzde kaç değişiyor?

**Alıştırma 5 — Ülke içi ve ülkeler arası.**
`reports/tables/long_difference_2000-2019.csv` dosyasını açın. Yaşam beklentisi en çok artan 10 ülkeyi ve bu ülkelerin gelir değişimini listeleyin. Bu ülkelerin çoğu hangi bölgeden? Bu gözlem, gelir dışındaki hangi faktörlerin yaşam beklentisini değiştirmiş olabileceği konusunda ne düşündürüyor? (İpucu: bu bir hipotezdir, verideki bir değişkenle test edilmiş bir sonuç değildir. Cevabınızda bu ayrımı yapın.)
