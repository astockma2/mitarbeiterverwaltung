@echo off
chcp 65001 >nul
title Mitarbeiterverwaltung - Alle Dienste beenden

echo ============================================
echo   Mitarbeiterverwaltung - Stop
echo ============================================
echo.

:: 1. Cloudflare Tunnel beenden
echo [1/4] Cloudflare Tunnel beenden...
taskkill /IM cloudflared.exe /F >nul 2>&1
if errorlevel 1 (
    echo       Kein Tunnel aktiv.
) else (
    echo       OK - Tunnel beendet.
)
echo.

:: 2. Frontend beenden (Node-Prozess auf Port 3000)
echo [2/4] Frontend beenden (Port 3000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000.*LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo       OK - Frontend beendet.
echo.

:: 3. Backend beenden (Uvicorn auf Port 8000, nur im Entwicklungsmodus)
echo [3/4] Backend beenden (Port 8000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000.*LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo       OK - Backend beendet.
echo.

:: 4. Docker-Dienste beenden (falls aktiv)
echo [4/4] Docker-Dienste beenden...
docker compose down >nul 2>&1
if errorlevel 1 (
    echo       Keine Docker-Dienste aktiv (Entwicklungsmodus).
) else (
    echo       OK - Docker-Dienste beendet.
)
echo.

:: Temp-Dateien aufraeumen
del tunnel.log >nul 2>&1
del tunnel_url.txt >nul 2>&1

echo ============================================
echo   Alle Dienste beendet.
echo ============================================
echo.
echo   Hinweis: Die Datenbank-Daten bleiben erhalten.
echo   Docker-Volume loeschen: docker compose down -v
echo   SQLite-DB loeschen:     del backend\mitarbeiterverwaltung.db
echo ============================================
