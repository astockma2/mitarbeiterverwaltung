---
name: Architekturplan Mitarbeiterverwaltung
description: Technische Architektur, Tech-Stack, Datenbankmodell und Projektstruktur
type: architecture
---

# Architekturplan — Mitarbeiterverwaltung IKK Kliniken

## 1. Systemuebersicht

```
┌─────────────────────────────────────────────────────────┐
│                    ON-PREMISE SERVER                      │
│                                                          │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Reverse  │  │   FastAPI     │  │   PostgreSQL      │  │
│  │ Proxy    │──│   Backend     │──│   Datenbank       │  │
│  │ (nginx)  │  │   + WebSocket │  │                   │  │
│  └──────────┘  └──────────────┘  └───────────────────┘  │
│       │              │                                    │
│       │         ┌────┴─────┐                             │
│       │         │  Redis   │  (Cache, WebSocket-Broker,  │
│       │         │          │   Session-Store)             │
│       │         └──────────┘                             │
│       │              │                                    │
│  ┌────┴─────────────┴──────────────────┐                 │
│  │         Internes Netzwerk            │                 │
│  │  ┌─────────┐  ┌──────────────────┐  │                 │
│  │  │ Active  │  │  Loga Server     │  │                 │
│  │  │Directory│  │  (CSV/XML Export) │  │                 │
│  │  └─────────┘  └──────────────────┘  │                 │
│  └──────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────┘
        │                    │
   ┌────┴────┐         ┌────┴────┐
   │ Web     │         │ Mobile  │
   │ Admin   │         │ App     │
   │ (React) │         │(Flutter)│
   └─────────┘         └─────────┘
```

## 2. Tech-Stack

| Schicht | Technologie | Begruendung |
|---|---|---|
| **Backend** | Python 3.12 + FastAPI | Schnelle API-Entwicklung, async, gute Doku, Python-Know-how vorhanden |
| **Datenbank** | PostgreSQL 16 | Robust, kostenlos, JSON-Support, bewährt im Enterprise-Bereich |
| **Cache / Broker** | Redis 7 | WebSocket-Scaling, Session-Cache, Hintergrund-Jobs |
| **Task Queue** | Celery + Redis | Zeitgesteuerter Loga-Export, AD-Sync, Benachrichtigungen |
| **Web-Frontend** | React 18 + TypeScript | Admin-Oberflaeche, Dienstplanung, Auswertungen |
| **Mobile App** | Flutter 3 (Dart) | Eine Codebase fuer iOS + Android, gute Performance |
| **Echtzeit-Chat** | WebSockets (FastAPI) | Direkt im Backend, kein separater Service noetig |
| **Push-Nachrichten** | Firebase Cloud Messaging | Zuverlaessig fuer iOS + Android, kostenlos |
| **Reverse Proxy** | nginx | SSL-Terminierung, Rate-Limiting, statische Dateien |
| **Auth** | LDAP/Kerberos (AD) + JWT | SSO gegen Active Directory, JWT fuer API/App |
| **Containerisierung** | Docker + Docker Compose | Einfaches Deployment und Updates on-premise |

## 3. Datenbankmodell (Kerntabellen)

### Mitarbeiter & Organisation

```
employees
├── id (PK)
├── personnel_number (unique)     -- Personalnummer
├── ad_username (unique)          -- Active Directory Login
├── first_name
├── last_name
├── email
├── phone
├── mobile
├── date_of_birth (nullable)
├── street (nullable)             -- Adresse
├── zip_code (nullable)
├── city (nullable)
├── department_id (FK)
├── role                          -- ADMIN, HR, DEPARTMENT_MANAGER, TEAM_LEADER, EMPLOYEE
├── job_title
├── employment_type              -- FULLTIME, PARTTIME, MINI, TRAINEE
├── weekly_hours                 -- Soll-Stunden/Woche
├── hire_date
├── exit_date (nullable)
├── vacation_days_per_year       -- Standard: 30
├── emergency_contact_name (nullable)
├── emergency_contact_phone (nullable)
├── is_active
├── created_at
└── updated_at

departments
├── id (PK)
├── name
├── parent_id (FK, self)         -- Hierarchie
├── cost_center                  -- Kostenstelle
└── manager_id (FK → employees)

qualifications
├── id (PK)
├── employee_id (FK)
├── name                         -- z.B. "Facharzt Innere Medizin"
├── valid_until (nullable)
└── document_path (nullable)
```

