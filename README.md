# Test Takip Dashboard

Python Flask + SQLite ile geliştirilmiş, localhost üzerinde çalışan Türkçe test takip uygulaması.

## Özellikler

| Modül | Açıklama |
|---|---|
| **Dashboard** | Toplam / Başarılı / Başarısız / Engellendi / Çalıştırılmadı sayıları, tamamlanma ve başarı oranları, durum dağılımı, paket ve modül bazında grafikler, son başarısız testler, yaklaşan görevler. Pakete ve modüle göre filtrelenebilir. |
| **Test Paketleri** | Paket oluşturma, düzenleme, silme. Her paket için ayrı ilerleme çubuğu, tamamlanma ve başarı oranı. **Birden fazla Excel dosyasını aynı anda sürükleyip bırakarak** paket ekleme/güncelleme (dosya adı = paket adı) ve her paket kartında “Excel ile güncelle”. |
| **Test Senaryoları** | Senaryo ekleme, düzenleme, silme. Test kodu, modül, adımlar, beklenen sonuç, gerçekleşen sonuç, durum, hata linki, test eden alanları. Listeden tek tıkla durum değiştirme, toplu durum güncelleme / silme, sayfalama. |
| **Filtreleme** | Test paketi, modül, durum ve serbest metin araması. |
| **Excel** | `.xlsx` içe aktarma (sayfa + başlık satırı seçimi, otomatik tahminli kolon eşleştirme, mevcut testleri güncelleme), filtreli Excel dışa aktarma (Özet sayfası dahil), örnek şablon. |
| **To-Do Listesi** | Görev ekleme, düzenleme, silme, tamamlandı işaretleme, öncelik (Kritik/Yüksek/Orta/Düşük), son tarih, gecikme vurgusu, önceliğe/tarihe göre sıralama. |
| **Kanban** | Görevler için Yapılacak / Devam Ediyor / İncelemede / Tamamlandı sütunları; sürükle-bırak ile taşıma ve sıralama, sütundan hızlı görev ekleme. Dokunmatik ekranlarda kart menüsündeki “Taşı” kullanılır. |
| **Tema** | Polsan renk paleti (lacivert / mavi / lime, Montserrat + Inter). Açık / koyu tema (kenar çubuğundaki “Tema değiştir”). |

### Excel'den hızlı paket ekleme (Test Paketleri sayfası)

- Bir veya birden fazla `.xlsx` dosyasını yükleme alanına bırakın. Her dosya, **dosya adıyla** bir paket olur; aynı adlı paket varsa güncellenir.
- Kolonlar başlıklardan otomatik tanınır, tüm dolu sayfalar aktarılır; birden fazla sayfa varsa her sayfa bir modül olur.
- Testler Test Kodu ile, yoksa Test Adı + Modül ile eşleşir — aynı dosyayı tekrar yüklemek kopya oluşturmaz.
- Paketi yeniden adlandırdıysanız güncel dosyayı o paketin kartındaki **“Excel ile güncelle”** ile yükleyin (dosya adı fark etmez).
- Kolonları tanınmayan dosyalar sonuç ekranında belirtilir; bunlar için Excel sayfasındaki eşleştirmeli içe aktarmayı kullanın.

### Oran hesapları

- **Tamamlanma Oranı** = (Başarılı + Başarısız + Engellendi) / Toplam test × 100
- **Başarı Oranı** = Başarılı / (Başarılı + Başarısız + Engellendi) × 100 — yani çalıştırılan testler içindeki başarı yüzdesi

## Gereksinimler

- Windows 10/11
- Python 3.10 veya üzeri (`python --version` ile kontrol edin)
- İnternet bağlantısı (Bootstrap, Bootstrap Icons ve Chart.js CDN üzerinden yüklenir)

## Kurulum ve Çalıştırma (Windows)

### Yöntem 1 — Tek tık

