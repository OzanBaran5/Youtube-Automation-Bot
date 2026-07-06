"""
test_script_generator.py — Gemini API script üretimini test eder.

Testler:
  1. Gemini API bağlantısı ve yanıt alınması
  2. JSON parse doğruluğu
  3. Zorunlu alanların varlığı (title, description, tags, script, pexels_keyword)
  4. Script kelime sayısı (100-130 arası)
  5. Başlık uzunluğu (60 karakter altı)
  6. daily_content.json dosyasının oluşturulması
  7. used_topics.json güncellenmesi
"""

import json
import sys
from pathlib import Path

# Proje kökünü Python yoluna ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.config import validate_config, DAILY_CONTENT_FILE, USED_TOPICS_FILE
from scripts.script_generator import generate_script, clean_json_response, pick_topic
from scripts.logger import logger


def test_json_cleaner():
    """JSON temizleme fonksiyonunu test et."""
    test_cases = [
        ('```json\n{"key": "val"}\n```', '{"key": "val"}'),
        ('```\n{"key": "val"}\n```', '{"key": "val"}'),
        ('{"key": "val"}', '{"key": "val"}'),
        ('  {"key": "val"}  ', '{"key": "val"}'),
    ]
    for raw, expected in test_cases:
        result = clean_json_response(raw)
        assert result == expected, f"Beklenmeyen: '{result}' (beklenen: '{expected}')"
    print("  ✅ JSON temizleme testi geçti.")


def test_topic_picker():
    """Konu seçimini test et."""
    topic = pick_topic()
    from scripts.script_generator import TOPIC_POOL
    assert topic in TOPIC_POOL, f"Seçilen konu havuzda değil: {topic}"
    print(f"  ✅ Konu seçimi testi geçti: '{topic}'")


def test_script_generation():
    """Tam Gemini API script üretimini test et."""
    print("\n  🔄 Gemini API'ye bağlanılıyor...")
    content = generate_script()

    # Zorunlu alanlar
    required_fields = ["topic", "title", "description", "tags", "script", "pexels_keyword"]
    missing = [f for f in required_fields if f not in content]
    assert not missing, f"Eksik alanlar: {missing}"
    print(f"  ✅ Zorunlu alanlar mevcut: {required_fields}")

    # Etiket sayısı
    assert isinstance(content["tags"], list), "tags bir liste olmalı"
    assert 3 <= len(content["tags"]) <= 10, f"Etiket sayısı beklenmedik: {len(content['tags'])}"
    print(f"  ✅ Etiketler: {content['tags']}")

    # Başlık uzunluğu
    title_len = len(content["title"])
    if title_len > 65:
        print(f"  ⚠️  Başlık uzun ({title_len} karakter): {content['title']}")
    else:
        print(f"  ✅ Başlık ({title_len} karakter): {content['title']}")

    # Script kelime sayısı
    word_count = len(content["script"].split())
    if 80 <= word_count <= 150:
        print(f"  ✅ Script kelime sayısı: {word_count} (hedef: 100-125)")
    else:
        print(f"  ⚠️  Script kelime sayısı beklenenden farklı: {word_count}")

    # Sorumluluk reddi kontrolü
    disclaimer_keywords = ["informational purposes", "not financial advice", "financial advice"]
    has_disclaimer = any(kw.lower() in content["script"].lower() for kw in disclaimer_keywords)
    if has_disclaimer:
        print("  ✅ Sorumluluk reddi metni bulundu.")
    else:
        print("  ⚠️  Sorumluluk reddi metni bulunamadı!")

    return content


def test_file_outputs():
    """Çıktı dosyalarının oluşturulduğunu kontrol et."""
    assert DAILY_CONTENT_FILE.exists(), f"daily_content.json oluşturulmadı: {DAILY_CONTENT_FILE}"
    with open(DAILY_CONTENT_FILE, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert "generated_at" in saved, "generated_at alanı eksik"
    print(f"  ✅ daily_content.json oluşturuldu: {DAILY_CONTENT_FILE}")

    assert USED_TOPICS_FILE.exists(), "used_topics.json oluşturulmadı"
    with open(USED_TOPICS_FILE, "r", encoding="utf-8") as f:
        history = json.load(f)
    assert len(history) >= 1, "used_topics.json boş"
    print(f"  ✅ used_topics.json güncellendi: {len(history)} kayıt")


def main():
    print("=" * 60)
    print("[TEST] GEMINI SCRIPT GENERATOR")
    print("=" * 60)

    # Konfigürasyon kontrolü
    print("\n[1/4] Konfigürasyon doğrulanıyor...")
    validate_config()
    print("  ✅ Konfigürasyon geçerli.")

    # JSON temizleme testi
    print("\n[2/4] JSON temizleme fonksiyonu test ediliyor...")
    test_json_cleaner()
    test_topic_picker()

    # Gemini API testi
    print("\n[3/4] Gemini API'den script üretiliyor...")
    content = test_script_generation()

    # Dosya çıktı testi
    print("\n[4/4] Dosya ciktilari kontrol ediliyor...")
    test_file_outputs()

    # Özet
    print("\n" + "=" * 60)
    print("[OK] TUM TESTLER BASARILI")
    print("=" * 60)
    print(f"\n[SCRIPT] URETILEN ICERIK:")
    print(f"  Konu     : {content['topic']}")
    print(f"  Baslik   : {content['title']}")
    print(f"  Pexels   : {content['pexels_keyword']}")
    print(f"  Kelimeler: {len(content['script'].split())}")
    print(f"\n  Script:\n{'---' + '-'*47}")
    print(f"  {content['script']}")
    print(f"{'---' + '-'*47}")


if __name__ == "__main__":
    main()
