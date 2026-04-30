# MVA - Mitarbeiterverwaltung fuer Kliniken

MVA ist ein HR- und Kommunikationssystem fuer Kliniken mit Personalverwaltung,
Zeiterfassung, Jahres-Dienstplanung, Schichtplanung, Abwesenheiten, Berichten,
Tickets und einem integrierten Support-Bot.

- Produktion: `https://mva.c3po42.de`
- Status: produktiv im Einsatz
- Stack: FastAPI, PostgreSQL, Redis, React 19, Flutter

## Versionstabelle

| Version | Datum | Inhalt |
|---------|-------|--------|
| `1.5.3` | 30.04.2026 | Dienstplanung per Klick/gedrueckter Maustaste, Plus-Dienstcodes, Abwesenheitskartei im Bereich Abwesenheiten, neues APK |
| `1.5.2` | 30.04.2026 | Dienstplanung und Support-Bot gehaertet |
| `1.5.1` | 26.04.2026 | Jahres-Dienstplan mit IT-Team-Beispieldaten 2026 |

## Aktuell

- Jahres-Dienstplanung unter `/shift-plans` mit farbigen Tagescodes, Klick-/Drag-Planung und CSV-Export
- Dienste werden per Klick oder bei gedrueckter linker Maustaste eingetragen; Mouseover allein schreibt nichts
- Kartei Abwesenheiten und Dienstreise-Antraege liegen im Bereich `/absences`
- Serverseitige Speicherung ueber `/api/v1/shifts/duty-plan`
- Bisherige Monatsplanung weiter unter `/shift-plans/monthly`

## Schnellstart

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Tests:

```bash
cd backend
pytest tests/ --asyncio-mode=auto
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Mobile

```bash
cd mobile
/c/Users/andre/flutter/bin/flutter pub get
/c/Users/andre/flutter/bin/flutter build apk --release
```

## Projektstruktur

```text
Mitarbeiterverwaltung/
|-- backend/                  FastAPI Backend
|   |-- app/
|   |   |-- api/             Router und Request-Schemas
|   |   |-- auth/            JWT, Rechte, Rate-Limit
|   |   |-- models/          SQLAlchemy Modelle
|   |   |-- services/        Seed, Push, Support-Bot
|   |   |-- config.py
|   |   `-- main.py
|   |-- alembic/
|   |-- requirements.txt
|   `-- Dockerfile
|-- frontend/                React 19 + TypeScript + Vite
|   |-- public/
|   |-- src/
|   |   |-- components/
|   |   |-- hooks/
|   |   |-- pages/
|   |   `-- services/
|   |-- Dockerfile
|   `-- nginx.conf
|-- mobile/                  Flutter App
|-- docs/                    Betriebs- und Produktdoku
|-- static/                  Produktseite
|-- tests/                   E2E-Artefakte und Tester-Helfer
|-- docker-compose.yml
|-- docker-compose.prod.yml
|-- deploy.py
|-- deploy_downloads.py
|-- deploy_tester.py
|-- deploy_website.py
`-- CLAUDE.md
```

## Architektur

### Gesamtbild

- Host-Nginx terminiert SSL und leitet `mva.c3po42.de` intern auf
  `127.0.0.1:8090`.
- Das Frontend laeuft als Nginx-Container und proxyt `/api/` an den
  Backend-Container.
- Das Backend spricht mit PostgreSQL 16 und Redis 7.
- Die Mobile-App nutzt die gleiche REST-API unter `/api/v1`.

### Backend

- Einstiegspunkt: `backend/app/main.py`
- Konfiguration: `backend/app/config.py`
- API-Prefix: `/api/v1`
- Health: `/api/health`
- App-Version: `/api/v1/app/version`
- Datenbank: SQLAlchemy 2 async
- Entwicklung: SQLite ueber `db_use_sqlite=True`
- Produktion: PostgreSQL ueber `.env`

Wichtige Router:

