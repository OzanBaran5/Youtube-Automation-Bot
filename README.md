<div align="right">
  <a href="README.en.md">🇬🇧 English</a>
</div>

# 🎬 YouTube Shorts Otomatik Üretim Pipeline

Finans okuryazarlığı ve kişisel gelişim konularında **günlük, tam otomatik** 40-55 saniyelik dikey (9:16) YouTube Shorts videosu üreten ve kanalınıza yükleyen Python pipeline.

---

## 📋 İçindekiler

1. [Sistem Gereksinimleri](#-sistem-gereksinimleri)
2. [FFmpeg Kurulumu (Windows)](#-ffmpeg-kurulumu-windows)
3. [Python Kurulumu & Bağımlılıklar](#-python-kurulumu--bağımlılıklar)
4. [API Anahtarları Kurulumu](#-api-anahtarları-kurulumu)
5. [Google OAuth2 Kurulumu](#-google-oauth2-kurulumu)
6. [Proje Yapısı](#-proje-yapısı)
7. [Kullanım](#-kullanım)
8. [İlk Çalıştırma & OAuth Yetkilendirme](#-i̇lk-çalıştırma--oauth-yetkilendirme)
9. [Windows Task Scheduler ile Otomatik Çalıştırma](#-windows-task-scheduler-ile-otomatik-çalıştırma)
10. [Test Rehberi](#-test-rehberi)
11. [Sorun Giderme](#-sorun-giderme)

---

## 🖥 Sistem Gereksinimleri

- **İşletim Sistemi**: Windows 10/11 (64-bit)
- **Python**: 3.10 veya üstü ([python.org](https://www.python.org/downloads/))
- **FFmpeg**: Aşağıdaki kurulum adımlarına bakın
- **İnternet Bağlantısı**: API çağrıları ve video indirme için

---

## 🎞 FFmpeg Kurulumu (Windows)

> **⚠️ ÖNEMLİ**: FFmpeg kurulmadan video render ve Whisper altyazı adımları çalışmaz.

### Adım 1 — FFmpeg İndir

1. Tarayıcınızı açın ve şu adrese gidin:
   **https://github.com/BtbN/FFmpeg-Builds/releases**

2. En üstteki release'de (en güncel) şu dosyayı indirin:
   ```
   ffmpeg-master-latest-win64-gpl.zip
   ```
   *(yaklaşık 100-150 MB)*

   > Alternatif kaynak: **https://ffmpeg.org/download.html** → Windows → gyan.dev builds

### Adım 2 — ZIP Dosyasını Çıkar

1. İndirilen ZIP dosyasına sağ tıklayın → **"Tümünü Çıkar..."**
2. Çıkarma konumu olarak şunu girin (veya kopyalayın):
   ```
   C:\
   ```
3. **"Çıkar"** butonuna tıklayın.

4. Çıkarılan klasörün adı `ffmpeg-master-latest-win64-gpl` veya benzeri olacak.
   Bu klasörü **yeniden adlandırın**: `ffmpeg`

   Sonuç olarak şu yapıda olmalı:
   ```
   C:\ffmpeg\
     ├── bin\
     │   ├── ffmpeg.exe    ← Bu dosya önemli
     │   ├── ffprobe.exe
     │   └── ffplay.exe
     ├── doc\
     └── ...
   ```

### Adım 3 — PATH Ortam Değişkenine Ekle

1. **Win + R** tuşlarına basın → `sysdm.cpl` yazın → **Tamam**

2. **"Gelişmiş"** sekmesine tıklayın → **"Ortam Değişkenleri..."** butonuna tıklayın

3. Alt bölümde **"Sistem değişkenleri"** listesinde **`Path`** satırını bulun → üzerine çift tıklayın

4. Açılan pencerede sağ üstteki **"Yeni"** butonuna tıklayın

5. Şunu yazın:
   ```
   C:\ffmpeg\bin
   ```

6. **"Tamam"** → **"Tamam"** → **"Tamam"** diyerek tüm pencereleri kapatın

### Adım 4 — Kurulumu Doğrula

**Yeni** bir PowerShell veya Komut İstemi penceresi açın (mevcut pencereyi kapatıp yeniden açın):

```powershell
ffmpeg -version
```

Aşağıdaki gibi bir çıktı görmelisiniz:
```
ffmpeg version N-xxx-gxxxxxxx Copyright (c) 2000-2024 ...
```

✅ Bu çıktıyı görüyorsanız FFmpeg başarıyla kuruldu.

---

## 🐍 Python Kurulumu & Bağımlılıklar

### Adım 1 — Sanal Ortam Oluştur (Önerilir)

Proje klasöründe PowerShell açın:

```powershell
cd "c:\Users\pc\Desktop\youtube otomasyon"
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> **Not**: PowerShell'de script çalıştırma politikası hatası alırsanız:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### Adım 2 — Bağımlılıkları Yükle

```powershell
pip install -r requirements.txt
```

> **Not**: `openai-whisper` yüklenirken `torch` da indirilir (~2GB). İlk yükleme uzun sürebilir.

---

## 🔑 API Anahtarları Kurulumu

### 1. Gemini API Key

1. **https://aistudio.google.com/app/apikey** adresine gidin
2. Google hesabınızla giriş yapın
3. **"Create API Key"** butonuna tıklayın
4. Oluşturulan API key'i kopyalayın
5. `.env` dosyasında `GEMINI_API_KEY=` alanına yapıştırın

### 2. Pexels API Key

1. **https://www.pexels.com/api/** adresine gidin
2. **"Get Started"** → üye olun (ücretsiz)
3. Dashboard'dan API key'i kopyalayın
4. `.env` dosyasında `PEXELS_API_KEY=` alanına yapıştırın

---

## 🔐 Google OAuth2 Kurulumu

TTS ve YouTube yükleme için kullanılan **aynı** `client_secret.json` dosyası.

### Mevcut Durumunuz

Projenizde zaten `client_secret.json` dosyası mevcut. Bu adımları sadece yeni bir OAuth2 client oluşturmanız gerekirse uygulayın.

### Yeni OAuth2 Client Oluşturma (Gerekirse)

1. **https://console.cloud.google.com** adresine gidin

2. Üst kısımdan projenizi seçin (veya yeni oluşturun)

3. Sol menü → **"APIs & Services"** → **"Library"**
   - **Google Cloud Text-to-Speech API** → Etkinleştir
   - **YouTube Data API v3** → Etkinleştir

4. Sol menü → **"APIs & Services"** → **"Credentials"**

5. **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**

6. Application type: **"Desktop app"** seçin → Name: istediğiniz isim → **"Create"**

7. **"DOWNLOAD JSON"** butonuna tıklayın → dosyayı indirin

8. İndirilen dosyayı proje klasörüne kopyalayın ve `client_secret.json` olarak kaydedin

### `.env` Dosyasını Kontrol Edin

```env
GOOGLE_OAUTH_CLIENT_SECRET_PATH=./client_secret.json
GOOGLE_TTS_TOKEN_PATH=./token_tts.json
GOOGLE_YOUTUBE_TOKEN_PATH=./token_youtube.json
```

---

## 📁 Proje Yapısı

```
youtube otomasyon/
├── .env                          # API anahtarları (gizli, git'e eklemeyin)
├── .env.example                  # Örnek .env (şablon)
├── client_secret.json            # Google OAuth2 client (gizli)
├── token_tts.json                # TTS token (otomatik oluşur)
├── token_youtube.json            # YouTube token (otomatik oluşur)
├── requirements.txt              # Python bağımlılıkları
├── run_daily.py                  # 🚀 Ana pipeline script
│
├── scripts/
│   ├── config.py                 # Ortam değişkenleri & yol yapılandırması
│   ├── logger.py                 # Loglama
│   ├── script_generator.py      # Gemini API → script üretimi
│   ├── tts_generator.py         # Google TTS OAuth2 → ses
│   ├── subtitle_generator.py    # Whisper → ASS altyazı
│   ├── music_downloader.py      # Telifsiz müzik indirme
│   ├── video_builder.py         # Pexels + FFmpeg → video render
│   └── youtube_uploader.py      # YouTube Data API v3 → yükleme
│
├── data/
│   ├── daily_content.json        # Günlük üretilen içerik
│   ├── used_topics.json          # Kullanılmış konu geçmişi
│   └── upload_log.csv            # YouTube yükleme logu
│
├── output/
│   └── YYYY-MM-DD_video.mp4     # Final videolar
│
├── assets/
│   └── music/                   # Arka plan müzikleri (.mp3)
│
├── temp/                        # Geçici dosyalar (otomatik temizlenir)
├── logs/                        # Günlük log dosyaları
│
└── tests/
    ├── test_script_generator.py  # Gemini testi
    └── test_tts.py              # TTS OAuth2 testi
```

---

## 🚀 Kullanım

```powershell
# Proje klasörüne git ve sanal ortamı aktif et
cd "c:\Users\pc\Desktop\youtube otomasyon"
.\venv\Scripts\Activate.ps1

# Tam pipeline (video üret + YouTube'a yükle)
python run_daily.py

# Dry-run: Sadece local video üret, yükleme yapma
python run_daily.py --dry-run

# Video üret ama yükleme yapma
python run_daily.py --skip-upload

# Belirli bir konuyla çalıştır
python run_daily.py --topic "saving habits"

# Yardım
python run_daily.py --help
```

---

## 🔑 İlk Çalıştırma & OAuth Yetkilendirme

İlk çalıştırmada **iki ayrı OAuth yetkilendirme** yapılır:

### 1. TTS Yetkilendirme (ilk `run_daily.py` veya `tests/test_tts.py`)

1. Terminalde şu mesajı görürsünüz:
   ```
   🌐 Tarayıcı üzerinden TTS yetkilendirmesi açılıyor...
   ```
2. Tarayıcınız otomatik açılır
3. Google hesabınızla giriş yapın
4. İzin ekranında **"İzin Ver"** tıklayın
5. `token_tts.json` otomatik oluşturulur
6. Bir sonraki çalıştırmada tarayıcı açılmaz (token otomatik yenilenir)

### 2. YouTube Yetkilendirme (ilk gerçek upload)

Aynı süreç, farklı izin ekranı → `token_youtube.json` oluşturulur.

> **⚠️ Token Sona Erme**: Google OAuth refresh token'ları genellikle uzun süre geçerlidir.
> Ancak uzun süre kullanılmazsa veya güvenlik ayarları değişirse token geçersiz olabilir.
> Bu durumda script açık bir hata mesajı verir ve token dosyasını silmenizi ister.

---

## ⏰ Windows Task Scheduler ile Otomatik Çalıştırma

Her gün sabah 09:00'da otomatik çalışması için:

### Adım 1 — Batch Script Oluştur

Proje klasöründe `run_daily.bat` dosyası oluşturun:

```batch
@echo off
cd /d "c:\Users\pc\Desktop\youtube otomasyon"
call venv\Scripts\activate.bat
python run_daily.py >> logs\scheduler.log 2>&1
```

### Adım 2 — Task Scheduler Ayarla

1. **Win + R** → `taskschd.msc` → **Tamam**

2. Sağ panelde **"Temel Görev Oluştur..."** tıklayın

3. **Ad**: `YouTube Shorts Daily` → **İleri**

4. **Tetikleyici**: `Günlük` → **İleri**

5. **Başlangıç saati**: `09:00:00` → **İleri**

6. **Eylem**: `Program başlat` → **İleri**

7. **Program/Betik**: Browse ile `run_daily.bat` dosyasını seçin

8. **Başlangıç konumu**: 
   ```
   c:\Users\pc\Desktop\youtube otomasyon
   ```

9. **Son** → **Tamam**

### Adım 3 — Test Et

Oluşturulan görevi sağ tıklayın → **"Çalıştır"** → log dosyasını kontrol edin.

---

## 🧪 Test Rehberi

### Test 1 — Gemini Script Üretimi (FFmpeg gerekmez)

```powershell
python tests/test_script_generator.py
```

Beklenen çıktı:
```
✅ Konfigürasyon geçerli.
✅ JSON temizleme testi geçti.
✅ Konu seçimi testi geçti.
✅ Zorunlu alanlar mevcut.
✅ TÜM TESTLER BAŞARILI
```

### Test 2 — TTS OAuth2 (FFmpeg gerekmez)

```powershell
python tests/test_tts.py
```

İlk kez çalıştırırken tarayıcı açılacak. İzin verdikten sonra:
```
✅ OAuth2 başarılı — token: ./token_tts.json
✅ Ses dosyası oluşturuldu: temp/test_audio.mp3
✅ TÜM TTS TESTLERİ BAŞARILI
```

### Test 3 — Dry-Run (FFmpeg kurulduktan sonra)

```powershell
python run_daily.py --dry-run
```

Bu test tüm adımları çalıştırır ama YouTube'a yüklemez.
Final video `output/YYYY-MM-DD_video.mp4` konumunda oluşur.

### Test 4 — Tam Pipeline

```powershell
python run_daily.py
```

---

## 🔧 Sorun Giderme

### `ffmpeg: command not found`
→ FFmpeg kurulumunu yapın ve PATH'e ekleyin (yukarıdaki adımlara bakın).
→ Yeni bir terminal penceresi açın (PATH değişikliği mevcut pencerede geçerli olmaz).

### `GEMINI_API_KEY is missing`
→ `.env` dosyasında API key'in doğru tanımlandığını kontrol edin.
→ Tırnak işareti kullanmayın: `GEMINI_API_KEY=AIzaSy...` (doğru)

### `OAuth client secret not found`
→ `client_secret.json` dosyasının proje kökünde olduğunu kontrol edin.
→ Dosya adının tam olarak `client_secret.json` olduğunu kontrol edin.

### `TTS token refresh failed`
→ `token_tts.json` dosyasını silin ve tekrar çalıştırın.
→ Tarayıcı üzerinden yeniden yetkilendirme yapılacak.

### `YouTube API quota exceeded`
→ YouTube Data API günlük 10.000 unit kotası var (1 upload ≈ 1600 unit).
→ Ertesi gün tekrar deneyin veya Google Cloud Console'dan kotanızı kontrol edin.

### Pexels video bulunamıyor
→ `PEXELS_API_KEY` doğru tanımlandığını kontrol edin.
→ Arama terimini `data/daily_content.json` içinde `pexels_keyword` alanından görüntüleyin.

### Whisper yavaş çalışıyor
→ `base` model CPU'da yavaş olabilir. Bu normaldir (2-3 dakika sürebilir).
→ GPU'nuz varsa: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`

---

## 📊 Log Dosyaları

| Dosya | İçerik |
|-------|---------|
| `logs/YYYY-MM-DD.log` | Günlük detaylı çalışma logu |
| `data/upload_log.csv` | YouTube yükleme geçmişi (video ID, URL, tarih) |
| `data/used_topics.json` | Kullanılmış konu geçmişi (tekrar önleme) |

---

## 🛡 Güvenlik Notları

- `.env`, `client_secret.json`, `token_tts.json`, `token_youtube.json` dosyalarını **asla** GitHub'a yüklemeyin
- Bu dosyaları `.gitignore`'a ekleyin:
  ```
  .env
  client_secret.json
  token_*.json
  ```

---

## ⚖️ Yasal Notlar

- Tüm üretilen içerik **genel bilgilendirme amaçlıdır**, finansal tavsiye değildir
- Pexels videoları [Pexels Lisansı](https://www.pexels.com/license/) kapsamındadır
- Arka plan müzikleri CC0 / kamu malı lisanslıdır
