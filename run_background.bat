@echo off
:: YouTube Shorts Pipeline - Arka plan launcher
:: Terminal kapansa bile calismayi surdurmek icin

set PROJ_DIR=c:\Users\pc\Desktop\youtube otomasyon
set LOG_FILE=%PROJ_DIR%\logs\pipeline_run.log
set PATH=%PATH%;C:\ffmpeg\bin

cd /d "%PROJ_DIR%"

echo [%DATE% %TIME%] Pipeline baslatiliyor... >> "%LOG_FILE%"

python run_daily.py --dry-run --use-existing-script >> "%LOG_FILE%" 2>&1

echo [%DATE% %TIME%] Pipeline tamamlandi. >> "%LOG_FILE%"
