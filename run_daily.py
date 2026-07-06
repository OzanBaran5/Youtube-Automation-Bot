#!/usr/bin/env python3
"""
run_daily.py — YouTube Shorts Otomasyon Pipeline Ana Script

Kullanım:
  python run_daily.py                        → Tam pipeline (YouTube'a yükle)
  python run_daily.py --dry-run              → Sadece local video üret, yükleme yok
  python run_daily.py --skip-upload          → Video üret ama yükleme yapma
  python run_daily.py --topic "saving habits" → Belirli konu ile çalıştır
  python run_daily.py --use-existing-script  → Mevcut daily_content.json kullan (Gemini atla)

Adımlar:
  [1/6] Gemini API ile script üret
  [2/6] Google TTS ile ses üret
  [3/6] Whisper ile altyazı üret
  [4/6] Arka plan müziği hazırla
  [5/6] Pexels video + FFmpeg render
  [6/6] YouTube'a yükle
"""

import argparse
import sys
import traceback
from datetime import date
from pathlib import Path

# Proje kökünü Python yoluna ekle
sys.path.insert(0, str(Path(__file__).parent))

from scripts.config import validate_config, OUTPUT_DIR, TEMP_DIR
from scripts.logger import logger
from scripts.script_generator import generate_script
from scripts.tts_generator import generate_audio
from scripts.subtitle_generator import create_subtitles
from scripts.video_builder import build_video
from scripts.youtube_uploader import upload_video
from scripts.music_downloader import ensure_music_available


def parse_args():
    parser = argparse.ArgumentParser(
        description="YouTube Shorts Otomasyon Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Sadece local video üret, YouTube'a yükleme",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Tam pipeline çalıştır ama YouTube'a yükleme",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Belirli bir konu ile çalıştır (rastgele seçim yerine)",
    )
    parser.add_argument(
        "--use-existing-script",
        action="store_true",
        help="Mevcut daily_content.json kullan, Gemini API çağrısı yapma (kota aşımında kullanışlı)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    today = date.today().isoformat()
    output_filename = f"{today}_video.mp4"
    output_path = OUTPUT_DIR / output_filename

    # Mod bilgisi
    mode = "DRY-RUN" if args.dry_run else ("SKIP-UPLOAD" if args.skip_upload else "FULL")

    logger.info("=" * 65)
    logger.info(f"🎬 YouTube Shorts Pipeline Başlıyor — Mod: {mode}")
    logger.info(f"   Tarih: {today} | Çıktı: {output_path.name}")
    logger.info("=" * 65)

    try:
        # ── Konfigürasyon Doğrulama ──────────────────────────────────────
        validate_config()
        logger.info("✅ Konfigürasyon geçerli.")

        # ── ADIM 1: Gemini Script Üretimi ────────────────────────────────
        if args.use_existing_script:
            import json
            from scripts.config import DAILY_CONTENT_FILE
            if not DAILY_CONTENT_FILE.exists():
                logger.error("--use-existing-script secildi ama data/daily_content.json yok!")
                sys.exit(1)
            with open(DAILY_CONTENT_FILE, "r", encoding="utf-8") as _f:
                content = json.load(_f)
            logger.info(f"[1/6] Mevcut script kullaniliyor: '{content['title']}'")
        else:
            logger.info("\n[1/6] Script uretiliyor (Gemini API)...")
            content = generate_script(topic=args.topic)
            logger.info(f"[1/6] Script hazir | '{content['title']}'")


        # ── ADIM 2: TTS Ses Üretimi ──────────────────────────────────────
        logger.info("\n[2/6] 🔊 TTS ses üretiliyor (Google Neural2)...")
        audio_path = generate_audio(content["script"], output_filename="audio.mp3")
        logger.info(f"[2/6] ✅ Ses hazır → {audio_path.name}")

        # ── ADIM 3: Altyazı Üretimi ──────────────────────────────────────
        logger.info("\n[3/6] 📜 Whisper ile altyazı üretiliyor...")
        subtitle_path = create_subtitles(audio_path)
        logger.info(f"[3/6] ✅ Altyazı hazır → {subtitle_path.name}")

        # ── ADIM 4: Müzik Hazırlama ──────────────────────────────────────
        logger.info("\n[4/6] 🎵 Arka plan müziği hazırlanıyor...")
        music_tracks = ensure_music_available()
        logger.info(f"[4/6] ✅ {len(music_tracks)} müzik parçası hazır.")

        # ── ADIM 5: Video Render ─────────────────────────────────────────
        logger.info("\n[5/6] 🎥 Video render ediliyor (Pexels + FFmpeg)...")
        build_video(
            audio_path=audio_path,
            subtitle_path=subtitle_path,
            music_tracks=music_tracks,
            pexels_keyword=content.get("pexels_keyword", "finance money"),
            output_path=output_path,
        )
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"[5/6] ✅ Video hazır → {output_path} ({size_mb:.1f} MB)")

        # ── ADIM 6: YouTube Yükleme ──────────────────────────────────────
        if args.dry_run or args.skip_upload:
            logger.info(
                f"\n[6/6] ⏭  YouTube yükleme atlandı ({mode} modu)."
            )
        else:
            logger.info("\n[6/6] 📤 YouTube'a yükleniyor...")
            video_id = upload_video(output_path, content)
            if video_id:
                logger.info(f"[6/6] ✅ Yüklendi: https://www.youtube.com/watch?v={video_id}")
            else:
                logger.error("[6/6] ❌ Yükleme başarısız. Logları kontrol edin.")

        # ── Tamamlandı ───────────────────────────────────────────────────
        logger.info("\n" + "=" * 65)
        logger.info(f"✅ Pipeline tamamlandı! Video: {output_path}")
        logger.info("=" * 65)

    except SystemExit:
        # Script içindeki sys.exit() çağrıları — zaten loglandı
        raise

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Kullanıcı tarafından iptal edildi.")
        sys.exit(0)

    except Exception as e:
        logger.error(f"\n❌ Beklenmeyen hata: {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