- `auth`
- `employees`
- `departments`
- `admin`
- `time_tracking`
- `absences`
- `shifts`
- `monthly_closing`
- `chat`
- `reports`
- `tickets`

Wichtige Auth-Regeln:

- JWT mit Access-Token und Refresh-Token
- In Produktion ist AD standardmaessig deaktiviert
- Produktions-Login laeuft ueber `ad_username + bcrypt password_hash`
- Development-Login nutzt Demo-Daten aus `seed.py`

### Frontend

- Einstiegspunkt: `frontend/src/App.tsx`
- API-Client: `frontend/src/services/api.ts`
- Auth-Hook: `frontend/src/hooks/useAuth.ts`
- Build: Vite
- Produktion: Nginx-Container mit SPA-Routing und API-Proxy

### Mobile

- Flutter 3
- Default-API: `https://mva.c3po42.de/api/v1`
- Token-Storage: `FlutterSecureStorage`
- Biometrie-Login ueber `local_auth`

### Support-Bot

- Bot-User: `BOT001`
- Seed: `backend/app/services/seed_prod.py`
- Service: `backend/app/services/support_bot.py`
- Wissensquelle: Markdown-Doku aus `docs/`
- Laufzeit in Produktion ueber die lokal eingebundene Claude-CLI

## Lokale Entwicklung

### Docker Compose

```bash
cp .env.example .env
docker compose up -d
```

### Ohne Docker

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Deployment

### VPS-Aufteilung

- Laufzeitverzeichnis: `/opt/mva`
- Git-Checkout fuer Deploys: `/opt/agents/Mitarbeiterverwaltung`

### Produktions-Compose

`docker-compose.prod.yml` startet:

- `db`
- `redis`
- `backend`
- `frontend`

Wichtige Produktionsdetails:

- Frontend-Bindung bleibt auf `127.0.0.1:8090:80`
- Backend mountet `docs/` und `static/`
- Host-Nginx zeigt nach `127.0.0.1:8090`

### Deploy-Workflow

Empfohlen:

```bash
python deploy.py
```

Das Deploy-Skript:

1. prueft den lokalen Git-Status
2. pusht `origin/master`
3. zieht den Stand auf `/opt/agents/Mitarbeiterverwaltung`
4. synchronisiert die benoetigten Projektteile nach `/opt/mva`
5. baut Backend und Frontend neu
6. startet die Container neu und prueft Healthchecks

Wichtig:

- Keine manuellen `cp -r` Deploys fuer `backend/app`, `frontend/src` oder
  `frontend/public` verwenden.
- Alte naive Kopiervorgaenge erzeugen sonst verschachtelte Verzeichnisse wie
  `app/app` oder `src/src`.

## Tests und Betrieb

### Backend-Tests

```bash
cd backend
pytest tests/ --asyncio-mode=auto
```

### Frontend-Build

```bash
cd frontend
npm run build
```

### Wichtige Betriebschecks

```bash
curl http://127.0.0.1:8090/api/health
curl http://127.0.0.1:8090/api/v1/app/version
docker compose -f /opt/mva/docker-compose.prod.yml ps
```

## Agenten und Automatisierung

Auf dem VPS laufen mehrere Agenten unter `/opt/agents/scripts/`.

- `entwickler.sh`
- `qa.sh`
- `docs.sh`

Typischer Ablauf:

1. Issue mit Agent-Label erstellen
2. Agent bearbeitet das Issue
3. PR wird erstellt
4. QA prueft
5. Mensch merged

## Sensible Dateien

Nicht einchecken:

- `.env`
- `.env.prod`
- `passwords.txt`

Sensible Werte bleiben lokal oder auf dem VPS und gehoeren nicht in Git.

## Weitere Doku

- `CLAUDE.md` fuer den knappen Agent-Einstieg
- `architektur.md` fuer ausfuehrlichere Architektur
- `anforderungen.md` fuer fachliche Anforderungen
- `BENUTZERHANDBUCH.md` fuer Anwenderdoku
