"""
script_generator.py — Gemini API ile günlük YouTube Shorts scripti üretir.

Üretilen içerik:
  - video başlığı (60 karakter altı)
  - açıklama metni + hashtag'ler
  - 5 adet etiket
  - 100-125 kelimelik konuşma scripti
  - Pexels arama anahtar kelimesi

Tüm içerik data/daily_content.json dosyasına kaydedilir.
Kullanılan konular data/used_topics.json dosyasında tutulur.
"""

import json
import random
import sys
from datetime import date, datetime
from pathlib import Path

from google import genai
from google.genai import types

from scripts.config import GEMINI_API_KEY, DATA_DIR, DAILY_CONTENT_FILE, USED_TOPICS_FILE
from scripts.logger import logger

# ── Konu Havuzu ──────────────────────────────────────────────────────────────
TOPIC_POOL = [
    "budgeting techniques",
    "compound interest",
    "saving habits",
    "debt management",
    "investment psychology",
    "income growth habits",
    "money mindset",
    "discipline and productivity",
    "morning routines",
    "overcoming procrastination",
]

# Konuya göre Pexels arama anahtar kelimeleri
TOPIC_PEXELS_KEYWORDS: dict[str, str] = {
    "budgeting techniques":       "budget money finance planning",
    "compound interest":          "money growth savings coins",
    "saving habits":              "piggy bank savings money jar",
    "debt management":            "stress money bills finance",
    "investment psychology":      "stock market trading charts finance",
    "income growth habits":       "success business work laptop",
    "money mindset":              "wealth mindset success motivation",
    "discipline and productivity": "focus productivity desk work",
    "morning routines":           "morning sunrise coffee routine",
    "overcoming procrastination": "motivation clock time focus",
}


