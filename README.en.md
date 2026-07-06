<div align="right">
  <a href="README.md">🇹🇷 Türkçe</a>
</div>

# 🎬 YouTube Shorts Automation Pipeline

A fully automated Python pipeline that produces and uploads a daily 40–55 second vertical (9:16) YouTube Shorts video on finance literacy and personal development topics.

---

## 📋 Table of Contents

1. [System Requirements](#-system-requirements)
2. [FFmpeg Installation (Windows)](#-ffmpeg-installation-windows)
3. [Python Setup & Dependencies](#-python-setup--dependencies)
4. [API Keys Setup](#-api-keys-setup)
5. [Google OAuth2 Setup](#-google-oauth2-setup)
6. [Project Structure](#-project-structure)
7. [Usage](#-usage)
8. [First Run & OAuth Authorization](#-first-run--oauth-authorization)
9. [Automated Daily Run with Windows Task Scheduler](#-automated-daily-run-with-windows-task-scheduler)
10. [Testing Guide](#-testing-guide)
11. [Troubleshooting](#-troubleshooting)

---

## 🖥 System Requirements

- **OS**: Windows 10/11 (64-bit)
- **Python**: 3.10 or higher ([python.org](https://www.python.org/downloads/))
- **FFmpeg**: See installation steps below
- **Internet Connection**: Required for API calls and video downloads

---

## 🎞 FFmpeg Installation (Windows)

> **⚠️ IMPORTANT**: Video rendering and Whisper subtitle generation will not work without FFmpeg.

### Step 1 — Download FFmpeg

1. Open your browser and go to:
   **https://github.com/BtbN/FFmpeg-Builds/releases**

2. In the latest release, under **"Assets"**, download:
   ```
   ffmpeg-master-latest-win64-gpl.zip
   ```
   *(approximately 100–150 MB)*

   > Alternative source: **https://ffmpeg.org/download.html** → Windows → gyan.dev builds

### Step 2 — Extract the ZIP

1. Right-click the downloaded ZIP → **"Extract All..."**
2. Set the destination to:
   ```
   C:\
   ```
3. Click **"Extract"**.

4. The extracted folder will be named something like `ffmpeg-master-latest-win64-gpl`.
   **Rename** it to: `ffmpeg`

   Your directory should look like:
   ```
   C:\ffmpeg\
     ├── bin\
     │   ├── ffmpeg.exe    ← This is the important file
     │   ├── ffprobe.exe
     │   └── ffplay.exe
     ├── doc\
     └── ...
   ```

### Step 3 — Add to PATH Environment Variable

1. Press **Win + R** → type `sysdm.cpl` → **OK**

2. Click the **"Advanced"** tab → click **"Environment Variables..."**

3. In the **"System variables"** section, find **`Path`** → double-click it

4. Click **"New"** in the top-right corner

5. Type:
   ```
   C:\ffmpeg\bin
   ```

6. Click **OK** → **OK** → **OK** to close all windows

### Step 4 — Verify Installation

Open a **new** PowerShell or Command Prompt window:

```powershell
ffmpeg -version
```

You should see output like:
```
ffmpeg version N-xxx-gxxxxxxx Copyright (c) 2000-2024 ...
```

✅ If you see this output, FFmpeg is successfully installed.

---

## 🐍 Python Setup & Dependencies

### Step 1 — Create a Virtual Environment (Recommended)

Open PowerShell in the project folder:

```powershell
cd "c:\Users\pc\Desktop\youtube otomasyon"
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> **Note**: If you get a script execution policy error in PowerShell:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### Step 2 — Install Dependencies

```powershell
pip install -r requirements.txt
```

> **Note**: Installing `openai-whisper` will also download `torch` (~2 GB). The first install may take a while.

---

## 🔑 API Keys Setup

### 1. Gemini API Key

1. Go to **https://aistudio.google.com/app/apikey**
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the generated API key
5. Paste it into the `.env` file under `GEMINI_API_KEY=`

### 2. Pexels API Key

1. Go to **https://www.pexels.com/api/**
2. Click **"Get Started"** → Sign up (free)
3. Copy the API key from your dashboard
4. Paste it into the `.env` file under `PEXELS_API_KEY=`

---

## 🔐 Google OAuth2 Setup

The same `client_secret.json` file is used for both TTS and YouTube uploads.

### Creating a New OAuth2 Client (if needed)

1. Go to **https://console.cloud.google.com**

2. Select your project from the top (or create a new one)

3. Left menu → **"APIs & Services"** → **"Library"**
   - Enable **Google Cloud Text-to-Speech API**
   - Enable **YouTube Data API v3**

4. Left menu → **"APIs & Services"** → **"Credentials"**

5. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**

6. Application type: **"Desktop app"** → Name: anything you like → **"Create"**

7. Click **"DOWNLOAD JSON"** → save the file

8. Copy the downloaded file to the project root and rename it to `client_secret.json`

### Check Your `.env` File

```env
GOOGLE_OAUTH_CLIENT_SECRET_PATH=./client_secret.json
GOOGLE_TTS_TOKEN_PATH=./token_tts.json
GOOGLE_YOUTUBE_TOKEN_PATH=./token_youtube.json
```

---

## 📁 Project Structure

```
youtube otomasyon/
├── .env                          # API keys (secret — never commit to Git)
├── .env.example                  # Template .env file
├── client_secret.json            # Google OAuth2 client (secret)
├── token_tts.json                # TTS token (auto-generated)
├── token_youtube.json            # YouTube token (auto-generated)
├── requirements.txt              # Python dependencies
├── run_daily.py                  # 🚀 Main pipeline script
│
├── scripts/
│   ├── config.py                 # Environment variables & path config
│   ├── logger.py                 # Logging
│   ├── script_generator.py      # Gemini API → script generation
│   ├── tts_generator.py         # Google TTS OAuth2 → audio
│   ├── subtitle_generator.py    # Whisper → ASS subtitles
│   ├── music_downloader.py      # Royalty-free music downloader
│   ├── video_builder.py         # Pexels + FFmpeg → video render
│   └── youtube_uploader.py      # YouTube Data API v3 → upload
│
├── data/
│   ├── daily_content.json        # Today's generated content
│   ├── used_topics.json          # Topic history (prevents repeats)
│   └── upload_log.csv            # YouTube upload history
│
├── output/
│   └── YYYY-MM-DD_video.mp4     # Final rendered videos
│
├── assets/
│   └── music/                   # Background music tracks (.mp3)
│
├── temp/                        # Temporary files (auto-cleaned)
├── logs/                        # Daily log files
│
└── tests/
    ├── test_script_generator.py  # Gemini API test
    └── test_tts.py              # TTS OAuth2 test
```

---

## 🚀 Usage

```powershell
# Navigate to the project folder and activate the virtual environment
cd "c:\Users\pc\Desktop\youtube otomasyon"
.\venv\Scripts\Activate.ps1

# Full pipeline (generate video + upload to YouTube)
python run_daily.py

# Dry-run: generate video locally, skip upload
python run_daily.py --dry-run

# Generate video but skip upload
python run_daily.py --skip-upload

# Run with a specific topic
python run_daily.py --topic "saving habits"

# Use the existing script (skip Gemini API call — useful when quota is exhausted)
python run_daily.py --use-existing-script

# Help
python run_daily.py --help
```

---

## 🔑 First Run & OAuth Authorization

On the first run, **two separate OAuth authorizations** are required:

### 1. TTS Authorization (first `run_daily.py` or `tests/test_tts.py`)

1. You'll see this message in the terminal:
   ```
   Opening browser for TTS authorization...
   ```
2. Your browser will open automatically
3. Sign in with your Google account
4. Click **"Allow"** on the consent screen
5. `token_tts.json` is saved automatically
6. On subsequent runs, the browser won't open (token auto-refreshes)

### 2. YouTube Authorization (first real upload)

Same process, different consent screen → `token_youtube.json` is created.

> **⚠️ Token Expiry**: Google OAuth refresh tokens are generally long-lived.
> However, if unused for a long time or if security settings change, the token may expire.
> In that case, the script will display a clear error message asking you to delete the token file.

---

## ⏰ Automated Daily Run with Windows Task Scheduler

To run automatically every morning at 09:00:

### Step 1 — The Batch Script

The file `run_daily_scheduler.bat` is already included in the project. It:
- Sets the correct working directory
- Adds FFmpeg to PATH
- Runs `run_daily.py` and writes output to `logs\scheduler.log`

### Step 2 — Set Up Task Scheduler

1. Press **Win + R** → type `taskschd.msc` → **OK**

2. In the right panel, click **"Create Basic Task..."**

3. **Name**: `YouTube Shorts Daily` → **Next**

4. **Trigger**: `Daily` → **Next**

5. **Start time**: `09:00:00` → **Next**

6. **Action**: `Start a program` → **Next**

7. **Program/Script**: Browse and select `run_daily_scheduler.bat`

8. **Start in**:
   ```
   c:\Users\pc\Desktop\youtube otomasyon
   ```

9. **Finish** → **OK**

### Step 3 — Test It

Right-click the created task → **"Run"** → check the log file.

---

## 🧪 Testing Guide

### Test 1 — Gemini Script Generation (no FFmpeg required)

```powershell
python tests/test_script_generator.py
```

Expected output:
```
Configuration valid.
JSON cleaning test passed.
Topic selection test passed.
Required fields present.
ALL TESTS PASSED
```

### Test 2 — TTS OAuth2 (no FFmpeg required)

```powershell
python tests/test_tts.py
```

The browser will open on the first run. After granting permission:
```
OAuth2 successful — token: ./token_tts.json
Audio file created: temp/test_audio.mp3
ALL TTS TESTS PASSED
```

### Test 3 — Dry-Run (requires FFmpeg)

```powershell
python run_daily.py --dry-run
```

Runs the full pipeline but skips the YouTube upload.
The final video is saved to `output/YYYY-MM-DD_video.mp4`.

### Test 4 — Full Pipeline

```powershell
python run_daily.py
```

---

## 🔧 Troubleshooting

### `ffmpeg: command not found`
→ Install FFmpeg and add it to PATH (see steps above).
→ Open a **new** terminal window after updating PATH.

### `GEMINI_API_KEY is missing`
→ Check that the key is correctly defined in `.env`.
→ Do not use quotes: `GEMINI_API_KEY=AIzaSy...` (correct)

### `Gemini 429 RESOURCE_EXHAUSTED` (limit: 0)
→ Your API key's free tier quota is exhausted or not configured.
→ Create a new key at **https://aistudio.google.com/app/apikey** and update `.env`.

### `OAuth client secret not found`
→ Verify that `client_secret.json` exists in the project root.
→ Check that the filename is exactly `client_secret.json`.

### `TTS token refresh failed`
→ Delete `token_tts.json` and run the script again.
→ A new browser authorization will be triggered.

### `YouTube API quota exceeded`
→ YouTube Data API has a daily quota of 10,000 units (1 upload ≈ 1,600 units).
→ Try again the next day or check your quota in Google Cloud Console.

### Pexels videos not found
→ Verify `PEXELS_API_KEY` is correctly set in `.env`.
→ Check the `pexels_keyword` field in `data/daily_content.json`.

### Whisper is slow
→ The `base` model can be slow on CPU — this is normal (may take 2–3 minutes).
→ If you have a GPU: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`

---

## 📊 Log Files

| File | Contents |
|------|----------|
| `logs/YYYY-MM-DD.log` | Detailed daily run log |
| `data/upload_log.csv` | YouTube upload history (video ID, URL, date) |
| `data/used_topics.json` | Topic history (prevents repeating topics) |

---

## 🛡 Security Notes

- **Never commit** `.env`, `client_secret.json`, `token_tts.json`, or `token_youtube.json` to Git
- Add them to `.gitignore`:
  ```
  .env
  client_secret.json
  token_*.json
  ```

---

## ⚖️ Legal Notes

- All generated content is **for informational purposes only** and does not constitute financial advice
- Pexels videos are used under the [Pexels License](https://www.pexels.com/license/)
- Background music tracks are CC0 / public domain licensed
