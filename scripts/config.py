"""
config.py — Merkezi konfigürasyon modülü.
Tüm ortam değişkenlerini .env dosyasından yükler ve doğrular.
Diğer tüm modüller bu dosyadan import eder.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# .env dosyasını proje kökünden yükle
_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# ── Proje Dizinleri ──────────────────────────────────────────────────────────
PROJECT_ROOT = _PROJECT_ROOT
OUTPUT_DIR   = PROJECT_ROOT / "output"
DATA_DIR     = PROJECT_ROOT / "data"
LOGS_DIR     = PROJECT_ROOT / "logs"
ASSETS_DIR   = PROJECT_ROOT / "assets"
MUSIC_DIR    = ASSETS_DIR / "music"
TEMP_DIR     = PROJECT_ROOT / "temp"

# Gerekli dizinleri oluştur
for _dir in [OUTPUT_DIR, DATA_DIR, LOGS_DIR, ASSETS_DIR, MUSIC_DIR, TEMP_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

# ── API Anahtarları ──────────────────────────────────────────────────────────
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
PEXELS_API_KEY  = os.getenv("PEXELS_API_KEY", "")

# ── OAuth2 Dosya Yolları ─────────────────────────────────────────────────────
GOOGLE_OAUTH_CLIENT_SECRET_PATH = os.getenv(
    "GOOGLE_OAUTH_CLIENT_SECRET_PATH", "./client_secret.json"
)
GOOGLE_TTS_TOKEN_PATH = os.getenv(
    "GOOGLE_TTS_TOKEN_PATH", "./token_tts.json"
)
GOOGLE_YOUTUBE_TOKEN_PATH = os.getenv(
    "GOOGLE_YOUTUBE_TOKEN_PATH", "./token_youtube.json"
)

# ── TTS Ayarları ─────────────────────────────────────────────────────────────
TTS_VOICE_NAME    = os.getenv("TTS_VOICE_NAME", "en-US-Neural2-D")
TTS_SPEAKING_RATE = float(os.getenv("TTS_SPEAKING_RATE", "1.1"))

# ── YouTube Ayarları ─────────────────────────────────────────────────────────
YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "public")
YOUTUBE_CATEGORY_ID    = os.getenv("YOUTUBE_CATEGORY_ID", "22")  # People & Blogs

# ── Whisper Ayarları ─────────────────────────────────────────────────────────
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# ── İçerik Dosyaları ─────────────────────────────────────────────────────────
DAILY_CONTENT_FILE = DATA_DIR / "daily_content.json"
USED_TOPICS_FILE   = DATA_DIR / "used_topics.json"
UPLOAD_LOG_FILE    = DATA_DIR / "upload_log.csv"

# ── Logo (opsiyonel) ─────────────────────────────────────────────────────────
LOGO_PATH = ASSETS_DIR / "logo.png"


def validate_config() -> bool:
    """
    Zorunlu ortam değişkenlerini ve dosyaları doğrular.
    Eksik varsa hata mesajı basar ve sys.exit(1) ile durur.
    """
    errors = []

    if not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY .env dosyasında tanımlı değil.")
    if not PEXELS_API_KEY:
        errors.append("PEXELS_API_KEY .env dosyasında tanımlı değil.")

    client_secret = Path(GOOGLE_OAUTH_CLIENT_SECRET_PATH)
    if not client_secret.exists():
        errors.append(
            f"OAuth client secret bulunamadı: {GOOGLE_OAUTH_CLIENT_SECRET_PATH}\n"
            "  → Google Cloud Console'dan Desktop app OAuth2 client indirip "
            "client_secret.json olarak kaydedin."
        )

    if errors:
        print("\n[CONFIG] ❌ Konfigürasyon hataları:")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        print()
        sys.exit(1)

    return True


if __name__ == "__main__":
    validate_config()
    print("✅ Konfigürasyon geçerli.")
    print(f"   PROJECT_ROOT : {PROJECT_ROOT}")
    print(f"   OUTPUT_DIR   : {OUTPUT_DIR}")
    print(f"   TTS_VOICE    : {TTS_VOICE_NAME}")
    print(f"   WHISPER      : {WHISPER_MODEL}")
    print(f"   YT_PRIVACY   : {YOUTUBE_PRIVACY_STATUS}")
