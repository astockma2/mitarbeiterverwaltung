#!/bin/bash
set -e

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║     Mitarbeiterverwaltung IKK Kliniken - Installer      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

INSTALL_DIR="/opt/mitarbeiterverwaltung"
REPO="astockma2/Mitarbeiterverwaltung"

# 1. Voraussetzungen prüfen
echo -e "${YELLOW}[1/7] Pruefe Voraussetzungen...${NC}"

check_cmd() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}✗ $1 nicht gefunden. Bitte installieren: $2${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ $1 gefunden${NC}"
}

check_cmd docker "https://docs.docker.com/engine/install/"
check_cmd "docker compose" "Docker Compose V2 wird benoetigt"
check_cmd curl "apt install curl / yum install curl"
check_cmd openssl "apt install openssl / yum install openssl"

# Docker Daemon prüfen
if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker Daemon laeuft nicht. Bitte starten: sudo systemctl start docker${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Daemon laeuft${NC}"

# 2. Verzeichnis erstellen
echo ""
echo -e "${YELLOW}[2/7] Erstelle Installationsverzeichnis...${NC}"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠ $INSTALL_DIR existiert bereits.${NC}"
    read -p "Ueberschreiben? (j/N): " OVERWRITE
    if [[ "$OVERWRITE" != "j" && "$OVERWRITE" != "J" ]]; then
        echo "Abgebrochen."
        exit 0
    fi
    rm -rf "$INSTALL_DIR"
fi

sudo mkdir -p "$INSTALL_DIR"
sudo chown $(whoami):$(whoami) "$INSTALL_DIR"
echo -e "${GREEN}✓ $INSTALL_DIR erstellt${NC}"

# 3. Release herunterladen
echo ""
echo -e "${YELLOW}[3/7] Lade neuestes Release herunter...${NC}"

RELEASE_URL=$(curl -s "https://api.github.com/repos/${REPO}/releases/latest" | grep "browser_download_url.*tar.gz" | head -1 | cut -d '"' -f 4)

if [ -z "$RELEASE_URL" ]; then
    echo -e "${RED}✗ Kein Release gefunden. Pruefe https://github.com/${REPO}/releases${NC}"
    exit 1
fi

echo "URL: $RELEASE_URL"
curl -L -o /tmp/mitarbeiterverwaltung.tar.gz "$RELEASE_URL"
tar xzf /tmp/mitarbeiterverwaltung.tar.gz -C "$INSTALL_DIR" --strip-components=1
rm /tmp/mitarbeiterverwaltung.tar.gz
echo -e "${GREEN}✓ Release entpackt nach $INSTALL_DIR${NC}"

# 4. Konfiguration
echo ""
echo -e "${YELLOW}[4/7] Konfiguration...${NC}"

cd "$INSTALL_DIR"

# .env erstellen
if [ -f .env.example ]; then
    cp .env.example .env
fi

# Sichere Passwoerter generieren
DB_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)
JWT_SECRET=$(openssl rand -base64 48 | tr -d '/+=' | head -c 64)
REDIS_PASSWORD=$(openssl rand -base64 16 | tr -d '/+=' | head -c 24)

# Interaktive Konfiguration
echo ""
echo -e "${BLUE}Bitte folgende Angaben machen:${NC}"
echo ""

read -p "Server-Hostname (z.B. mitarbeiter.klinik.local): " SERVER_HOST
SERVER_HOST=${SERVER_HOST:-localhost}

read -p "Active Directory aktivieren? (j/N): " AD_ENABLED
if [[ "$AD_ENABLED" == "j" || "$AD_ENABLED" == "J" ]]; then
    AD_ENABLED="true"
    read -p "AD-Server (z.B. ldap://dc01.klinik.local): " AD_SERVER
    read -p "AD-Basis-DN (z.B. DC=klinik,DC=local): " AD_BASE_DN
    read -p "AD-Bind-Benutzer (z.B. CN=svc_app,OU=Service,DC=klinik,DC=local): " AD_BIND_DN
    read -sp "AD-Bind-Passwort: " AD_BIND_PW
    echo ""
else
    AD_ENABLED="false"
    AD_SERVER=""
    AD_BASE_DN=""
    AD_BIND_DN=""
    AD_BIND_PW=""
fi

# .env schreiben
cat > .env << ENVEOF
# === Datenbank ===
DB_USE_SQLITE=false
DB_HOST=db
DB_PORT=5432
DB_NAME=mitarbeiterverwaltung
DB_USER=postgres
DB_PASSWORD=${DB_PASSWORD}

# === Redis ===
REDIS_URL=redis://redis:6379/0

# === JWT ===
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# === Active Directory ===
AD_ENABLED=${AD_ENABLED}
AD_SERVER=${AD_SERVER}
AD_BASE_DN=${AD_BASE_DN}
AD_BIND_DN=${AD_BIND_DN}
AD_BIND_PASSWORD=${AD_BIND_PW}

# === App ===
APP_ENV=production
APP_DEBUG=false
CORS_ORIGINS=https://${SERVER_HOST}
SERVER_HOST=${SERVER_HOST}
ENVEOF

echo -e "${GREEN}✓ Konfiguration gespeichert${NC}"

# 5. TLS-Zertifikat
echo ""
echo -e "${YELLOW}[5/7] TLS-Zertifikat...${NC}"

read -p "Self-signed Zertifikat erstellen? (J/n): " CREATE_CERT
if [[ "$CREATE_CERT" != "n" && "$CREATE_CERT" != "N" ]]; then
    mkdir -p certs
    openssl req -x509 -nodes -days 365 \
        -newkey rsa:2048 \
        -keyout certs/server.key \
        -out certs/server.crt \
        -subj "/CN=${SERVER_HOST}/O=IKK Kliniken/C=DE" \
        2>/dev/null
    echo -e "${GREEN}✓ Self-signed Zertifikat erstellt (1 Jahr gueltig)${NC}"
    echo -e "${YELLOW}  Fuer Produktion: Ersetze certs/server.crt und certs/server.key mit echtem Zertifikat${NC}"
else
    echo -e "${YELLOW}⚠ Kein Zertifikat erstellt. Bitte manuell unter certs/ ablegen.${NC}"
fi

# 6. Docker Build & Start
echo ""
echo -e "${YELLOW}[6/7] Baue und starte Container...${NC}"

docker compose build --quiet
docker compose up -d

echo -e "${GREEN}✓ Container gestartet${NC}"

# 7. Health-Check
echo ""
echo -e "${YELLOW}[7/7] Warte auf Health-Check...${NC}"

for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend ist bereit!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Backend antwortet nicht. Pruefe: docker compose logs backend${NC}"
        exit 1
    fi
    sleep 2
done

# Fertig
echo ""
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              Installation abgeschlossen!                ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                         ║"
echo "║  Web-App:  https://${SERVER_HOST}                        "
echo "║  API-Docs: https://${SERVER_HOST}/api/docs               "
echo "║                                                         ║"
echo "║  Standard-Login (Dev-Modus):                            ║"
echo "║    Benutzer: admin  |  Passwort: dev                    ║"
echo "║                                                         ║"
echo "║  Verzeichnis: ${INSTALL_DIR}                             "
echo "║                                                         ║"
echo "║  Befehle:                                               ║"
echo "║    cd ${INSTALL_DIR}                                     "
echo "║    docker compose logs -f    # Logs anzeigen            ║"
echo "║    docker compose restart    # Neustart                 ║"
echo "║    docker compose down       # Stoppen                  ║"
echo "║                                                         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