Proje klasöründeki **`run.bat`** dosyasına çift tıklayın. İlk çalıştırmada sanal ortamı oluşturur ve bağımlılıkları kurar, ardından uygulamayı başlatır. Tarayıcıda **http://127.0.0.1:5000** adresini açın.

### Yöntem 2 — PowerShell ile adım adım

```powershell
# 1) Proje klasörüne gidin
cd C:\Users\<kullanici>\Desktop\TestTakipDashboard

# 2) Sanal ortam oluşturun (yalnızca ilk sefer)
python -m venv .venv

# 3) Sanal ortamı etkinleştirin
.\.venv\Scripts\Activate.ps1

# 4) Bağımlılıkları kurun (yalnızca ilk sefer / requirements değişince)
pip install -r requirements.txt

# 5) Uygulamayı başlatın
python app.py
```

Tarayıcıda **http://127.0.0.1:5000** adresine gidin. Durdurmak için terminalde `CTRL + C`.

> **PowerShell “running scripts is disabled” hatası verirse** (adım 3), bir kez şunu çalıştırın:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
> ya da etkinleştirmeden doğrudan çalıştırın: `.\.venv\Scripts\python.exe app.py`

### Komut İstemi (cmd) kullanıyorsanız

```bat
cd %USERPROFILE%\Desktop\TestTakipDashboard
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python app.py
```

## İş Arkadaşlarıyla Paylaşma (yerel ağ / VPN)

Uygulama sizin bilgisayarınızda çalışır; aynı ağdaki iş arkadaşlarınız tarayıcıdan bağlanır ve **hepiniz aynı veriyi** görüp düzenlersiniz.

1. **Güvenlik duvarını açın (bir kez):** `guvenlik_duvari_ac.bat` dosyasına çift tıklayın, yönetici iznini onaylayın. Yalnızca *Etki Alanı* ve *Özel* ağlar için TCP 5000 portunu açar (kafe/otel gibi *Genel* ağlarda kapalı kalır).
2. **Paylaşım modunda başlatın:** `paylas.bat` dosyasına çift tıklayın.
   - İlk seferde bir **paylaşım şifresi** belirlemeniz istenir (en az 6 karakter).
   - Pencerede iş arkadaşlarınıza vereceğiniz adres yazar, ör. `http://192.168.1.3:5000`.
3. İş arkadaşınız bu adresi açar ve şifreyi girer. Oturum 12 saat açık kalır; kenar çubuğunda **Çıkış yap** düğmesi bulunur.

Notlar:
- Uygulamanın çalıştığı bilgisayardan (`127.0.0.1`) şifre sorulmaz.
- `paylas.bat` debug modu kapalı, çok kullanıcılı **waitress** sunucusuyla çalışır. `run.bat` ise yalnızca sizin bilgisayarınızdan erişilen geliştirme modudur; ikisini aynı anda çalıştırmayın (aynı portu kullanırlar).
- Bilgisayarınız kapanır veya pencere kapatılırsa iş arkadaşlarınız erişemez. Sürekli erişim için uygulamayı şirket içi bir sunucuya/VM'e kurun (adımlar aynı).
- Şifreyi değiştirmek: `.\.venv\Scripts\python.exe sifre_belirle.py` · Port değiştirmek: `$env:PORT="8080"; .\.venv\Scripts\python.exe serve.py`
- Uygulamayı **internete açmayın** (ngrok vb.) — test notlarında kurum içi bilgiler bulunur.

### Örnek veri (isteğe bağlı)

Uygulamayı denemek için boş bir veritabanına örnek paket, senaryo ve görev ekler (veri varsa hiçbir şey yapmaz):

```powershell
python seed_demo.py
```

## Excel İçe Aktarma

