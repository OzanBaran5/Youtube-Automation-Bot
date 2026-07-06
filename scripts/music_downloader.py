"""
music_downloader.py — Telifsiz arka plan müziği indirici.

Strateji:
  1. assets/music/ klasöründe zaten MP3 varsa → onları kullan (indirme yok)
  2. Yoksa → Soundhelix ve Internet Archive'dan CC0/kamu malı müzik indir
  3. En az 1 parça indirilemezse → sessizce uyarı ver, müziksiz devam et

NOT: Kullanıcılar isterlerse kendi MP3 dosyalarını assets/music/ klasörüne
     ekleyebilirler, bu durumda script otomatik indir yapmaz.
"""

import random
from pathlib import Path

import requests

from scripts.config import MUSIC_DIR
from scripts.logger import logger

# ── Güvenilir CC0 / Kamu Malı Müzik Kaynakları ───────────────────────────────
# Soundhelix: test/arka plan müziği için özel üretilmiş, ücretsiz kullanım
# Archive.org: Kamu malı enstrümantal müzik
ROYALTY_FREE_TRACKS = [
    {
        "name": "soundhelix_01.mp3",
        "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        "source": "soundhelix.com",
    },
    {
        "name": "soundhelix_02.mp3",
        "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
        "source": "soundhelix.com",
    },
    {
        "name": "soundhelix_03.mp3",
        "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3",
        "source": "soundhelix.com",
    },
    {
        "name": "soundhelix_04.mp3",
        "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3",
        "source": "soundhelix.com",
    },
    {
        "name": "soundhelix_05.mp3",
        "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-12.mp3",
        "source": "soundhelix.com",
    },
]

# Minimum kabul edilebilir dosya boyutu (sahte/hatalı indirmeleri filtreler)
MIN_FILE_SIZE_BYTES = 50 * 1024  # 50 KB


def _download_track(url: str, save_path: Path, timeout: int = 60) -> bool:
    """
    Tek bir müzik parçasını indirir.

    Returns:
        True: İndirme başarılı
        False: Hata oluştu (log yazılır, exception fırlatılmaz)
    """
    try:
        logger.debug(f"İndiriliyor: {save_path.name} ← {url}")
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # Dosya boyutu kontrolü
        file_size = save_path.stat().st_size
        if file_size < MIN_FILE_SIZE_BYTES:
            logger.warning(f"İndirilen dosya çok küçük ({file_size} byte), siliniyor: {save_path.name}")
            save_path.unlink(missing_ok=True)
            return False

        logger.info(f"✅ Müzik indirildi: {save_path.name} ({file_size // 1024} KB)")
        return True

    except requests.exceptions.Timeout:
        logger.warning(f"Zaman aşımı: {url}")
        save_path.unlink(missing_ok=True)
        return False
    except requests.exceptions.RequestException as e:
        logger.warning(f"İndirme hatası ({save_path.name}): {e}")
        save_path.unlink(missing_ok=True)
        return False
    except Exception as e:
        logger.warning(f"Beklenmeyen hata ({save_path.name}): {e}")
        save_path.unlink(missing_ok=True)
        return False


def ensure_music_available() -> list[str]:
    """
    assets/music/ klasöründe en az bir MP3 olmasını sağlar.

    Zaten dosya varsa → mevcut dosyaları döndür.
    Yoksa → telifsiz kaynaklardan indir.
    Hiçbir şey indirilemezse → boş liste döndür (müziksiz devam).

    Returns:
        Kullanılabilir MP3 dosya yollarının listesi.
    """
    # Mevcut MP3'leri kontrol et
    existing = list(MUSIC_DIR.glob("*.mp3"))
    if existing:
        logger.info(f"Mevcut müzik parçaları kullanılıyor: {len(existing)} dosya")
        return [str(p) for p in existing]

    logger.info("Müzik klasörü boş — telifsiz parçalar indiriliyor...")
    downloaded = []

    for track in ROYALTY_FREE_TRACKS:
        save_path = MUSIC_DIR / track["name"]
        if save_path.exists() and save_path.stat().st_size > MIN_FILE_SIZE_BYTES:
            downloaded.append(str(save_path))
            continue
        if _download_track(track["url"], save_path):
            downloaded.append(str(save_path))

    if not downloaded:
        logger.warning(
            "⚠️  Hiç müzik parçası indirilemedi. Video müziksiz üretilecek.\n"
            "    İpucu: Kendi MP3 dosyalarınızı assets/music/ klasörüne ekleyebilirsiniz."
        )
    else:
        logger.info(f"Toplam {len(downloaded)} müzik parçası hazır.")

    return downloaded


def get_random_track(tracks: list[str]) -> str | None:
    """Müzik listesinden rastgele bir parça seçer."""
    if not tracks:
        return None
    return random.choice(tracks)


if __name__ == "__main__":
    tracks = ensure_music_available()
    if tracks:
        print(f"\n✅ {len(tracks)} müzik parçası hazır:")
        for t in tracks:
            print(f"   {Path(t).name}")
    else:
        print("\n⚠️  Müzik parçası bulunamadı.")
