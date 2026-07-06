"""
video_builder.py — Pexels stok videoları + FFmpeg ile final video render.

Pipeline:
  1. Pexels API'den konuya uygun dikey (portrait) videolar ara ve indir
  2. Her klibi 1080x1920, 30fps olarak normalize et
  3. Klipler yeterli süre değilse tekrar kullan (döngüsel)
  4. Klipleri birleştir ve ses süresine kes
  5. Karartma filtresi uygula (brightness -0.15)
  6. ASS altyazı overlay ekle
  7. TTS sesi + arka plan müziği (-20dB) mikslere
  8. H.264/AAC ile final MP4 çıktısı

Gereksinim: FFmpeg PATH'te kurulu olmalı.
"""

import random
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import requests

from scripts.config import PEXELS_API_KEY, TEMP_DIR, OUTPUT_DIR
from scripts.logger import logger

# ── Sabitler ─────────────────────────────────────────────────────────────────
VIDEO_WIDTH   = 1080
VIDEO_HEIGHT  = 1920
VIDEO_FPS     = 30
VIDEO_CODEC   = "libx264"
AUDIO_CODEC   = "aac"
AUDIO_BITRATE = "192k"
CRF           = 23          # H.264 kalite (düşük = daha iyi, yavaş)
PRESET        = "fast"      # FFmpeg encode hızı
CROSSFADE_DUR = 0.5         # Klip geçiş süresi (saniye)
DIM_BRIGHTNESS = -0.15      # Karartma miktarı (-1.0 – 1.0)
BGM_VOLUME     = 0.08       # Arka plan müziği ses seviyesi (TTS = 1.0)

PEXELS_API_BASE = "https://api.pexels.com/videos/search"


# ── FFmpeg Kontrolü ──────────────────────────────────────────────────────────
def check_ffmpeg() -> None:
    """
    FFmpeg'in PATH'te kurulu olup olmadığını kontrol eder.
    Kurulu değilse açık hata mesajı ile çıkar.
    """
    if shutil.which("ffmpeg") is None:
        logger.error(
            "\n❌ FFmpeg bulunamadı!\n"
            "   Video render için FFmpeg kurulumu gerekli.\n"
            "   README.md → 'FFmpeg Kurulumu (Windows)' bölümüne bakın.\n"
            "   Kurulumdan sonra yeni bir terminal açıp tekrar deneyin."
        )
        sys.exit(1)
    logger.debug("FFmpeg kontrol: ✅")


def check_ffprobe() -> None:
    """ffprobe (FFmpeg ile birlikte gelir) varlığını kontrol eder."""
    if shutil.which("ffprobe") is None:
        logger.error("❌ ffprobe bulunamadı. FFmpeg kurulumunu kontrol edin.")
        sys.exit(1)


