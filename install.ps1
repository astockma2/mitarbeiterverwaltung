#Requires -RunAsAdministrator
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Blue
Write-Host "  Mitarbeiterverwaltung IKK Kliniken - Installer" -ForegroundColor Blue
Write-Host "========================================================" -ForegroundColor Blue
Write-Host ""

$InstallDir = 'C:\Mitarbeiterverwaltung'
$Repo = 'astockma2/Mitarbeiterverwaltung'

# 1. Voraussetzungen
Write-Host '[1/7] Pruefe Voraussetzungen...' -ForegroundColor Yellow

function Test-Command {
    param([string]$cmd, [string]$hint)
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        Write-Host "  OK $cmd gefunden" -ForegroundColor Green
    } else {
        Write-Host "  FEHLER $cmd nicht gefunden. $hint" -ForegroundColor Red
        exit 1
    }
}

Test-Command 'docker' 'Bitte Docker Desktop installieren: https://docs.docker.com/desktop/install/windows/'
Test-Command 'curl' 'curl sollte in Windows 10+ enthalten sein'

# Docker Daemon pruefen
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'Docker nicht bereit' }
    Write-Host '  OK Docker laeuft' -ForegroundColor Green
} catch {
    Write-Host '  FEHLER Docker Desktop laeuft nicht. Bitte starten.' -ForegroundColor Red
    exit 1
}

# Docker Compose pruefen
try {
    $null = docker compose version 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'kein compose' }
    Write-Host '  OK Docker Compose gefunden' -ForegroundColor Green
} catch {
    Write-Host '  FEHLER Docker Compose nicht gefunden.' -ForegroundColor Red
    exit 1
}

# 2. Verzeichnis
Write-Host ''
Write-Host '[2/7] Erstelle Installationsverzeichnis...' -ForegroundColor Yellow

if (Test-Path $InstallDir) {
    $overwrite = Read-Host "  $InstallDir existiert bereits. Ueberschreiben? j/N"
    if ($overwrite -ne 'j') { Write-Host 'Abgebrochen.'; exit 0 }
    Remove-Item -Recurse -Force $InstallDir
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Write-Host "  OK $InstallDir erstellt" -ForegroundColor Green

# 3. Download
Write-Host ''
Write-Host '[3/7] Lade neuestes Release herunter...' -ForegroundColor Yellow

$releaseUrl = "https://api.github.com/repos/$Repo/releases/latest"
$release = Invoke-RestMethod $releaseUrl
$asset = $release.assets | Where-Object { $_.name -like '*.zip' } | Select-Object -First 1

if (-not $asset) {
    Write-Host '  FEHLER Kein Release gefunden.' -ForegroundColor Red
    exit 1
}

$downloadUrl = $asset.browser_download_url
Write-Host "  URL: $downloadUrl"

$zipPath = Join-Path $env:TEMP 'mitarbeiterverwaltung.zip'
Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath
Expand-Archive -Path $zipPath -DestinationPath $InstallDir -Force
Remove-Item $zipPath

# Falls in Unterordner entpackt, eine Ebene hoch verschieben
$subDirs = Get-ChildItem $InstallDir -Directory
if ($subDirs.Count -eq 1) {
    Get-ChildItem $subDirs[0].FullName | Move-Item -Destination $InstallDir -Force
    Remove-Item $subDirs[0].FullName -Recurse -Force
}

Write-Host '  OK Release entpackt' -ForegroundColor Green

# 4. Konfiguration
Write-Host ''
Write-Host '[4/7] Konfiguration...' -ForegroundColor Yellow

Set-Location $InstallDir

# Passwoerter generieren
Add-Type -AssemblyName System.Security
$bytes32 = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes32)
$DbPassword = [Convert]::ToBase64String($bytes32).Substring(0, 32)

$bytes48 = New-Object byte[] 48
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes48)
$JwtSecret = [Convert]::ToBase64String($bytes48).Substring(0, 64)

Write-Host ''
Write-Host 'Bitte folgende Angaben machen:' -ForegroundColor Blue
Write-Host ''

$ServerHost = Read-Host '  Server-Hostname, z.B. mitarbeiter.klinik.local [localhost]'
if (-not $ServerHost) { $ServerHost = 'localhost' }

$adChoice = Read-Host '  Active Directory aktivieren? j/N'
$AdEnabled = 'false'
$AdServer = ''
$AdBaseDn = ''
$AdBindDn = ''
$AdBindPw = ''

