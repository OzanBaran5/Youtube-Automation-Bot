"""
Tek seferlik TTS OAuth2 token alma — Manuel URL yontemi.

Adimlar:
  1. Bu scripti calistirin
  2. Ekrandaki URL'i kopyalayip tarayicida acin
  3. Google hesabinizla giris yapin ve izin verin
  4. Tarayici "localhost'a baglanamadi" diyecek — URL'deki "code=" degerini kopyalayin
  5. Terminale yapistirin ve Enter'a basin
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_PATH", "./client_secret.json")
TOKEN_OUT     = os.getenv("GOOGLE_TTS_TOKEN_PATH", "./token_tts.json")
SCOPES        = ["https://www.googleapis.com/auth/cloud-platform"]

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)

# Manuel redirect_uri ile authorization URL olustur
flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
auth_url, _ = flow.authorization_url(
    access_type="offline",
    prompt="consent",
)

print("=" * 65)
print("ADIM 1 — Su URL'i kopyalayip tarayicinizda acin:")
print("=" * 65)
print()
print(auth_url)
print()
print("=" * 65)
print("ADIM 2 — Tarayicida Google'a giris yapin ve izin verin.")
print("Izin verdikten sonra ekranda bir KOD goreceksiniz.")
print("(Sayfada 'Yetkilendirme kodu' veya uzun bir metin)")
print("=" * 65)
print()

code = input("ADIM 3 — O kodu buraya yapistirin ve Enter'a basin: ").strip()

flow.fetch_token(code=code)
creds = flow.credentials

with open(TOKEN_OUT, "w") as f:
    f.write(creds.to_json())

print()
print(f"Token basariyla kaydedildi: {TOKEN_OUT}")
print("Artik TTS otomatik calisacak!")