### Zeiterfassung

```
time_entries
├── id (PK)
├── employee_id (FK)
├── clock_in (timestamp)
├── clock_out (timestamp, nullable)
├── break_minutes
├── entry_type                   -- REGULAR, CORRECTION, MANUAL
├── status                       -- OPEN, APPROVED, LOCKED
├── approved_by (FK → employees, nullable)
├── net_hours (computed)
└── created_at

surcharges
├── id (PK)
├── time_entry_id (FK)
├── type                         -- NIGHT, SUNDAY, HOLIDAY
├── hours
└── rate_percent

absences
├── id (PK)
├── employee_id (FK)
├── type                         -- VACATION, SICK, TRAINING, SPECIAL
├── start_date
├── end_date
├── status                       -- REQUESTED, APPROVED, REJECTED
├── approved_by (FK → employees, nullable)
├── notes
└── created_at

monthly_closings
├── id (PK)
├── employee_id (FK)
├── year
├── month
├── total_hours
├── overtime_hours
├── status                       -- OPEN, CLOSED, EXPORTED
├── closed_by (FK → employees, nullable)
├── exported_at (nullable)
└── loga_export_file (nullable)
```

### Schichtplanung

```
shift_templates
├── id (PK)
├── name                         -- z.B. "Fruehdienst"
├── short_code                   -- z.B. "F"
├── start_time
├── end_time
├── break_minutes
├── color                        -- Fuer Kalenderanzeige
└── department_id (FK, nullable)

shift_assignments
├── id (PK)
├── employee_id (FK)
├── shift_template_id (FK)
├── date
├── status                       -- PLANNED, CONFIRMED, SWAPPED, CANCELLED
├── swap_requested_by (FK, nullable)
├── notes
└── created_at

shift_requirements
├── id (PK)
├── department_id (FK)
├── shift_template_id (FK)
├── weekday                      -- 0-6
├── min_staff
├── required_qualifications      -- JSONB Array
└── is_active

coverage_requests                -- Vertretungsanfragen
├── id (PK)
├── shift_assignment_id (FK)
├── reason
├── status                       -- OPEN, FILLED, CANCELLED
├── filled_by (FK → employees, nullable)
└── created_at
```

### Kommunikation

```
conversations
├── id (PK)
├── type                         -- DIRECT, GROUP, ANNOUNCEMENT
├── name (nullable)              -- Gruppenname
├── department_id (FK, nullable)
├── created_by (FK → employees)
└── created_at

conversation_members
├── conversation_id (FK)
├── employee_id (FK)
├── joined_at
├── last_read_at
└── is_muted

messages
├── id (PK)
├── conversation_id (FK)
├── sender_id (FK → employees)
├── content (text, verschluesselt)
├── message_type                 -- TEXT, IMAGE, FILE
├── file_path (nullable)
├── created_at
└── edited_at (nullable)
```

## 4. Projektstruktur

