"""
tts_generator.py — Google Cloud Text-to-Speech ile ses üretimi.

OAuth2 kimlik doğrulama akışı:
  1. token_tts.json varsa → yükle
  2. Token süresi dolmuşsa → refresh token ile yenile
  3. Token yoksa veya refresh başarısızsa → tarayıcı üzerinden yetkilendirme
  4. Elde edilen token → token_tts.json'a kaydet (sonraki çalıştırmalarda kullanılır)

TTS ayarları:
  - Ses: en-US-Neural2-D (erkek, doğal)
  - Hız: 1.1 (Shorts formatı için optimize)
  - Format: MP3
"""

import sys
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.cloud import texttospeech

from scripts.config import (
    GOOGLE_OAUTH_CLIENT_SECRET_PATH,
    GOOGLE_TTS_TOKEN_PATH,
    TTS_VOICE_NAME,
    TTS_SPEAKING_RATE,
    TEMP_DIR,
)
from scripts.logger import logger

# TTS için gerekli OAuth2 scope
TTS_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def get_tts_credentials() -> Credentials:
    """
    OAuth2 kimlik doğrulama ile geçerli TTS credentials döndürür.

    Token geçerliyse doğrudan kullanır.
    Token süresi dolmuşsa refresh eder.
    Token yoksa veya refresh başarısızsa tarayıcı üzerinden yetkilendirme açar.

    Raises:
        SystemExit(1): Geri kurtarılamaz auth hatası durumunda.
    """
    token_path = Path(GOOGLE_TTS_TOKEN_PATH)
    client_secret_path = Path(GOOGLE_OAUTH_CLIENT_SECRET_PATH)
    creds: Credentials | None = None

    # 1) Mevcut token dosyasını yükle
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), TTS_SCOPES)
            logger.debug(f"TTS token yüklendi: {token_path}")
        except Exception as e:
            logger.warning(f"TTS token dosyası okunamadı, yeniden yetkilendirme gerekiyor: {e}")
            creds = None

    # 2) Süresi dolmuşsa refresh et
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            logger.info("TTS token başarıyla yenilendi (refresh).")
            # Güncellenmiş token'ı kaydet
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        except RefreshError as e:
            logger.error(
                f"❌ TTS token yenileme başarısız!\n"
                f"   Neden: {e}\n"
                f"   Çözüm: '{token_path}' dosyasını silin ve tekrar çalıştırın.\n"
                f"          Tarayıcı üzerinden yeniden yetkilendirme yapılacak."
            )
            sys.exit(1)

    # 3) Token geçersizse yeni yetkilendirme
    if not creds or not creds.valid:
        if not client_secret_path.exists():
            logger.error(
                f"❌ OAuth client secret bulunamadı: {client_secret_path}\n"
                "   Google Cloud Console'dan Desktop app OAuth2 client indirin."
            )
            sys.exit(1)

        logger.info("🌐 Tarayıcı üzerinden TTS yetkilendirmesi açılıyor...")
        logger.info("   (Lütfen Google hesabınıza giriş yapın ve izin verin)")
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secret_path), TTS_SCOPES
            )
            creds = flow.run_local_server(port=0)
        except Exception as e:
            logger.error(f"❌ OAuth2 akışı başarısız: {e}")
            sys.exit(1)

        # Token'ı kaydet
        with open(token_path, "w") as f:
            f.write(creds.to_json())
        logger.info(f"✅ TTS token kaydedildi: {token_path}")

    return creds


def generate_audio(script_text: str, output_filename: str = "audio.mp3") -> Path:
    """
    Verilen metni Google TTS ile sese çevirir ve MP3 dosyası olarak kaydeder.

    Args:
        script_text: Seslendirilecek metin.
        output_filename: Çıktı dosya adı (temp/ klasörüne kaydedilir).

    Returns:
        Oluşturulan MP3 dosyasının Path nesnesi.

    Raises:
        SystemExit(1): TTS API hatası durumunda.
    """
    logger.info(f"TTS ses üretiliyor... (ses: {TTS_VOICE_NAME}, hız: {TTS_SPEAKING_RATE})")

    try:
        creds = get_tts_credentials()
        client = texttospeech.TextToSpeechClient(credentials=creds)

        synthesis_input = texttospeech.SynthesisInput(text=script_text)

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=TTS_VOICE_NAME,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=TTS_SPEAKING_RATE,
        )

        logger.debug("Google TTS API çağrısı yapılıyor...")
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        output_path = TEMP_DIR / output_filename
        with open(output_path, "wb") as f:
            f.write(response.audio_content)

        # Dosya boyutu kontrolü
        size_kb = output_path.stat().st_size / 1024
        logger.info(f"✅ TTS tamamlandı → {output_path} ({size_kb:.1f} KB)")
        return output_path

    except Exception as e:
        logger.error(f"❌ TTS API hatası: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Hızlı test: kısa bir metni sese çevir
    _test_script = (
        "Most people never build wealth because they skip this one step. "
        "Before you spend a single dollar, pay yourself first. "
        "Set up an automatic transfer to savings the moment your paycheck hits. "
        "Even ten percent makes a massive difference over time. "
        "Start today, not next month. Your future self is counting on you. "
        "This is for informational purposes only, not financial advice."
    )
    out = generate_audio(_test_script, output_filename="test_audio.mp3")
    print(f"\n✅ Test ses dosyası oluşturuldu: {out}")
    print("   Dosyayı bir medya oynatıcıda dinleyin.")