def run_ffmpeg(cmd: List[str], step_name: str = "FFmpeg") -> None:
    """FFmpeg komutu çalıştırır. Hata durumunda log yazar ve çıkar."""
    logger.debug(f"[{step_name}] Komut: {' '.join(cmd[:6])}...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.error(f"❌ {step_name} hatası (return code {result.returncode}):")
            logger.error(result.stderr[-2000:] if result.stderr else "(çıktı yok)")
            sys.exit(1)
    except FileNotFoundError:
        logger.error("❌ FFmpeg çalıştırılamadı. PATH'e eklendiğinden emin olun.")
        sys.exit(1)


def get_audio_duration(audio_path: Path) -> float:
    """ffprobe ile ses dosyasının süresini (saniye) döndürür."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        logger.error(f"❌ Ses süresi alınamadı: {audio_path}")
        sys.exit(1)
    duration = float(result.stdout.strip())
    logger.debug(f"Ses süresi: {duration:.2f} saniye")
    return duration


def get_video_duration(video_path: Path) -> float:
    """ffprobe ile video dosyasının süresini döndürür."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return 0.0
    return float(result.stdout.strip())


# ── Pexels Video İndirme ──────────────────────────────────────────────────────
def search_pexels_videos(keyword: str, count: int = 6) -> List[dict]:
    """
    Pexels API'de portrait video arar.

    Returns:
        [{"id": ..., "duration": ..., "url": ..., "width": ..., "height": ...}, ...]
    """
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": keyword,
        "orientation": "portrait",
        "per_page": count,
        "size": "medium",
    }
    try:
        response = requests.get(PEXELS_API_BASE, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Pexels API hatası: {e}")
        sys.exit(1)

    videos = []
    for video in data.get("videos", []):
        # En iyi kaliteli portrait dosyayı seç
        best_file = _pick_best_video_file(video.get("video_files", []))
        if best_file:
            videos.append({
                "id": video["id"],
                "duration": video.get("duration", 10),
                "url": best_file["link"],
                "width": best_file.get("width", 0),
                "height": best_file.get("height", 0),
            })

    logger.info(f"Pexels'tan {len(videos)} video bulundu (arama: '{keyword}')")
    return videos


def _pick_best_video_file(video_files: list) -> Optional[dict]:
    """
    Mevcut video dosyaları arasından en iyi portrait kaliteyi seçer.
    Tercih sırası: HD portrait > SD portrait > herhangi biri
    """
    portrait_files = [
        f for f in video_files
        if f.get("height", 0) > f.get("width", 0)  # portrait: yükseklik > genişlik
    ]
    if not portrait_files:
        portrait_files = video_files  # portrait yoksa hepsinden seç

    # HD kaliteyi tercih et (en az 720p yükseklik)
    hd = [f for f in portrait_files if f.get("height", 0) >= 720]
    return hd[0] if hd else (portrait_files[0] if portrait_files else None)


def download_video_clip(url: str, output_path: Path) -> bool:
    """Tek bir video klibini indirir."""
    try:
        logger.debug(f"Video indiriliyor: {output_path.name}")
        response = requests.get(url, timeout=120, stream=True)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                f.write(chunk)
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.debug(f"İndirildi: {output_path.name} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        logger.warning(f"Video indirme hatası ({output_path.name}): {e}")
        output_path.unlink(missing_ok=True)
        return False


def download_pexels_clips(keyword: str, needed_duration: float) -> List[Path]:
    """
    Gereken toplam süreyi karşılayacak kadar video klip indirir.

    Args:
        keyword: Pexels arama terimi.
        needed_duration: İhtiyaç duyulan toplam video süresi (saniye).

    Returns:
        İndirilen video klip yollarının listesi.
    """
    videos = search_pexels_videos(keyword, count=6)

    if not videos:
        logger.error(f"❌ '{keyword}' için Pexels'tan video bulunamadı.")
        sys.exit(1)

    # Rastgele sırala (her gün farklı klip kombinasyonu)
    random.shuffle(videos)

    downloaded_clips = []
    total_duration = 0.0

    for i, video in enumerate(videos):
        if total_duration >= needed_duration + 2:  # 2 saniye buffer
            break

        clip_path = TEMP_DIR / f"pexels_{video['id']}_{i}.mp4"
        if download_video_clip(video["url"], clip_path):
            downloaded_clips.append(clip_path)
            total_duration += video["duration"]
            logger.debug(f"Klip {i+1}: {video['duration']}s → toplam: {total_duration:.1f}s")

    # Yeterli süre yoksa mevcut klipleri döngüsel kullan
    while total_duration < needed_duration + 2 and downloaded_clips:
        logger.info("Yeterli video süresi yok, klipleri döngüsel kullanıyorum...")
        extra_clip = random.choice(downloaded_clips)
        # Kopyalanmış klipler için benzersiz isim
        copy_path = TEMP_DIR / f"loop_{len(downloaded_clips)}_{extra_clip.name}"
        import shutil as _shutil
        _shutil.copy2(str(extra_clip), str(copy_path))
        downloaded_clips.append(copy_path)
        dur = get_video_duration(extra_clip)
        total_duration += dur if dur > 0 else 10

    logger.info(f"Toplam {len(downloaded_clips)} klip hazır (~{total_duration:.1f}s)")
    return downloaded_clips


# ── FFmpeg Video İşleme ───────────────────────────────────────────────────────
def normalize_clip(input_path: Path, output_path: Path) -> None:
    """
    Video klibini 1080x1920 dikey formata scale+crop ile normalize eder.
    Ses kanalını kaldırır (TTS sesi ayrıca eklenir).
    """
    # Scale: en-boy oranını koruyarak büyüt, sonra crop ile tam boyuta getir
    vf = (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
        f"setsar=1,"
        f"fps={VIDEO_FPS}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", vf,
        "-c:v", VIDEO_CODEC,
        "-preset", PRESET,
        "-crf", str(CRF),
        "-an",  # Ses kaldır
        str(output_path),
    ]
    run_ffmpeg(cmd, step_name="Normalize")


def concat_clips(clip_paths: List[Path], output_path: Path, max_duration: float) -> None:
    """
    Normalize edilmiş klipleri birleştirir ve max_duration saniyeye kırpar.
    Crossfade geçiş efekti uygular (>1 klip varsa).
    """
    n = len(clip_paths)

    if n == 1:
        # Tek klip → sadece kırp
        cmd = [
            "ffmpeg", "-y",
            "-i", str(clip_paths[0]),
            "-t", str(max_duration + 0.5),  # Küçük buffer
            "-c:v", "copy",
            "-an",
            str(output_path),
        ]
        run_ffmpeg(cmd, step_name="SingleClipTrim")
        return

    # Çoklu klip: concat filtre grafiği oluştur
    inputs = []
    for p in clip_paths:
        inputs.extend(["-i", str(p)])

    # concat filtresi: tüm klipleri sırayla birleştir
    filter_inputs = "".join(f"[{i}:v]" for i in range(n))
    filter_complex = f"{filter_inputs}concat=n={n}:v=1:a=0[vconcat]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vconcat]",
        "-t", str(max_duration + 0.5),
        "-c:v", VIDEO_CODEC,
        "-preset", PRESET,
        "-crf", str(CRF),
        str(output_path),
    ]
    run_ffmpeg(cmd, step_name="Concat")


def build_final_video(
    video_path: Path,
    audio_path: Path,
    subtitle_path: Path,
    music_path: Optional[str],
    output_path: Path,
    audio_duration: float,
) -> None:
    """
    Final video render:
      - Karartma filtresi
      - ASS altyazı overlay
      - TTS + arka plan müziği miksaj
      - Kesin süre kırpma

    Args:
        video_path: Normalize+concat edilmiş geçici video.
        audio_path: TTS ses dosyası.
        subtitle_path: ASS altyazı dosyası.
        music_path: Arka plan müziği (None ise müzik eklenmez).
        output_path: Final çıktı dosyası.
        audio_duration: Tam video süresi (saniye).
    """
    # ASS dosya yolunu FFmpeg için doğru formatta hazırla (Windows path escape)
    sub_str = str(subtitle_path).replace("\\", "/")
    # Windows: sürücü harfinden sonra gelen ':' karakterini escape et
    if len(sub_str) > 1 and sub_str[1] == ":":
        sub_str = sub_str[0] + "\\:" + sub_str[2:]

    # FFmpeg input'ları
    inputs: List[str] = [
        "-i", str(video_path),
        "-i", str(audio_path),
    ]
    if music_path:
        inputs.extend(["-i", str(music_path)])

    # Filter complex oluştur
    # Video: karartma + altyazı
    vf_chain = (
        f"[0:v]eq=brightness={DIM_BRIGHTNESS},"
        f"subtitles='{sub_str}'[vfinal]"
    )

    # Ses miksaj
    if music_path:
        af_chain = (
            f"[1:a]volume=1.0[tts];"
            f"[2:a]volume={BGM_VOLUME}[bgm];"
            f"[tts][bgm]amix=inputs=2:duration=first:dropout_transition=2[afinal]"
        )
        filter_complex = f"{vf_chain};{af_chain}"
        audio_map = "[afinal]"
    else:
        filter_complex = vf_chain
        audio_map = "1:a"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vfinal]",
        "-map", audio_map,
        "-t", str(audio_duration),
        "-c:v", VIDEO_CODEC,
        "-preset", PRESET,
        "-crf", str(CRF),
        "-c:a", AUDIO_CODEC,
        "-b:a", AUDIO_BITRATE,
        "-movflags", "+faststart",  # Web için optimize
        str(output_path),
    ]
    run_ffmpeg(cmd, step_name="FinalRender")