```
mitarbeiterverwaltung/
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                 -- DB-Migrationen
│   ├── app/
│   │   ├── main.py              -- FastAPI App, Router-Registrierung, Startup (DB-Init, Seed)
│   │   ├── config.py            -- Umgebungskonfiguration (DB, CORS, JWT-Secret)
│   │   ├── database.py          -- SQLAlchemy async Engine + Session
│   │   ├── auth/
│   │   │   ├── jwt.py           -- JWT-Token-Erzeugung/-Validierung, Dev-Login
│   │   │   └── permissions.py   -- Rollen-Checks (is_hr, is_manager, can_view_employee)
│   │   ├── models/              -- SQLAlchemy ORM Models
│   │   │   ├── employee.py      -- Employee, UserRole, EmploymentType
│   │   │   ├── department.py
│   │   │   ├── time_entry.py    -- TimeEntry, Surcharge
│   │   │   ├── absence.py
│   │   │   ├── shift.py         -- ShiftTemplate, ShiftPlan, ShiftAssignment, Requirements, Swap/Coverage
│   │   │   ├── monthly_closing.py
│   │   │   ├── qualification.py
│   │   │   ├── message.py       -- Conversation, ConversationMember, Message
│   │   │   └── audit_log.py
│   │   ├── api/                 -- API Router (alle unter /api/v1)
│   │   │   ├── auth.py          -- Login, Refresh, /me
│   │   │   ├── employees.py     -- CRUD + Qualifikationen, Self-Edit fuer eigene Kontaktdaten
│   │   │   ├── departments.py
│   │   │   ├── time_tracking.py -- Clock-In/Out, Tages-/Monatsuebersicht
│   │   │   ├── shifts.py        -- Templates, Plaene, Assign/Bulk-Assign, Publish, Swap, Coverage
│   │   │   ├── absences.py      -- CRUD, Genehmigung, Urlaubskonto
│   │   │   ├── chat.py          -- WebSocket + REST (Conversations, Messages, Online-Status)
│   │   │   ├── monthly.py       -- Monatsabschluss, Loga-CSV-Export
│   │   │   ├── reports.py       -- Jahres-, Abteilungs-, Zuschlagsuebersicht, Abwesenheitsstatistik
│   │   │   ├── admin.py         -- Dashboard-Statistiken
│   │   │   └── schemas.py       -- Pydantic Request/Response Schemas
│   │   └── services/            -- Business-Logik
│   │       ├── seed.py          -- Demo-Daten (7 Mitarbeiter, 10 Abteilungen, 6 Schichtvorlagen)
│   │       ├── surcharge.py     -- Zuschlagsberechnung (Nacht/Sonntag/Feiertag)
│   │       ├── shift_validator.py -- Arbeitszeitgesetz-Pruefung (11h Ruhezeit, Max-Stunden)
│   │       └── audit.py         -- Audit-Logging
│   └── tests/
│
├── frontend/                    -- React Admin-Panel (Vite + TypeScript)
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx              -- Routing, Auth-Guard, rollenbasierte Seitenfreigabe
│       ├── hooks/useAuth.ts     -- Auth-State (Login, Token, Rollen-Flags)
│       ├── services/api.ts      -- Axios-Client mit JWT-Interceptor, alle API-Funktionen
│       ├── components/
│       │   ├── Layout.tsx       -- Sidebar-Navigation, Header, Outlet
│       │   └── Card.tsx         -- Wiederverwendbare Card- und Badge-Komponenten
│       └── pages/
│           ├── Login.tsx
│           ├── Dashboard.tsx
│           ├── Employees.tsx        -- Mitarbeiterliste mit Suche/Filter/Paginierung
│           ├── EmployeeDetail.tsx   -- Detailansicht mit Bearbeitungsformular (Adresse, Beruf, etc.)
│           ├── Departments.tsx      -- Abteilungsliste mit Hierarchie
│           ├── TimeTracking.tsx     -- Kommen/Gehen, Tages-/Monatsuebersicht
│           ├── MySchedule.tsx       -- Eigener Dienstplan (Mitarbeiter-Ansicht)
│           ├── ShiftPlans.tsx       -- Dienstplanung mit Drag-to-Paint-Kalender
│           ├── Absences.tsx         -- Abwesenheiten, Urlaubsantraege, Genehmigungen
│           ├── Chat.tsx             -- Einzel-/Gruppenchat mit WebSocket
│           ├── MonthlyClosing.tsx   -- Monatsabschluss, Loga-CSV-Export
│           └── Reports.tsx          -- Berichte (Jahres-, Abteilungs-, Zuschlagsuebersicht)

│
├── mobile/                      -- Flutter App
│   ├── lib/
│   │   ├── main.dart
│   │   ├── screens/
│   │   │   ├── login/
│   │   │   ├── dashboard/
│   │   │   ├── shift_plan/
│   │   │   ├── time_clock/
│   │   │   ├── absences/
│   │   │   ├── chat/
│   │   │   └── profile/
│   │   ├── services/
│   │   ├── models/
│   │   └── widgets/
│   ├── android/
│   └── ios/
│
└── docs/
    ├── anforderungen.md
    ├── architektur.md
    └── api-spec.yaml
```

