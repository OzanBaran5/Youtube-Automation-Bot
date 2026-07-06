"""
youtube_uploader.py — YouTube Data API v3 ile video yükleme.

OAuth2 kimlik doğrulama akışı (TTS ile aynı mantık, farklı scope):
  - Scope: https://www.googleapis.com/auth/youtube.upload
  - Token: token_youtube.json
  - İlk çalıştırmada tarayıcı üzerinden yetkilendirme
  - Sonraki çalıştırmalarda refresh token ile otomatik yenileme

Yükleme sonrası:
  - Video ID ve URL'i data/upload_log.csv'ye kaydedilir
  - Hata durumunda log yazılır, script çökmez
"""

import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from scripts.config import (
    GOOGLE_OAUTH_CLIENT_SECRET_PATH,
    GOOGLE_YOUTUBE_TOKEN_PATH,
    YOUTUBE_PRIVACY_STATUS,
    YOUTUBE_CATEGORY_ID,
    UPLOAD_LOG_FILE,
)
from scripts.logger import logger

# YouTube upload için gerekli OAuth2 scope
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


# ── OAuth2 Kimlik Doğrulama ──────────────────────────────────────────────────
def get_youtube_credentials() -> Credentials:
    """
    YouTube upload için OAuth2 credentials döndürür.
    TTS'ten farklı token dosyası ve scope kullanır.

    Raises:
        SystemExit(1): Geri kurtarılamaz auth hatası.
    """
    token_path = Path(GOOGLE_YOUTUBE_TOKEN_PATH)
    client_secret_path = Path(GOOGLE_OAUTH_CLIENT_SECRET_PATH)
    creds: Credentials | None = None

    # 1) Mevcut token yükle
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), YOUTUBE_SCOPES)
            logger.debug(f"YouTube token yüklendi: {token_path}")
        except Exception as e:
            logger.warning(f"YouTube token dosyası okunamadı, yeniden yetkilendirme: {e}")
            creds = None

    # 2) Süresi dolmuşsa refresh et
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            logger.info("YouTube token başarıyla yenilendi (refresh).")
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        except RefreshError as e:
            logger.error(
                f"❌ YouTube token yenileme başarısız!\n"
                f"   Neden: {e}\n"
                f"   Çözüm: '{token_path}' dosyasını silin ve tekrar çalıştırın."
            )
            sys.exit(1)

    # 3) Geçersizse yeni yetkilendirme
    if not creds or not creds.valid:
        if not client_secret_path.exists():
            logger.error(f"❌ OAuth client secret bulunamadı: {client_secret_path}")
            sys.exit(1)

        logger.info("🌐 Tarayıcı üzerinden YouTube yetkilendirmesi açılıyor...")
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secret_path), YOUTUBE_SCOPES
            )
            creds = flow.run_local_server(port=0)
        except Exception as e:
            logger.error(f"❌ YouTube OAuth2 akışı başarısız: {e}")
            sys.exit(1)

        with open(token_path, "w") as f:
            f.write(creds.to_json())
        logger.info(f"✅ YouTube token kaydedildi: {token_path}")

    return creds


# ── Upload Log ────────────────────────────────────────────────────────────────
def log_upload(
    video_id: str,
    title: str,
    topic: str,
    video_path: Path,
    status: str,
    error_msg: str = "",
) -> None:
    """Upload sonucunu data/upload_log.csv'ye ekler."""
    is_new = not UPLOAD_LOG_FILE.exists()
    with open(UPLOAD_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow([
                "timestamp", "date", "video_id", "url",
                "title", "topic", "file", "privacy", "status", "error"
            ])
        writer.writerow([
            datetime.now().isoformat(),
            datetime.now().strftime("%Y-%m-%d"),
            video_id,
            f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
            title,
            topic,
            video_path.name,
            YOUTUBE_PRIVACY_STATUS,
            status,
            error_msg,
        ])
    logger.debug(f"Upload logu güncellendi: {UPLOAD_LOG_FILE}")


# ── Video Yükleme ─────────────────────────────────────────────────────────────
def upload_video(video_path: Path, content: dict) -> Optional[str]:
    """
    YouTube'a video yükler.

    Args:
        video_path: Yüklenecek MP4 dosyasının yolu.
        content: daily_content.json'dan gelen içerik dict'i.
                 Anahtarlar: title, description, tags, topic, pexels_keyword

    Returns:
        Başarılı ise video_id str, hata ise None.
    """
    title   = content.get("title", "YouTube Short")
    # Başlıkta #Shorts olmadığı durum için güvence
    if "#Shorts" not in title and "#shorts" not in title:
        title = title + " #Shorts"
    # 100 karakter limiti
    if len(title) > 100:
        title = title[:97] + "..."

    description = content.get("description", "")
    if "#Shorts" not in description and "#shorts" not in description:
        description += "\n\n#Shorts"

    tags = content.get("tags", [])
    # Temel tagları ekle
    base_tags = ["Shorts", "Finance", "PersonalFinance", "SelfImprovement", "MoneyTips"]
    tags = list(set(tags + base_tags))

    topic = content.get("topic", "")

    logger.info(f"YouTube'a yükleniyor: '{title}'")
    logger.info(f"  Gizlilik: {YOUTUBE_PRIVACY_STATUS} | Kategori: {YOUTUBE_CATEGORY_ID}")

    try:
        creds = get_youtube_credentials()
        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": YOUTUBE_CATEGORY_ID,
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en",
            },
            "status": {
                "privacyStatus": YOUTUBE_PRIVACY_STATUS,
                "selfDeclaredMadeForKids": False,
            },
        }

        # Resumable upload (büyük dosyalar için güvenli)
        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 5,  # 5MB chunks
        )

        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        # Upload ilerlemesini takip et
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                percent = int(status.progress() * 100)
                logger.info(f"  Yükleniyor... %{percent}")

        video_id = response.get("id", "")
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info(f"✅ Video yüklendi: {video_url}")

        log_upload(video_id, title, topic, video_path, "success")
        return video_id

    except HttpError as e:
        error_msg = f"YouTube API HTTP hatası: {e.status_code} — {e.reason}"
        logger.error(f"❌ {error_msg}")

        # Kota aşımı özel mesajı
        if e.status_code == 403:
            logger.error(
                "   Olası neden: Günlük upload kotası aşıldı.\n"
                "   Yarın tekrar deneyin veya Google Cloud Console'dan kotanızı kontrol edin."
            )
        elif e.status_code == 401:
            logger.error(
                "   Yetkilendirme hatası. token_youtube.json'ı silin ve tekrar deneyin."
            )

        log_upload("", title, topic, video_path, "error", error_msg)
        return None

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(f"❌ Beklenmeyen upload hatası: {error_msg}")
        log_upload("", title, topic, video_path, "error", error_msg)
        return None


if __name__ == "__main__":
    print("YouTube uploader doğrudan çalıştırılamaz.")
    print("run_daily.py üzerinden kullanın.")
