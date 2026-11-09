@echo off
REM Windows Guvenlik Duvari'nda 5000 portunu (yalnizca Etki Alani ve Ozel aglar icin) acar.
REM Yonetici izni ister. Bir kez calistirmaniz yeterlidir.
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Yonetici izni isteniyor...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    goto :eof
)
powershell -NoProfile -Command "if (Get-NetFirewallRule -DisplayName 'Test Takip Dashboard' -ErrorAction SilentlyContinue) { Write-Host 'Kural zaten var.' } else { New-NetFirewallRule -DisplayName 'Test Takip Dashboard' -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow -Profile Domain,Private | Out-Null; Write-Host 'Kural eklendi: TCP 5000 (Etki Alani, Ozel).' }"
echo.
pause