## 5. Deployment (On-Premise)

```yaml
# docker-compose.yml (vereinfacht)
services:
  db:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: mitarbeiterverwaltung
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  redis:
    image: redis:7-alpine

  backend:
    build: ./backend
    depends_on: [db, redis]
    environment:
      DATABASE_URL: postgresql://...
      REDIS_URL: redis://redis:6379
      AD_SERVER: ${AD_SERVER}
      AD_BASE_DN: ${AD_BASE_DN}

  celery:
    build: ./backend
    command: celery -A app.celery worker
    depends_on: [db, redis]

  frontend:
    build: ./frontend

  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
```

### Serveranforderungen

| Ressource | Minimum | Empfohlen |
|---|---|---|
| CPU | 4 Kerne | 8 Kerne |
| RAM | 16 GB | 32 GB |
| Storage | 100 GB SSD | 250 GB SSD |
| OS | Ubuntu 22.04 LTS oder RHEL 9 | |
| Netzwerk | Zugang zu AD, internes WLAN fuer App | |

## 6. Sicherheitskonzept

### 6.1 Uebersicht

| Bereich | Ist-Zustand | Bewertung |
|---|---|---|
| Authentifizierung | JWT + LDAP/AD | Grundlegend OK |
| Autorisierung (RBAC) | Rollenbasiert auf API-Ebene | Luecken vorhanden |
| Transportverschluesselung | TLS via nginx (Produktion) | OK |
| Token-Speicherung | localStorage (Web), flutter_secure_storage (Mobile) | Web: Risiko |
| CORS | `allow_origins=["*"]` im Code | **Kritisch** |
| Fehlerbehandlung | Exception-Detail wird an Client gesendet | **Hoch** |
| Rate-Limiting | Nicht implementiert | **Hoch** |
| Netzwerk | Nur internes Netz, kein Internet noetig (ausser FCM) | OK |
| Audit-Log | Alle Aenderungen an Stammdaten protokolliert | OK |

### 6.2 Sicherheitsanalyse — Ergebnisse

Die folgende Analyse wurde am 29.03.2026 gegen den aktuellen Codestand durchgefuehrt.

#### KRITISCH

**S-01: CORS komplett offen (`main.py:53`)**
```python
allow_origins=["*"]
```
- Die CORS-Config in `.env` (`cors_origins`) wird **ignoriert** — im Code steht `["*"]` statt `settings.cors_origins.split(",")`.
- Jede beliebige Website kann authentifizierte API-Anfragen stellen, wenn ein Benutzer eingeloggt ist.
- **Fix**: `allow_origins=settings.cors_origins.split(",")` und `allow_credentials=True` setzen.

**S-02: Exception-Details an Client (`main.py:78`)**
```python
return JSONResponse(status_code=500, content={"detail": str(exc)})
```
- Interne Fehlermeldungen (Stacktraces, DB-Queries, Dateipfade) werden direkt an den Client gesendet.
- Angreifer koennen so Datenbankstruktur, Dateipfade und interne Logik auslesen.
- **Fix**: In Produktion nur generische Fehlermeldung senden (`"Interner Serverfehler"`).

**S-03: Hardcoded Cloudflare-Tunnel-URL in Mobile App (`api_service.dart:13`)**
```dart
static String baseUrl = 'https://festivals-mentor-exchanges-pda.trycloudflare.com/api/v1';
```
- Eine oeffentlich erreichbare Cloudflare-Tunnel-URL ist fest im Quellcode hinterlegt.
- Die App sendet Credentials an diesen Endpunkt — jeder mit der URL hat potenziell Zugriff.
- **Fix**: URL konfigurierbar machen, Tunnel-URL aus Code entfernen.

#### HOCH

**S-04: JWT-Secret als Default-Wert (`config.py:18`)**
```python
jwt_secret_key: str = "dev-secret-key-CHANGE-IN-PRODUCTION"
```
- Wenn `.env` nicht gesetzt ist, wird ein bekannter Secret-Key verwendet.
- Angreifer koennen damit gueltige JWT-Tokens generieren.
- **Fix**: Kein Default-Wert, Anwendung muss beim Start ohne Secret abbrechen.

