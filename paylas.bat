@echo off
chcp 65001 >nul
REM Test Takip Dashboard - yerel agda paylasim modu (waitress, debug kapali, sifreli giris)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Sanal ortam olusturuluyor...
    python -m venv .venv || goto :error
)

echo Bagimliliklar kontrol ediliyor...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :error

REM Sifre yoksa bir kez sor
".venv\Scripts\python.exe" sifre_belirle.py --yoksa || goto :error

echo.
".venv\Scripts\python.exe" serve.py
goto :eof

:error
echo.
echo HATA: Baslatma basarisiz oldu.
pause
