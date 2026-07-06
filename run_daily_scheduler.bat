@echo off
:: YouTube Shorts - Gunluk Otomatik Calistirici
:: Windows Task Scheduler tarafindan her sabah calistirilir

set PROJ_DIR=c:\Users\pc\Desktop\youtube otomasyon
set LOG_FILE=%PROJ_DIR%\logs\scheduler.log
set PATH=%PATH%;C:\ffmpeg\bin

cd /d "%PROJ_DIR%"

echo. >> "%LOG_FILE%"
echo ============================================ >> "%LOG_FILE%"
echo [%DATE% %TIME%] Gunluk pipeline baslatildi >> "%LOG_FILE%"
echo ============================================ >> "%LOG_FILE%"

python run_daily.py >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% EQU 0 (
    echo [%DATE% %TIME%] Pipeline BASARILI tamamlandi >> "%LOG_FILE%"
) else (
    echo [%DATE% %TIME%] Pipeline HATA ile sonlandi - Log kontrol edin >> "%LOG_FILE%"
)