**S-05: Demo-Daten laufen immer beim Start (`main.py:35`)**
```python
await seed_demo_data()
```
- `seed_demo_data()` wird bei **jedem** Start ausgefuehrt, unabhaengig von `APP_ENV`.
- In Produktion mit leerer DB werden Demo-Benutzer mit bekannten Credentials angelegt.
- **Fix**: Nur ausfuehren wenn `settings.app_env == "development"`.

**S-06: Kein Rate-Limiting auf Login-Endpoint**
- Kein Schutz gegen Brute-Force-Angriffe auf `/api/v1/auth/login`.
- Im Dev-Modus ist das Passwort fuer alle Benutzer `dev`.
- **Fix**: Rate-Limiter (z.B. `slowapi`) auf Auth-Endpoints, Account-Lockout nach X Fehlversuchen.

**S-07: Admin-Dashboard gibt `{"error": ...}` statt HTTP 403 (`admin.py:22`)**
```python
if not is_hr(current_user):
    return {"error": "Keine Berechtigung"}
```
- Gibt Status 200 mit Fehlermeldung zurueck statt HTTP 403.
- Clients koennten dies als Erfolg werten. Gleicher Fehler bei `/admin/ad-sync`.
- **Fix**: `raise HTTPException(status_code=403, ...)` verwenden.

**S-08: WebSocket-Authentifizierung nur beim Connect (`chat.py:84-93`)**
- JWT-Token wird nur beim Verbindungsaufbau geprueft, nicht waehrend der Session.
- Ein abgelaufener/gesperrter Token bleibt aktiv bis der WebSocket getrennt wird.
- Keine Pruefung ob der Benutzer Mitglied der Konversation ist (im WebSocket-Handler).
- **Fix**: Token periodisch re-validieren, Konversationsmitgliedschaft pruefen.

**S-09: Kein Refresh-Token-Widerruf**
- Refresh-Tokens koennen nicht widerrufen werden (kein Token-Blacklisting).
- Ein gestohlener Refresh-Token ist 7 Tage gueltig und kann nicht invalidiert werden.
- Auch nach `is_active=False` bleibt ein bestehender Token bis zum naechsten DB-Check gueltig.
- **Fix**: Token-Blacklist in Redis, Widerruf bei Logout/Deaktivierung.

#### MITTEL

**S-10: Token in localStorage statt httpOnly-Cookie (Frontend `api.ts:9`)**
- `localStorage.getItem('access_token')` — anfaellig fuer XSS-Angriffe.
- Jedes Script auf der Seite kann den Token auslesen.
- **Mildernd**: Internes Netz, keine fremden Scripts. Aber: Chat-Nachrichten koennten als XSS-Vektor dienen.
- **Fix**: httpOnly-Cookie mit SameSite=Strict fuer Produktionsbetrieb.

**S-11: Abteilungspruefung bei Managern fehlt (`permissions.py:46-47`)**
```python
if viewer.role in (UserRole.DEPARTMENT_MANAGER, UserRole.TEAM_LEADER):
    return True  # Wird spaeter verfeinert mit Abteilungspruefung
```
- Department-Manager und Teamleiter koennen die Daten **aller** Mitarbeiter sehen, nicht nur ihrer Abteilung.
- **Fix**: `viewer.department_id == target_employee.department_id` pruefen.

**S-12: Keine Abteilungspruefung bei Korrekturen/Abwesenheiten**
- Manager koennen Korrekturen und Abwesenheiten aller Mitarbeiter genehmigen (`is_manager()` prueft nur die Rolle).
- Ein Teamleiter der Pflege koennte Urlaubsantraege der IT genehmigen.
- **Fix**: Abteilungszugehoerigkeit in Genehmigungspruefungen einbeziehen.

**S-13: Swagger-Docs in Produktion offen (`main.py:46-47`)**
- `/api/docs` und `/api/redoc` sind immer aktiv, auch in Produktion.
- Gibt die komplette API-Struktur, Schemas und Beispiele preis.
- **Fix**: In Produktion deaktivieren: `docs_url=None if settings.app_env == "production" else "/api/docs"`.