1. **Excel** sayfasından `.xlsx` dosyanızı yükleyin (`.xls` dosyalarını önce Excel'de `.xlsx` olarak kaydedin).
2. Referans sayfayı ve başlık satırını seçin.
3. Excel kolonlarını alanlarla eşleştirin. Başlıklar otomatik tahmin edilir (ör. “Test Kodu”, “Kontrol Edilecek Alan”, “Yapılacak İşlem”, “Beklenen Sonuç”, “Durum”, “Hata / Not”…).
4. **Durum değerlerini eşleştirin:** Durum kolonundaki her farklı değer (ör. “Geçti”, “Uygulanamaz”) listelenir; her birinin hangi duruma karşılık geleceğini siz seçersiniz. Otomatik tanınmayanlar “tanınmadı” rozetiyle işaretlenir.
5. **Çok sayfalı dosyalar:** Birden fazla sayfayı tek seferde aktarabilirsiniz. Diğer sayfalarda kolonlar başlık adına göre bulunur. “Modül = sayfa adı” seçeneğiyle her sayfa ayrı modül olur (`01 Üyelik Ana Sayfa` → `Üyelik Ana Sayfa`).
6. Hedef paketi seçin: tüm satırlar tek bir pakete **veya** “Test Paketi” kolonundaki pakete (olmayanlar otomatik oluşturulur).
7. Mevcut testler **Test Kodu** veya **Test Adı + Modül** ile, aynı paket içinde eşleştirilir:
   - “Eşleşen mevcut testleri güncelle” açıksa eşleşenler güncellenir, kapalıysa atlanır.
   - “Boş hücreler mevcut değerlerin üzerine yazılmasın” açıksa Excel'de boş olan alanlar korunur.
   - Eşleşmeyen satırlar yeni senaryo olarak eklenir.

Tanınan durum değerleri: `Başarılı / Passed / Pass / Geçti`, `Başarısız / Failed / Fail / Kaldı`, `Engellendi / Blocked / Bloke`, `Çalıştırılmadı / Uygulanamaz / Not Run`. Tanınmayan değerler “Çalıştırılmadı” kabul edilir.

**İpucu:** Dışa aktarılan dosya içe aktarma ile aynı başlıkları kullanır. Dışa aktarın → Excel'de durumları/sonuçları güncelleyin → tekrar içe aktarın.

## Proje Yapısı

```
TestTakipDashboard/
├── app.py              # Flask uygulaması ve tüm sayfalar (route'lar)
├── database.py         # SQLite bağlantısı ve şema
├── constants.py        # Durum / öncelik etiketleri, renkler, Excel kolon takma adları
├── excel_utils.py      # openpyxl ile içe/dışa aktarma
├── seed_demo.py        # İsteğe bağlı örnek veri
├── requirements.txt
├── run.bat             # Windows için tek tık başlatma
├── templates/          # Jinja2 şablonları (Bootstrap 5)
├── static/
│   ├── css/style.css
│   └── js/app.js, dashboard.js (Chart.js grafikleri)
├── instance/           # test_takip.db (ilk çalıştırmada otomatik oluşur)
└── uploads/            # Geçici Excel yüklemeleri (içe aktarma sonrası silinir)
```

## Veriler ve Yedekleme

Tüm veriler `instance\test_takip.db` dosyasında tutulur. Yedek almak için **uygulamayı durdurup** `instance` klasörünü kopyalayın (çalışırken `test_takip.db-wal` / `-shm` yardımcı dosyaları da oluşur; `settings.json` paylaşım şifresinin özetini ve oturum anahtarını içerir — başkalarıyla paylaşmayın). Farklı bir veritabanı dosyası kullanmak için başlatmadan önce:

```powershell
$env:TEST_TAKIP_DB = "D:\yedek\baska.db"
python app.py
```

## Notlar

- Uygulama yalnızca `127.0.0.1` üzerinde dinler; ağdaki diğer bilgisayarlardan erişilemez.
- Geliştirme sunucusu (`debug=True`) yerel kullanım içindir. Port 5000 doluysa `app.py` dosyasının sonundaki `port=5000` değerini değiştirin.
