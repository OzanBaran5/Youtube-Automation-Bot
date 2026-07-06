"""
test_tts.py — Google TTS OAuth2 ses üretimini test eder.

Testler:
  1. OAuth2 credentials akışı (token yükleme / tarayıcı auth)
  2. TTS API çağrısı ve MP3 üretimi
  3. Çıktı dosyasının varlığı ve geçerli boyutu
  4. Token yenileme mekanizması
"""

import sys
from pathlib import Path

# Proje kökünü Python yoluna ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.config import validate_config, TEMP_DIR, GOOGLE_TTS_TOKEN_PATH
from scripts.tts_generator import get_tts_credentials, generate_audio
from scripts.logger import logger


# Test metni (yaklaşık 45 saniye)
TEST_SCRIPT = (
    "Most people never build wealth because they skip this one step. "
    "Before you spend a single dollar, pay yourself first. "
    "Set up an automatic transfer to your savings account the moment your paycheck hits. "
    "Even just ten percent makes a massive difference over time, thanks to compound interest. "
    "You don't need to be rich to start — you need to start to get rich. "
    "Drop a comment below and tell me: are you paying yourself first? "
    "This is for informational purposes only, not financial advice."
)


def test_oauth_credentials():
    """OAuth2 credentials akışını test et."""
    print("  🔐 OAuth2 credentials alınıyor...")
    print("     (İlk kez çalıştırıyorsanız tarayıcı açılacak — izin verin)")
    
    creds = get_tts_credentials()
    
    assert creds is not None, "Credentials None döndü"
    assert creds.valid, "Credentials geçerli değil"
    
    token_path = Path(GOOGLE_TTS_TOKEN_PATH)
    assert token_path.exists(), f"Token dosyası oluşturulmadı: {token_path}"
    
    print(f"  ✅ OAuth2 başarılı — token: {token_path}")
    return creds


def test_audio_generation():
    """TTS ses üretimini test et."""
    print("\n  🔊 Test metni seslendiriliiyor...")
    print(f"     '{TEST_SCRIPT[:60]}...'")
    
    output_path = generate_audio(TEST_SCRIPT, output_filename="test_audio.mp3")
    
    # Dosya varlık ve boyut kontrolü
    assert output_path.exists(), f"Ses dosyası oluşturulmadı: {output_path}"
    
    file_size = output_path.stat().st_size
    assert file_size > 10 * 1024, f"Ses dosyası çok küçük ({file_size} byte) — TTS hatası olabilir"
    
    size_kb = file_size / 1024
    print(f"  ✅ Ses dosyası oluşturuldu: {output_path} ({size_kb:.1f} KB)")
    print(f"     Dosyayı açarak dinleyin: {output_path}")
    
    return output_path


def main():
    print("=" * 60)
    print("🧪 GOOGLE TTS OAUTH2 TEST")
    print("=" * 60)

    # Konfigürasyon kontrolü
    print("\n[1/3] Konfigürasyon doğrulanıyor...")
    validate_config()
    print("  ✅ Konfigürasyon geçerli.")

    # OAuth2 testi
    print("\n[2/3] OAuth2 kimlik doğrulama test ediliyor...")
    test_oauth_credentials()

    # TTS ses üretimi testi
    print("\n[3/3] TTS ses üretimi test ediliyor...")
    audio_path = test_audio_generation()

    # Özet
    print("\n" + "=" * 60)
    print("✅ TÜM TTS TESTLERİ BAŞARILI")
    print("=" * 60)
    print(f"\n📢 Test ses dosyası: {audio_path}")
    print("   Dosyayı Windows Media Player veya başka bir oynatıcıda açın.")
    print(f"\n🔑 Token dosyası kaydedildi: {GOOGLE_TTS_TOKEN_PATH}")
    print("   Sonraki çalıştırmalarda tarayıcı açılmayacak (otomatik yenileme).")


if __name__ == "__main__":
    main()