**S-14: Docker-Container laeuft als root (`Dockerfile`)**
- Kein `USER`-Statement im Dockerfile — der Prozess laeuft als root.
- Bei Container-Escape hat der Angreifer Root-Rechte.
- **Fix**: `RUN useradd -m appuser` + `USER appuser` im Dockerfile.

**S-15: PostgreSQL und Redis Ports nach aussen offen (`docker-compose.yml:13, 24`)**
```yaml
ports:
  - "5432:5432"
  - "6379:6379"
```
- DB und Redis sind direkt vom Hostnetzwerk erreichbar (nicht nur container-intern).
- **Fix**: Ports entfernen oder auf `127.0.0.1:5432:5432` binden. Fuer Produktion nur Backend exponieren.

**S-16: Android erlaubt Cleartext-Traffic (`AndroidManifest.xml:8`)**
```xml
android:usesCleartextTraffic="true"
```
- Die App erlaubt HTTP-Verbindungen (ohne TLS) — Credentials koennten mitgelesen werden.
- **Fix**: Fuer Produktion auf `false` setzen und Network-Security-Config mit Ausnahmen fuer Dev nutzen.

#### NIEDRIG

**S-17: Hardcoded API-URL im Frontend (`api.ts:3`)**
```typescript
const API_BASE = 'http://127.0.0.1:8000/api/v1';
```
- Wird in Produktion nicht funktionieren. Sollte ueber Vite-Umgebungsvariable konfiguriert werden.
- Der Vite-Proxy (`vite.config.ts`) leitet `/api` korrekt weiter, aber die axio-Instanz umgeht ihn.
- **Fix**: `const API_BASE = '/api/v1'` (nutzt den Vite-Proxy / nginx-Proxy).

**S-18: Debug-Logging in Produktion (`config.py:39`)**
```python
app_debug: bool = True
```
- Standard ist `True` — SQL-Queries und interne Details werden geloggt.
- **Fix**: Default auf `False` setzen, nur explizit in `.env` aktivieren.

**S-19: `echo=True` bei SQLAlchemy im Debug-Modus (`database.py:11`)**
- Alle SQL-Statements werden in die Logs geschrieben, potenziell mit sensiblen Daten.
- **Mildernd**: Nur wenn `app_debug=True`.

**S-20: Keine LDAP-Verbindungsverschluesselung (`config.py:26-27`)**
```python
ad_use_ssl: bool = False
ad_port: int = 389
```
- LDAP-Verbindung unverschluesselt (Port 389 statt 636).
- Passwoerter werden im Klartext ueber das Netzwerk gesendet.
- **Mildernd**: Internes Netzwerk. Aber Standard sollte LDAPS sein.
- **Fix**: Default auf `ad_use_ssl=True` und Port 636 aendern.

### 6.3 Zusammenfassung nach Schweregrad

| Schweregrad | Anzahl | Kritischste Punkte |
|---|---|---|
| **Kritisch** | 3 | CORS offen, Exception-Leak, Cloudflare-URL im Code |
| **Hoch** | 6 | JWT-Secret Default, Demo-Daten in Prod, kein Rate-Limiting |
| **Mittel** | 7 | Token in localStorage, fehlende Abteilungspruefung, Docker-Root |
| **Niedrig** | 4 | Hardcoded URLs, Debug-Defaults, LDAP ohne SSL |

### 6.4 Prioritaeten fuer Produktion (vor Rollout)

Folgende Punkte **muessen** vor dem produktiven Einsatz behoben werden:

- [ ] **S-01**: CORS auf konfigurierte Origins einschraenken
- [ ] **S-02**: Generische Fehlermeldung in Produktion
- [ ] **S-03**: Cloudflare-Tunnel-URL aus Mobile-Code entfernen
- [ ] **S-04**: JWT-Secret ohne Default, Pflichtfeld in `.env`
- [ ] **S-05**: Demo-Daten nur im Development-Modus
- [ ] **S-06**: Rate-Limiting auf Login-Endpoint
- [ ] **S-07**: HTTP 403 statt `{"error": ...}` im Admin-Router
- [ ] **S-09**: Token-Blacklist fuer Refresh-Tokens
- [ ] **S-14**: Docker-Container als non-root ausfuehren
- [ ] **S-15**: DB/Redis-Ports nicht nach aussen exponieren

