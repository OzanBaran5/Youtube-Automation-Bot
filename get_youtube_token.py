"""
Tek seferlik YouTube OAuth2 token alma.
Bu script sadece bir kez calistirilir. Token kaydedildikten sonra
run_daily.py otomatik olarak bu tokeni kullanir.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_PATH", "./client_secret.json")
TOKEN_OUT     = os.getenv("GOOGLE_YOUTUBE_TOKEN_PATH", "./token_youtube.json")
SCOPES        = ["https://www.googleapis.com/auth/youtube.upload"]

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")

print("=" * 65)
print("YouTube OAuth2 Token Alma")
print("=" * 65)
print()
print("ADIM 1 — Su URL'i tarayicinizda acin:")
print()
print(auth_url)
print()
print("=" * 65)
print("ADIM 2 — Google hesabinizla giris yapin, izin verin.")
print("Ekranda bir yetkilendirme KODU goreceksiniz.")
print("=" * 65)
print()

code = input("ADIM 3 — Kodu buraya yapistirin + Enter: ").strip()

flow.fetch_token(code=code)
creds = flow.credentials

with open(TOKEN_OUT, "w") as f:
    f.write(creds.to_json())

print()
print(f"YouTube token kaydedildi: {TOKEN_OUT}")
print("Artik 'python run_daily.py' ile YouTube'a yukleme yapilabilir!")
