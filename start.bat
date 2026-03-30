@echo off
chcp 65001 >nul
title Mitarbeiterverwaltung - Alle Dienste starten

echo ============================================
echo   Mitarbeiterverwaltung - Start
echo ============================================
echo.

:: Cloudflared finden
set "CLOUDFLARED="
where cloudflared >nul 2>&1 && set "CLOUDFLARED=cloudflared"
if "%CLOUDFLARED%"=="" (
    if exist "%LOCALAPPDATA%\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe" (
        set "CLOUDFLARED=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe"
    )
)

:: Modus erkennen: Docker (mit .env) oder Entwicklung (SQLite)
if exist ".env" (
    goto start_docker
) else (
    goto start_dev
)

:: ============================================
:: DOCKER-MODUS (PostgreSQL, Redis, Backend, Celery)
:: ============================================
:start_docker
echo   Modus: Docker (PostgreSQL)
echo.

echo [1/4] Docker-Dienste starten (PostgreSQL, Redis, Backend, Celery)...
docker compose up -d
if errorlevel 1 (
    echo [FEHLER] Docker-Dienste konnten nicht gestartet werden.
    echo          Ist Docker Desktop gestartet?
    pause
    exit /b 1
)
echo       OK - Docker-Dienste laufen.
echo.

echo [2/4] Warte auf Backend (Port 8000)...
set /a count=0
:wait_docker
set /a count+=1
if %count% gtr 30 (
    echo [WARNUNG] Backend antwortet nicht nach 30 Sekunden.
    echo           Pruefe: docker compose logs backend
    goto start_frontend
)
curl -s http://localhost:8000/api/health >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_docker
)
echo       OK - Backend ist bereit.
echo.
goto start_frontend

:: ============================================
:: ENTWICKLUNGSMODUS (SQLite, kein Docker)
:: ============================================
:start_dev
echo   Modus: Entwicklung (SQLite, kein Docker)
echo.

:: Backend starten
echo [1/4] Backend starten (Port 8000, SQLite)...
cd backend
if not exist "venv" (
    echo       Virtuelle Umgebung wird erstellt...
    python -m venv venv
)
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)
if not exist "venv\Lib\site-packages\fastapi" (
    echo       Abhaengigkeiten werden installiert...
    pip install -r requirements.txt >nul 2>&1
)
start "Mitarbeiterverwaltung Backend" cmd /c "venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"
cd ..
echo       OK - Backend wird gestartet.
echo.

:: Warten bis Backend bereit ist
echo [2/4] Warte auf Backend (Port 8000)...
set /a count=0
:wait_dev
set /a count+=1
if %count% gtr 30 (
    echo [WARNUNG] Backend antwortet nicht nach 30 Sekunden.
    goto start_frontend
)
curl -s http://localhost:8000/api/health >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_dev
)
echo       OK - Backend ist bereit.
echo.
goto start_frontend

:: ============================================
:: FRONTEND (beide Modi)
:: ============================================
:start_frontend
echo [3/4] Frontend starten (Port 3000)...
cd frontend
if not exist "node_modules" (
    echo       npm install laeuft...
    call npm install >nul 2>&1
)
start "Mitarbeiterverwaltung Frontend" cmd /c "npm run dev"
cd ..
echo       OK - Frontend wird gestartet.
echo.

:: ============================================
:: CLOUDFLARE TUNNEL
:: ============================================
echo [4/4] Cloudflare Tunnel starten (Backend Port 8000)...
if "%CLOUDFLARED%"=="" (
    echo [WARNUNG] cloudflared nicht gefunden.
    echo          Installieren: winget install Cloudflare.cloudflared
    echo          Tunnel wird uebersprungen.
    goto done
)

:: Tunnel starten und URL in Datei schreiben
start "Cloudflare Tunnel" cmd /c ""%CLOUDFLARED%" tunnel --url http://localhost:8000 2>&1 | tee tunnel.log"

:: Warten bis Tunnel-URL verfuegbar ist
echo       Warte auf Tunnel-URL...
set /a tcount=0
:wait_tunnel
set /a tcount+=1
if %tcount% gtr 20 (
    echo [WARNUNG] Tunnel-URL nicht gefunden nach 20 Sekunden.
    echo           Pruefe tunnel.log manuell.
    goto done
)
timeout /t 1 /nobreak >nul
findstr /C:"trycloudflare.com" tunnel.log >nul 2>&1
if errorlevel 1 goto wait_tunnel

:: URL extrahieren und anzeigen
for /f "tokens=*" %%u in ('findstr /R "https://.*trycloudflare.com" tunnel.log') do set "TUNNEL_LINE=%%u"
:: URL aus der Zeile extrahieren
for /f "tokens=1,2,3,4,5,6" %%a in ("%TUNNEL_LINE%") do (
    echo %%a | findstr "https://" >nul 2>&1 && set "TUNNEL_URL=%%a"
    echo %%b | findstr "https://" >nul 2>&1 && set "TUNNEL_URL=%%b"
    echo %%c | findstr "https://" >nul 2>&1 && set "TUNNEL_URL=%%c"
    echo %%d | findstr "https://" >nul 2>&1 && set "TUNNEL_URL=%%d"
    echo %%e | findstr "https://" >nul 2>&1 && set "TUNNEL_URL=%%e"
    echo %%f | findstr "https://" >nul 2>&1 && set "TUNNEL_URL=%%f"
)
echo       OK - Tunnel laeuft.
echo.
echo       Tunnel-URL: %TUNNEL_URL%
echo       Mobile App baseUrl: %TUNNEL_URL%/api/v1
echo.

:: URL in Datei speichern fuer Referenz
echo %TUNNEL_URL%> tunnel_url.txt

:done
echo ============================================
echo   Alle Dienste gestartet!
echo ============================================
echo.
echo   Web-Frontend:   http://localhost:3000
echo   Backend API:    http://localhost:8000/api/v1
echo   API-Docs:       http://localhost:8000/api/docs
if defined TUNNEL_URL (
echo.
echo   Tunnel-URL:     %TUNNEL_URL%
echo   Mobile App:     %TUNNEL_URL%/api/v1
) else (
echo.
echo   Mobile App:     baseUrl auf http://[SERVER-IP]:8000/api/v1 setzen
)
echo.
echo   Zum Beenden:    stop.bat ausfuehren
echo ============================================
