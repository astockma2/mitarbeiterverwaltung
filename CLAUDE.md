# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Sprache

Kommunikation auf Deutsch.

## Ueberblick

Mitarbeiterverwaltung fuer IKK Kliniken (~1.000 Mitarbeiter). Zeiterfassung, Schichtplanung, Chat.
Produktion: https://mva.c3po42.de (Hostinger VPS 187.77.84.94).

## Befehle

### Backend (Entwicklung)

```bash
cd backend
pip install -r requirements.txt          # Python 3.12 erforderlich
uvicorn app.main:app --reload --port 8000   # SQLite-Modus (Standard)
pytest tests/ --asyncio-mode=auto        # Alle Tests
pytest tests/test_employees.py --asyncio-mode=auto  # Einzelner Test
```

### Frontend (Entwicklung)

```bash
cd frontend
npm install
npm run dev       # Vite Dev-Server Port 3000, Proxy /api → localhost:8000
npm run build     # TypeScript-Check + Vite Build
npm run lint
```

### Mobile (Android)

```bash
cd mobile
/c/Users/andre/flutter/bin/flutter pub get
/c/Users/andre/flutter/bin/flutter build apk --release
# APK: build/app/outputs/flutter-apk/app-release.apk
```

### Produktion (VPS)

```bash
# Auf VPS unter /opt/mva:
cp .env.prod .env
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs backend
```

## Architektur

### Backend — FastAPI (async)

- Einstiegspunkt: `backend/app/main.py`
- Konfiguration: `backend/app/config.py` — pydantic-settings, laedt `.env`
- DB: SQLAlchemy 2.0 async. Entwicklung: SQLite (`db_use_sqlite=True`), Produktion: PostgreSQL 16
- DB-Session: `get_db()` Dependency mit auto-commit/rollback
- Tabellen werden beim Start via `create_tables()` erstellt (kein Alembic in Entwicklung)
- Seed: `app_env=development` → `seed.py` (Demo-Daten, Passwort "dev"), `app_env=production` → `seed_prod.py` (bcrypt-Hashes)
- API-Prefix: `/api/v1`, Docs: `/api/docs`, Health: `/api/health`

**Auth-Flow:**
- Passwort-Verifikation via `bcrypt` direkt (nicht passlib)
- JWT: Access-Token 15min, Refresh-Token 7 Tage
- RBAC: ADMIN > HR > DEPARTMENT_MANAGER/TEAM_LEADER > EMPLOYEE
- AD optional (`ad_enabled`), in Produktion deaktiviert

**Router:** auth, employees, departments, admin, time_tracking, absences, shifts, monthly_closing, chat, reports

**Modelle:** Employee (mit password_hash), Department (Hierarchie via parent_id), TimeEntry, Surcharge, Absence, MonthlyClosing, ShiftTemplate/ShiftPlan/ShiftAssignment, Conversation/Message, Qualification, AuditLog

### Frontend — React 19 + TypeScript + Vite

- API-Client: `src/services/api.ts` — axios, JWT-Interceptor, auto-Logout bei 401
- Auth-Hook: `src/hooks/useAuth.ts`
- Produktion: Nginx-Container, SPA-Routing, Proxy `/api/` → backend:8000

### Mobile — Flutter 3 (nur Android)

- API-URL: `lib/services/api_service.dart` (Default: `https://mva.c3po42.de/api/v1`)
- Auth: `lib/services/auth_provider.dart` — Provider-Pattern, Biometrie-Login (local_auth)
- Token-Storage: FlutterSecureStorage (verschluesselt)
- Biometrie: Nach erstem Login werden Credentials gespeichert, danach Fingerabdruck-Login moeglich

### KI-Support-Bot (Chat)

- Bot-User: BOT001 "MVA Support", wird via `seed_prod.py` beim Start angelegt
- LLM: Claude Code CLI (`claude --print -p "..."`) — nutzt Claude Max Abo, keine API-Kosten
- Service: `backend/app/services/support_bot.py` — ruft `claude` als Subprocess auf
- Wissensquelle: `docs/benutzerhandbuch.md` wird als System-Prompt mitgesendet
- Bot-Erkennung: `chat.py` prueft ob Empfaenger BOT001 ist, triggert async Antwort
- Im Docker-Container: Claude CLI + Node.js + Credentials werden per Volume vom Host gemountet

### Docker Compose (Produktion)

`docker-compose.prod.yml`: PostgreSQL 16, Redis 7, Backend (1 Uvicorn-Worker), Frontend (Nginx auf Port 8090).
Nginx auf dem Host leitet mva.c3po42.de → Port 8090 (SSL via Certbot).
Backend-Container hat `TZ=Europe/Berlin` und Volume-Mounts fuer `docs/`, Claude CLI und Credentials.

### Deployment

Dateien auf dem VPS liegen unter `/opt/mva/` (kein Git-Repo). Das Git-Repo der Agenten liegt unter `/opt/agents/Mitarbeiterverwaltung/`. Deployment-Ablauf:
1. `git push origin master`
2. VPS: `cd /opt/agents/Mitarbeiterverwaltung && git fetch origin master && git reset --hard origin/master`
3. VPS: `cp -r .../backend/app/ /opt/mva/backend/app/` (und requirements.txt, frontend/src etc.)
4. VPS: `cd /opt/mva && docker compose -f docker-compose.prod.yml build --no-cache backend && docker compose -f docker-compose.prod.yml up -d backend`

SSH: `root@187.77.84.94` (paramiko von Windows, da kein SSH-Key vorhanden).

### Autonome Agenten (VPS)

3 Claude Code Agenten laufen als Prozesse unter `/opt/agents/scripts/`:
- **Entwickler** (`entwickler.sh`): Nimmt Issues mit Label `agent:entwickler`, erstellt PRs
- **QA** (`qa.sh`): Reviewt PRs mit Label `agent-pr`, bearbeitet Issues mit `agent:qa`
- **Docs** (`docs.sh`): Bearbeitet Issues mit Label `agent:docs`

Workflow: Issue erstellen mit Label → Agent nimmt auf (alle 5 Min) → PR erstellt → QA reviewt → Mensch merged

## Sensible Dateien (nicht in Git)

- `.env.prod` — DB-Passwort, JWT-Secret
- `passwords.txt` — Klartext-Passwoerter der Produktions-Benutzer
