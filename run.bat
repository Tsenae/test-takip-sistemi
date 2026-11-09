@echo off
REM Test Takip Dashboard - Windows baslatma betigi
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Sanal ortam olusturuluyor...
    python -m venv .venv || goto :error
)

echo Bagimliliklar kontrol ediliyor...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :error

echo.
echo Uygulama baslatiliyor: http://127.0.0.1:5000
echo Durdurmak icin CTRL+C
echo.
".venv\Scripts\python.exe" app.py
goto :eof

:error
echo.
echo HATA: Kurulum basarisiz oldu. Python'un kurulu ve PATH'te oldugundan emin olun.
pause