### 6.5 Bestehende Sicherheitsmassnahmen (positiv)

Was bereits korrekt umgesetzt ist:

- **JWT-Token-Typ-Pruefung**: Access- und Refresh-Tokens werden unterschieden (`type: access/refresh`)
- **Benutzer-Deaktivierungs-Check**: `get_current_user()` prueft `is_active` bei jedem Request
- **LDAP-Injection-Schutz**: `_sanitize_ldap_input()` escaped gefaehrliche Zeichen
- **Soft-Delete**: Mitarbeiter werden deaktiviert, nicht geloescht
- **Audit-Log**: Alle relevanten Aktionen werden protokolliert (CREATE, UPDATE, DELETE, APPROVE)
- **Pydantic-Validierung**: Eingabedaten werden durch Pydantic-Schemas validiert
- **SQL-Injection-Schutz**: SQLAlchemy ORM mit parametrisierten Queries (kein Raw-SQL)
- **Konversationsmitgliedschaft**: Chat-REST-Endpoints pruefen Mitgliedschaft
- **Self-Edit-Einschraenkung**: Mitarbeiter koennen nur bestimmte eigene Felder aendern
- **Gesperrte Eintraege**: Monatsabschluss sperrt Zeiteintraege gegen Aenderungen
- **Flutter Secure Storage**: Mobile App nutzt plattformspezifische sichere Speicherung
- **Docker Health-Checks**: PostgreSQL und Redis werden vor Backend-Start geprueft

## 7. Active-Directory-Anbindung

### 7.1 Designentscheidung: AD ist Master

Active Directory ist die fuehrende Quelle fuer Identitaet, Authentifizierung und Rollenzuweisung. Die App speichert fachspezifische Daten (Arbeitszeit, Schichten, Qualifikationen), die im AD nicht existieren.

### 7.2 Datenhoheit — Wer ist Master?

| Bereich | Master | Begruendung |
|---|---|---|
| **Authentifizierung** | AD | Zentrale Passwortverwaltung, sofortige Sperrung bei Austritt |
| **Rollen / Berechtigungen** | AD (Gruppen) | IT steuert Zugriff zentral ueber AD-Gruppenmitgliedschaft |
| **Name, E-Mail** | AD | HR pflegt Stammdaten im AD / HR-System |
| **Abteilungszuordnung** | AD | `department`-Attribut aus AD |
| **Arbeitszeit, Schichten** | App | Fachspezifisch, existiert nicht im AD |
| **Qualifikationen** | App | Fachspezifisch, existiert nicht im AD |
| **Abwesenheiten, Zeiterfassung** | App | Fachspezifisch, existiert nicht im AD |

### 7.3 Rollenmapping AD-Gruppen → App-Rollen

| AD-Gruppe | App-Rolle |
|---|---|
| `APP-Mitarbeiterverwaltung-Admin` | ADMIN |
| `APP-Mitarbeiterverwaltung-HR` | HR |
| `APP-Mitarbeiterverwaltung-Leitung` | DEPARTMENT_MANAGER |
| `APP-Mitarbeiterverwaltung-Teamleitung` | TEAM_LEADER (noch nicht konfiguriert) |
| Keine der obigen Gruppen | EMPLOYEE |

Die Gruppen werden in der `.env` konfiguriert (`AD_GROUP_ADMIN`, `AD_GROUP_HR`, `AD_GROUP_MANAGER`). Prioritaet: ADMIN > HR > DEPARTMENT_MANAGER > TEAM_LEADER > EMPLOYEE.

### 7.4 Sync-Richtung: AD → App (Einweg)

```
Active Directory ──────────────► Mitarbeiterverwaltung App
                   Sync-Richtung
  - sAMAccountName                  → ad_username
  - givenName                       → first_name
  - sn                              → last_name
  - mail                            → email
  - department                      → Abteilungszuordnung (TODO)
  - memberOf (Gruppenmitgliedschaft)→ role
```

Die App schreibt **niemals** zurueck ins AD.

### 7.5 Sync-Mechanismen

