"""
subtitle_generator.py — Whisper ile ses transkripti ve ASS altyazı dosyası üretimi.

Pipeline:
  1. openai-whisper (local, base model) ile ses dosyasını transkript et
  2. Kelime bazlı zaman damgaları (word_timestamps=True) çıkar
  3. Kelimeleri 4'lü gruplara böl (3–5 kelime / ekran)
  4. ASS formatında altyazı dosyası oluştur
     - Büyük beyaz yazı (80pt Arial)
     - Siyah outline (4px)
     - Ekran alt-ortası (Alignment: 2)

NOT: Whisper ve bu modül FFmpeg gerektirmektedir.
     FFmpeg kurulu değilse açık hata mesajı verilir.
"""

import sys
from pathlib import Path
from typing import List, Dict

from scripts.config import TEMP_DIR, WHISPER_MODEL
from scripts.logger import logger


def _check_ffmpeg_for_whisper() -> None:
    """Whisper'ın çalışması için FFmpeg varlığını kontrol eder."""
    import shutil
    if shutil.which("ffmpeg") is None:
        logger.error(
            "❌ FFmpeg bulunamadı! Whisper çalışmak için FFmpeg'e ihtiyaç duyar.\n"
            "   README.md dosyasındaki 'FFmpeg Kurulumu (Windows)' bölümüne bakın."
        )
        sys.exit(1)


def get_word_timestamps(audio_path: Path) -> List[Dict]:
    """
    Whisper ile ses dosyasını transkript eder ve kelime bazlı timestamp listesi döndürür.

    Returns:
        [{"word": "Hello", "start": 0.0, "end": 0.4}, ...]
    """
    _check_ffmpeg_for_whisper()

    try:
        import whisper
    except ImportError:
        logger.error("❌ openai-whisper kurulu değil. Çalıştırın: pip install openai-whisper")
        sys.exit(1)

    logger.info(f"Whisper modeli yükleniyor: '{WHISPER_MODEL}' (ilk kez indirilecek)")
    model = whisper.load_model(WHISPER_MODEL)

    logger.info(f"Ses transkript ediliyor: {audio_path.name}")
    result = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        language="en",
        verbose=False,
    )

    words = []
    for segment in result.get("segments", []):
        for word_info in segment.get("words", []):
            word = word_info.get("word", "").strip()
            if word:
                words.append({
                    "word": word,
                    "start": round(word_info["start"], 3),
                    "end": round(word_info["end"], 3),
                })

    logger.info(f"Transkript tamamlandı: {len(words)} kelime bulundu.")
    return words


def group_words_into_chunks(words: List[Dict], chunk_size: int = 4) -> List[Dict]:
    """
    Kelimeleri subtitle ekranı başına chunk_size kelimelik gruplara böler.

    Args:
        words: get_word_timestamps() çıktısı.
        chunk_size: Her ekranda gösterilecek kelime sayısı (3–5 önerilir).

    Returns:
        [{"text": "SAVE MORE MONEY", "start": 0.0, "end": 1.5}, ...]
    """
    chunks = []
    for i in range(0, len(words), chunk_size):
        group = words[i:i + chunk_size]
        if not group:
            continue
        # Altyazı büyük harf olacak (daha okunaklı)
        text = " ".join(w["word"] for w in group).upper()
        chunks.append({
            "text": text,
            "start": group[0]["start"],
            "end": group[-1]["end"],
        })
    return chunks


def _seconds_to_ass_time(seconds: float) -> str:
    """Saniyeyi ASS timestamp formatına çevirir: H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = int((s - int(s)) * 100)
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


def generate_ass_subtitle(chunks: List[Dict], output_path: Path) -> Path:
    """
    ASS formatında altyazı dosyası oluşturur.

    Stil özellikleri:
      - Font: Arial, 80pt
      - Renk: Beyaz yazı, Siyah outline (4px)
      - Konum: Ekran alt-ortası (Alignment=2, MarginV=150)
      - Gölge: 2px
    """
    # ASS dosya başlığı ve stil tanımı
    ass_content = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,4,2,2,60,60,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Her chunk için bir dialogue satırı
    dialogue_lines = []
    for chunk in chunks:
        start = _seconds_to_ass_time(chunk["start"])
        end   = _seconds_to_ass_time(chunk["end"])
        # ASS özel karakterlerini escape et
        text  = chunk["text"].replace("\\", "\\\\").replace("{", "\\{")
        dialogue_lines.append(
            f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}"
        )

    ass_content += "\n".join(dialogue_lines)

    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.write(ass_content)

    logger.info(f"✅ ASS altyazı dosyası oluşturuldu: {output_path} ({len(chunks)} satır)")
    return output_path


def create_subtitles(audio_path: Path) -> Path:
    """
    Tam altyazı pipeline'ı: Ses → Whisper → Chunk → ASS dosyası.

    Args:
        audio_path: Transkript edilecek ses dosyasının yolu.

    Returns:
        Oluşturulan .ass dosyasının yolu (temp/subtitles.ass).
    """
    words = get_word_timestamps(audio_path)

    if not words:
        logger.error("❌ Whisper hiç kelime bulamadı. Ses dosyasını kontrol edin.")
        sys.exit(1)

    chunks = group_words_into_chunks(words, chunk_size=4)
    ass_path = TEMP_DIR / "subtitles.ass"
    generate_ass_subtitle(chunks, ass_path)
    return ass_path


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print("Kullanım: python -m scripts.subtitle_generator <ses_dosyası.mp3>")
        _sys.exit(1)

    audio = Path(_sys.argv[1])
    if not audio.exists():
        print(f"Hata: Dosya bulunamadı: {audio}")
        _sys.exit(1)

    sub_path = create_subtitles(audio)
    print(f"\n✅ Altyazı dosyası: {sub_path}")