# ── Konu Seçimi ───────────────────────────────────────────────────────────────
def load_used_topics() -> list[dict]:
    """Kullanılmış konu geçmişini yükle."""
    if USED_TOPICS_FILE.exists():
        with open(USED_TOPICS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_used_topic(topic: str) -> None:
    """Kullanılan konuyu geçmişe ekle (maksimum havuz boyutu - 1 kayıt tutar)."""
    history = load_used_topics()
    history.append({"topic": topic, "date": date.today().isoformat()})
    # Son (pool_size - 1) kaydı tut, böylece tüm havuz asla bloke olmaz
    history = history[-(len(TOPIC_POOL) - 1):]
    with open(USED_TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def pick_topic() -> str:
    """Son 2 günde kullanılmayan bir konu seç."""
    history = load_used_topics()
    recently_used = [entry["topic"] for entry in history[-2:]]
    available = [t for t in TOPIC_POOL if t not in recently_used]
    if not available:
        logger.warning("Tüm konular son 2 günde kullanılmış, havuzun tamamından seçiliyor.")
        available = TOPIC_POOL
    chosen = random.choice(available)
    logger.debug(f"Seçilen konu: '{chosen}' (son kullanılanlar: {recently_used})")
    return chosen


# ── JSON Temizleme ────────────────────────────────────────────────────────────
def clean_json_response(text: str) -> str:
    """
    Gemini'nin yanıtından markdown kod bloklarını (```json ... ```) temizler.
    Bazı model yanıtları backtick ile başlar/biter, bu güvenlik adımı onu önler.
    """
    text = text.strip()
    # Başlangıçtaki ```json veya ``` kaldır
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    # Sondaki ``` kaldır
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


# ── Script Üretimi ────────────────────────────────────────────────────────────
def generate_script(topic: str | None = None) -> dict:
    """
    Belirtilen (veya otomatik seçilen) konu için Gemini API ile script üretir.

    Returns:
        Başlık, açıklama, etiketler, script ve Pexels keyword içeren dict.

    Raises:
        SystemExit(1): API hatası veya JSON parse hatası durumunda.
    """
    if topic is None:
        topic = pick_topic()

    logger.info(f"Konu: '{topic}' için script üretiliyor...")

    prompt = f"""Respond ONLY with a valid JSON object. No markdown, no backticks, no explanation before or after the JSON.

Generate a YouTube Shorts script on the topic: "{topic}"

STRICT RULES (follow ALL of these exactly):
1. Hook: Start with ONE punchy sentence that grabs attention in the first 2 seconds.
2. Share ONE clear, actionable tip or insight — focused, not vague.
3. Explanation: 3-4 sentences in natural, conversational American English. Write like a knowledgeable friend talking — NOT like a translation.
4. Call-to-action: 1 sentence CTA (e.g., "Follow for more money tips!" or "Share this with someone who needs it!").
5. MANDATORY DISCLAIMER: The LAST line of the script MUST be exactly: "This is for informational purposes only, not financial advice."
6. WORD COUNT: Script must be 110-125 words total (count carefully — this fills 40-55 seconds at speaking pace).
7. Language: Natural, native American English. Energetic, relatable tone.
8. ABSOLUTELY NO direct financial advice. Do NOT say "buy X", "invest in Y", "sell Z", or recommend specific stocks/crypto.

Return ONLY this JSON (no extra keys, no text outside the JSON object):
{{
  "topic": "{topic}",
  "title": "Eye-catching YouTube Shorts title, under 60 characters",
  "description": "2–3 engaging sentences summarizing the video. Add these hashtags at the end: #Shorts #Finance #PersonalFinance #SelfImprovement #MoneyTips",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "script": "Full script here — natural, conversational, energetic.",
  "pexels_keyword": "2–4 word search term for portrait stock video (e.g. morning coffee, city finance, saving money)"
}}"""

    raw_text = ""
    try:
        import time as _time
        client = genai.Client(api_key=GEMINI_API_KEY)

        # Model öncelik sırası: lite modeller daha az kota kullanır
        MODELS_TO_TRY = [
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash-lite",
            "gemini-flash-lite-latest",
        ]
        MAX_RETRIES = 3

        response = None
        last_error = None
        for attempt in range(MAX_RETRIES):
            for model_name in MODELS_TO_TRY:
                try:
                    logger.debug(f"Deneniyor: {model_name} (deneme {attempt+1}/{MAX_RETRIES})")
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    logger.debug(f"Basarili: {model_name}")
                    break
                except Exception as model_err:
                    err_str = str(model_err)
                    last_error = model_err
                    # 503 (sunucu mesgul) veya 429 (kota/rate-limit) -> siradaki modeli dene
                    if any(code in err_str for code in ["503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"]):
                        logger.debug(f"{model_name} kullanilamiyor ({err_str[:60]}...), siradaki model deneniyor")
                        continue
                    raise  # Baska bir hata -> yukari firlatil

            if response is not None:
                break

            # Tum modeller basarisiz -> bekle ve tekrar dene
            wait_secs = 30 * (attempt + 1)  # 30s, 60s, 90s
            logger.warning(f"Tum modeller basarisiz (deneme {attempt+1}/{MAX_RETRIES}), {wait_secs}s bekleniyor...")
            _time.sleep(wait_secs)

        if response is None:
            if last_error and ("429" in str(last_error) or "RESOURCE_EXHAUSTED" in str(last_error)):
                logger.error(
                    "Gemini API kotasi tuketildi (limit: 0). "
                    "Cozum: https://aistudio.google.com/app/apikey adresinden "
                    "yeni bir API key olusturun ve .env dosyasindaki GEMINI_API_KEY degerini guncelleyin."
                )
            raise RuntimeError(f"Tum modeller ve tum denemeler basarisiz: {last_error}")

        raw_text = response.text

        cleaned = clean_json_response(raw_text)
        content: dict = json.loads(cleaned)

        # Zorunlu alanları doğrula
        required = ["topic", "title", "description", "tags", "script", "pexels_keyword"]
        missing = [f for f in required if f not in content]
        if missing:
            raise ValueError(f"Gemini yanıtında eksik alanlar: {missing}")

        # Başlık 60 karakter kontrolü
        if len(content["title"]) > 65:
            logger.warning(f"Başlık {len(content['title'])} karakter, 60'ı geçiyor.")

        # Sorumluluk reddi garantisi: model eklemediyse kod tarafında ekle
        DISCLAIMER = "This is for informational purposes only, not financial advice."
        if DISCLAIMER.lower() not in content["script"].lower():
            content["script"] = content["script"].rstrip() + f" {DISCLAIMER}"
            logger.debug("Sorumluluk reddi script'e kod tarafında eklendi.")

        # Metadata ekle
        content["generated_at"] = datetime.now().isoformat()
        if "pexels_keyword" not in content:
            content["pexels_keyword"] = TOPIC_PEXELS_KEYWORDS.get(topic, "finance money")

        # Kaydet
        with open(DAILY_CONTENT_FILE, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        logger.info(f"Script kaydedildi → {DAILY_CONTENT_FILE}")

        save_used_topic(topic)
        logger.info(f"✅ Script üretildi | Başlık: {content['title']}")
        return content

    except json.JSONDecodeError as e:
        logger.error(f"Gemini yanıtı JSON olarak parse edilemedi: {e}")
        logger.debug(f"Ham yanıt (ilk 500 karakter): {raw_text[:500]}")
        sys.exit(1)

    except ValueError as e:
        logger.error(f"Gemini yanıtı doğrulama hatası: {e}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Gemini API hatası: {type(e).__name__}: {e}")
        logger.error("Olası nedenler: geçersiz API key, kota aşımı, ağ hatası.")
        sys.exit(1)


if __name__ == "__main__":
    content = generate_script()
    print("\n" + "=" * 60)
    print("📄 ÜRETİLEN İÇERİK")
    print("=" * 60)
    print(f"Konu     : {content['topic']}")
    print(f"Başlık   : {content['title']} ({len(content['title'])} karakter)")
    print(f"Etiketler: {', '.join(content['tags'])}")
    print(f"Pexels   : {content['pexels_keyword']}")
    print(f"\nScript:\n{'-'*40}\n{content['script']}")
    print(f"\nAçıklama:\n{content['description']}")