| Mechanismus | Wann | Was wird synchronisiert |
|---|---|---|
| **Login-Sync** | Bei jeder Anmeldung | Name, E-Mail, Rolle des angemeldeten Benutzers |
| **Periodischer Sync** | Alle 30 Min (Celery-Beat) | Alle aktiven Mitarbeiter mit `ad_username` (TODO) |
| **Manueller Sync** | Admin-Aktion ueber API | Einzelner Mitarbeiter oder alle |

### 7.6 Provisioning & Deprovisioning

| Vorgang | Aktueller Stand | Zielzustand |
|---|---|---|
| **Neuer Mitarbeiter im AD** | Muss manuell in der App angelegt werden | Auto-Provisioning: Neue User aus definierter OU automatisch anlegen |
| **Mitarbeiter deaktiviert im AD** | Bleibt in der App aktiv | Auto-Deprovisioning: `is_active=False` setzen bei naechstem Sync |
| **Mitarbeiter wechselt Abteilung** | Muss manuell aktualisiert werden | Abteilung aus AD-Attribut `department` uebernehmen |

### 7.7 Ablauf: Login mit AD

```
Benutzer             App (Frontend)         Backend (FastAPI)         Active Directory
   │                      │                       │                        │
   │── Login-Formular ───►│                       │                        │
   │                      │── POST /api/v1/auth ─►│                        │
   │                      │                       │── LDAP-Bind ──────────►│
   │                      │                       │   (Service-Account)    │
   │                      │                       │◄── User-DN gefunden ───│
   │                      │                       │                        │
   │                      │                       │── LDAP-Bind ──────────►│
   │                      │                       │   (User-Credentials)   │
   │                      │                       │◄── Authentifiziert ────│
   │                      │                       │                        │
   │                      │                       │── Gruppen + Daten ────►│
   │                      │                       │◄── ADUser-Objekt ──────│
   │                      │                       │                        │
   │                      │                       │── Sync in DB           │
   │                      │                       │── JWT generieren       │
   │                      │◄── JWT-Token ─────────│                        │
   │◄── Dashboard ────────│                       │                        │
```

### 7.8 Entwicklungsmodus (ohne AD)

Wenn `AD_ENABLED=false` (Standard in Entwicklung):
- Authentifizierung laeuft gegen lokale Datenbank (bcrypt-Passwoerter)
- Demo-Benutzer werden beim Start angelegt (Passwort: `dev`)
- Kein LDAP-Server erforderlich

### 7.9 Offene Punkte (TODO)

- [ ] AD-Gruppe fuer TEAM_LEADER konfigurierbar machen (`AD_GROUP_TEAM_LEADER`)
- [ ] Auto-Provisioning: Neue User aus bestimmter OU automatisch anlegen
- [ ] Auto-Deprovisioning: Deaktivierte AD-User in der App sperren
- [ ] Abteilungs-Sync: `department`-Attribut aus AD in App-Abteilung mappen
- [ ] Periodischer Sync via Celery-Beat (alle 30 Min)
- [ ] Login-Sync implementieren (AD-Daten bei jedem Login aktualisieren)

## 8. Entwicklungsphasen

| Phase | Inhalt | Schaetzung |
|---|---|---|
| **Phase 1** | Backend-Grundgeruest, Auth (JWT/Dev), Mitarbeiterverwaltung CRUD, Web-Admin | ✅ Fertig |
| **Phase 2** | Zeiterfassung (Stempeln, Berechnung, Pausen, Zuschlaege) | ✅ Fertig |
| **Phase 3** | Schichtplanung (Vorlagen, Dienstplaene, Zuweisung, Regelwerk, Drag-to-Paint) | ✅ Fertig |
| **Phase 4** | Mobile App Flutter (Login, Zeitstempel, Dienstplan, Chat, Profil) | ✅ Fertig |
| **Phase 5** | Chat & Kommunikation (WebSocket, Einzel-/Gruppenchat, Online-Status) | ✅ Fertig |
| **Phase 6** | Loga-CSV-Export, Monatsabschluss, Berichte (Jahres-/Abteilungs-/Zuschlagsuebersicht) | ✅ Fertig |
| **Phase 7** | Test, Bugfixes, Betriebsrat-Abstimmung, Rollout | Offen |