def cleanup_temp_files(paths: List[Path]) -> None:
    """Geçici video dosyalarını temizler."""
    for p in paths:
        try:
            p.unlink(missing_ok=True)
            logger.debug(f"Temp dosya silindi: {p.name}")
        except Exception:
            pass


# ── Ana Build Fonksiyonu ──────────────────────────────────────────────────────
def build_video(
    audio_path: Path,
    subtitle_path: Path,
    music_tracks: List[str],
    pexels_keyword: str,
    output_path: Path,
) -> None:
    """
    Tam video render pipeline'ı.

    Args:
        audio_path: TTS ses dosyası.
        subtitle_path: ASS altyazı dosyası.
        music_tracks: Mevcut müzik dosyaları listesi.
        pexels_keyword: Pexels arama terimi.
        output_path: Final video çıktı yolu.
    """
    # FFmpeg ve ffprobe kontrolü
    check_ffmpeg()
    check_ffprobe()

    # Ses süresini al
    audio_duration = get_audio_duration(audio_path)
    logger.info(f"Video süresi: {audio_duration:.2f} saniye")

    # Pexels'tan klip indir
    logger.info(f"Pexels'tan video klipleri indiriliyor... ('{pexels_keyword}')")
    raw_clips = download_pexels_clips(pexels_keyword, audio_duration)

    # Klipler normalize et
    logger.info(f"{len(raw_clips)} klip normalize ediliyor (1080x1920)...")
    normalized_clips = []
    for i, clip in enumerate(raw_clips):
        norm_path = TEMP_DIR / f"norm_{i}.mp4"
        logger.debug(f"Normalize ediliyor: klip {i+1}/{len(raw_clips)}")
        normalize_clip(clip, norm_path)
        normalized_clips.append(norm_path)

    # Klipler birleştir
    concat_path = TEMP_DIR / "concat.mp4"
    logger.info("Klipler birleştiriliyor...")
    concat_clips(normalized_clips, concat_path, audio_duration)

    # Müzik seç
    music_path = random.choice(music_tracks) if music_tracks else None
    if music_path:
        logger.info(f"Arka plan müziği: {Path(music_path).name}")
    else:
        logger.info("Arka plan müziği yok — sessiz devam ediliyor.")

    # Final render
    logger.info("Final video render ediliyor...")
    build_final_video(
        video_path=concat_path,
        audio_path=audio_path,
        subtitle_path=subtitle_path,
        music_path=music_path,
        output_path=output_path,
        audio_duration=audio_duration,
    )

    # Temp dosyaları temizle
    cleanup_temp_files(raw_clips + normalized_clips + [concat_path])

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"✅ Video render tamamlandı → {output_path} ({size_mb:.1f} MB)")