if ($adChoice -eq 'j') {
    $AdEnabled = 'true'
    $AdServer = Read-Host '  AD-Server, z.B. ldap://dc01.klinik.local'
    $AdBaseDn = Read-Host '  AD-Basis-DN, z.B. DC=klinik,DC=local'
    $AdBindDn = Read-Host '  AD-Bind-Benutzer'
    $AdBindPwSecure = Read-Host '  AD-Bind-Passwort' -AsSecureString
    $AdBindPw = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($AdBindPwSecure))
}

$envLines = @(
    "DB_USE_SQLITE=false",
    "DB_HOST=db",
    "DB_PORT=5432",
    "DB_NAME=mitarbeiterverwaltung",
    "DB_USER=postgres",
    "DB_PASSWORD=$DbPassword",
    "",
    "REDIS_URL=redis://redis:6379/0",
    "",
    "JWT_SECRET_KEY=$JwtSecret",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15",
    "JWT_REFRESH_TOKEN_EXPIRE_DAYS=7",
    "",
    "AD_ENABLED=$AdEnabled",
    "AD_SERVER=$AdServer",
    "AD_BASE_DN=$AdBaseDn",
    "AD_BIND_DN=$AdBindDn",
    "AD_BIND_PASSWORD=$AdBindPw",
    "",
    "APP_ENV=production",
    "APP_DEBUG=false",
    "CORS_ORIGINS=https://$ServerHost",
    "SERVER_HOST=$ServerHost"
)
$envContent = $envLines -join "`r`n"
[System.IO.File]::WriteAllText((Join-Path $InstallDir '.env'), $envContent)
Write-Host '  OK Konfiguration gespeichert' -ForegroundColor Green

# 5. TLS
Write-Host ''
Write-Host '[5/7] TLS-Zertifikat...' -ForegroundColor Yellow

$createCert = Read-Host '  Self-signed Zertifikat erstellen? J/n'
if ($createCert -ne 'n') {
    New-Item -ItemType Directory -Path 'certs' -Force | Out-Null

    if (Get-Command openssl -ErrorAction SilentlyContinue) {
        $subj = "/CN=$ServerHost/O=IKK Kliniken/C=DE"
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout certs\server.key -out certs\server.crt -subj $subj 2>$null
    } else {
        $cert = New-SelfSignedCertificate -DnsName $ServerHost -CertStoreLocation 'Cert:\LocalMachine\My' -NotAfter (Get-Date).AddYears(1)
        $pfxPw = ConvertTo-SecureString -String 'temp' -Force -AsPlainText
        Export-PfxCertificate -Cert $cert -FilePath 'certs\server.pfx' -Password $pfxPw | Out-Null
        Write-Host '  Hinweis: PFX-Zertifikat erstellt unter certs\server.pfx' -ForegroundColor Yellow
    }
    Write-Host '  OK Zertifikat erstellt' -ForegroundColor Green
}

# 6. Docker Build und Start
Write-Host ''
Write-Host '[6/7] Baue und starte Container...' -ForegroundColor Yellow

docker compose build --quiet
docker compose up -d

Write-Host '  OK Container gestartet' -ForegroundColor Green

# 7. Health-Check
Write-Host ''
Write-Host '[7/7] Warte auf Health-Check...' -ForegroundColor Yellow

for ($i = 1; $i -le 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri 'http://localhost:8000/api/health' -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host '  OK Backend ist bereit!' -ForegroundColor Green
            break
        }
    } catch {}
    if ($i -eq 30) {
        Write-Host '  FEHLER Backend antwortet nicht. Pruefe: docker compose logs backend' -ForegroundColor Red
        exit 1
    }
    Start-Sleep -Seconds 2
}

Write-Host ''
Write-Host '========================================================' -ForegroundColor Green
Write-Host '  Installation abgeschlossen!' -ForegroundColor Green
Write-Host '========================================================' -ForegroundColor Green
Write-Host ''
Write-Host "  Web-App:  https://$ServerHost" -ForegroundColor Green
Write-Host "  API-Docs: https://$ServerHost/api/docs" -ForegroundColor Green
Write-Host '' -ForegroundColor Green
Write-Host '  Standard-Login:' -ForegroundColor Green
Write-Host '    Benutzer: admin  |  Passwort: dev' -ForegroundColor Green
Write-Host '' -ForegroundColor Green
Write-Host "  Verzeichnis: $InstallDir" -ForegroundColor Green
Write-Host '' -ForegroundColor Green
Write-Host '  Befehle:' -ForegroundColor Green
Write-Host "    cd $InstallDir" -ForegroundColor Green
Write-Host '    docker compose logs -f    # Logs' -ForegroundColor Green
Write-Host '    docker compose restart    # Neustart' -ForegroundColor Green
Write-Host '    docker compose down       # Stoppen' -ForegroundColor Green
Write-Host '========================================================' -ForegroundColor Green
Write-Host ''
