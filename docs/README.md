---
name: Projektdokumentation Mitarbeiterverwaltung
description: Zentrale Dokumentation fuer die Mitarbeiterverwaltung IKK Kliniken
type: documentation
---

# Mitarbeiterverwaltung IKK Kliniken — Projektdokumentation

## Uebersicht

Die Mitarbeiterverwaltung ist eine On-Premise-Webanwendung fuer die IKK Kliniken. Sie deckt die Verwaltung von ca. 1.000 Mitarbeitern ab — von Stammdaten ueber Zeiterfassung und Schichtplanung bis hin zu einem internen Chat-System.

**Kernfunktionen:**

- Mitarbeiterverwaltung mit Stammdaten, Abteilungen und Qualifikationen
- Zeiterfassung mit Stempelfunktion, Zuschlagsberechnung und Pausenregelung
- Abwesenheitsverwaltung (Urlaub, Krankheit, Fortbildung) mit Genehmigungsworkflow
- Schichtplanung mit Regelwerk nach Arbeitszeitgesetz (ArbZG)
- Interner Chat mit Echtzeit-Nachrichten (WebSocket), Gruppen, Dateianhängen und Push-Benachrichtigungen
- KI-Support-Bot (BOT001 „MVA Support") beantwortet Bedienungsfragen im Chat
- Monatsabschluss und Loga-Export fuer die Lohnabrechnung
- Auswertungen und Berichte (Jahresuebersicht, Zuschlaege, Abwesenheitsstatistik)
- Rate-Limiting beim Login (Schutz vor Brute-Force-Angriffen)
- DSGVO-konforme rollenbasierte Mitarbeiterliste

**Zielgruppe:** Aerzte, Pflegekraefte, Verwaltung, Technik — mit rollenbasiertem Zugriff.

---

## Inhaltsverzeichnis

1. [Schnellstart (Entwicklung)](#1-schnellstart-entwicklung)
2. [Projektstruktur](#2-projektstruktur)
3. [Tech-Stack](#3-tech-stack)
4. [Backend](#4-backend)
5. [Frontend](#5-frontend)
6. [Mobile App (Android & iOS)](#6-mobile-app-android--ios)
7. [Datenbank](#7-datenbank)
8. [Authentifizierung und Rollen](#8-authentifizierung-und-rollen)
9. [API-Referenz](#9-api-referenz)
10. [Geschaeftslogik im Detail](#10-geschaeftslogik-im-detail)
11. [Deployment (Produktion)](#11-deployment-produktion)
12. [Aktueller Projektstand](#12-aktueller-projektstand)
13. [Dienste, Ports und Firewall](#13-dienste-ports-und-firewall)
14. [Bekannte Einschraenkungen](#14-bekannte-einschraenkungen)

---

## 1. Schnellstart (Entwicklung)

### Voraussetzungen

- Python 3.12+
- Node.js 20+
- Git

### Backend starten (SQLite-Modus, kein PostgreSQL noetig)

```bash
cd Mitarbeiterverwaltung/backend

# Virtuelle Umgebung erstellen und aktivieren
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # Linux/Mac

# Abhaengigkeiten installieren (Entwicklung ohne PostgreSQL)
pip install -r requirements-dev.txt

# Server starten
uvicorn app.main:app --reload --port 8000
```

Beim ersten Start werden automatisch Tabellen erstellt und Demo-Daten geladen.

**API-Dokumentation:** http://localhost:8000/api/docs (Swagger UI)

### Frontend starten

```bash
cd Mitarbeiterverwaltung/frontend

npm install
npm run dev
```

Das Frontend laeuft auf http://localhost:3000 und leitet API-Aufrufe automatisch an Port 8000 weiter (Vite-Proxy).

### Demo-Zugangsdaten

| Benutzer | Rolle | Passwort |
|---|---|---|
| `admin` | Administrator | `dev` |
| `hr.leitung` | Personalabteilung | `dev` |
| `m.mueller` | Abteilungsleitung | `dev` |
| `s.schmidt` | Teamleitung | `dev` |
| `t.weber` | Mitarbeiter | `dev` |

> Alle Demo-Benutzer verwenden im Entwicklungsmodus das Passwort **dev**. In Produktion erfolgt die Anmeldung ueber Active Directory.

### Alternative: Gesamtsystem mit Docker

```bash
cd Mitarbeiterverwaltung

# .env-Datei aus Vorlage erstellen
cp .env.example .env
# DB_PASSWORD in .env setzen!

docker compose up -d
```

Startet PostgreSQL, Redis, Backend und Celery-Worker.

---

## 2. Projektstruktur

```
Mitarbeiterverwaltung/
├── docker-compose.yml          # Container-Setup (PostgreSQL, Redis, Backend, Celery)
├── .env.example                # Vorlage fuer Umgebungsvariablen
├── anforderungen.md            # Funktionale Anforderungen
├── architektur.md              # Technische Architektur und DB-Modell
│
├── backend/                    # Python / FastAPI
│   ├── Dockerfile
│   ├── requirements.txt        # Produktion (mit PostgreSQL, Redis, Celery)
│   ├── requirements-dev.txt    # Entwicklung (SQLite, minimale Abhaengigkeiten)
│   ├── alembic/                # Datenbank-Migrationen
│   ├── app/
│   │   ├── main.py             # FastAPI-Einstiegspunkt
│   │   ├── config.py           # Konfiguration (aus .env)
│   │   ├── database.py         # Datenbank-Verbindung (async SQLAlchemy)
│   │   ├── auth/               # Authentifizierung (JWT, LDAP, Berechtigungen)
│   │   ├── models/             # SQLAlchemy-Datenmodelle
│   │   ├── api/                # API-Endpunkte (Router)
│   │   ├── services/           # Geschaeftslogik
│   │   ├── integrations/       # Externe Systeme (geplant)
│   │   └── websocket/          # WebSocket-Handler (Chat)
│   └── tests/                  # Tests (pytest)
│
├── frontend/                   # React / TypeScript / Vite
│   ├── package.json
│   ├── vite.config.ts          # Dev-Server auf Port 3000, Proxy auf 8000
│   └── src/
│       ├── App.tsx             # Routing und rollenbasierte Seitenfreigabe
│       ├── hooks/useAuth.ts    # Authentifizierungs-Hook
│       ├── services/api.ts     # Axios-API-Client
│       ├── components/         # Wiederverwendbare UI-Bausteine
│       └── pages/              # Seitenkomponenten
│
├── mobile/                     # Flutter / Dart (in Entwicklung)
│   ├── pubspec.yaml
│   └── lib/
│       ├── main.dart
│       ├── screens/            # App-Bildschirme
│       ├── services/           # API-Client, Auth-Provider
│       ├── models/             # Datenmodelle
│       └── widgets/            # Wiederverwendbare Widgets
│
└── docs/                       # Diese Dokumentation
```

---

## 3. Tech-Stack

| Schicht | Technologie | Version |
|---|---|---|
| **Backend** | Python + FastAPI (async) | 3.12 / 0.115 |
| **Datenbank** | PostgreSQL (Produktion) / SQLite (Entwicklung) | 16 / — |
| **ORM** | SQLAlchemy (async) + Alembic | 2.0 |
| **Cache / Broker** | Redis + Celery | 7 / 5.4 |
| **Web-Frontend** | React + TypeScript + Vite | 19 / 5.9 / 8.0 |
| **Mobile App** | Flutter (Dart) | 3.16+ |
| **HTTP-Client** | Axios (Frontend) / http (Mobile) | 1.14 / 1.2 |
| **Icons** | lucide-react (Web) / cupertino_icons (Mobile) | — |
| **Datumslogik** | date-fns (Web) / intl (Mobile) | 4.1 / 0.19 |
| **Auth** | JWT (HS256) + LDAP/Active Directory | — |
| **Reverse Proxy** | nginx (Produktion) | — |
| **Containerisierung** | Docker + Docker Compose | — |

---

## 4. Backend

### Aufbau

Das Backend ist eine asynchrone FastAPI-Anwendung mit klarer Schichtentrennung:

```
Anfrage → Router (api/) → Service (services/) → Datenbank (models/)
                ↕                    ↕
          Auth (auth/)         Externe Systeme (integrations/)
```

- **Router** (`app/api/`): Nehmen HTTP-Anfragen entgegen, pruefen Berechtigungen, rufen Services auf und geben Antworten zurueck.
- **Services** (`app/services/`): Enthalten die eigentliche Geschaeftslogik (Zuschlagsberechnung, Schichtvalidierung, Audit-Protokollierung).
- **Models** (`app/models/`): Definieren die Datenbankstruktur mit SQLAlchemy ORM.
- **Auth** (`app/auth/`): JWT-Token-Verwaltung, LDAP-Anbindung und Berechtigungsprueufungen.

### Konfiguration

Die gesamte Konfiguration erfolgt ueber Umgebungsvariablen (`.env`-Datei), verwaltet durch `pydantic-settings` in `app/config.py`.

**Wichtige Schalter:**

| Variable | Standard (Dev) | Beschreibung |
|---|---|---|
| `DB_USE_SQLITE` | `true` | SQLite statt PostgreSQL verwenden |
| `AD_ENABLED` | `false` | Active-Directory-Authentifizierung deaktivieren |
| `APP_DEBUG` | `true` | Debug-Logging und SQL-Ausgabe |
| `CORS_ORIGINS` | `localhost:3000,...` | Erlaubte Frontend-URLs |

### API-Prefix und Dokumentation

- Alle Endpunkte unter `/api/v1/`
- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`
- Health-Check: `GET /api/health`

### Services im Detail

| Service | Datei | Aufgabe |
|---|---|---|
| **Zeitberechnung** | `time_calculator.py` | Pausenregeln (ArbZG), Zuschlaege (Nacht/Sonntag/Feiertag), Feiertage NRW, Monatssoll |
| **Schichtvalidierung** | `shift_validator.py` | Max. 10h/Tag, 48h/Woche, 11h Ruhezeit, max. 6 Tage am Stueck, Doppelbelegung |
| **Audit** | `audit.py` | Protokolliert alle Aenderungen an Stammdaten (wer, was, wann) |
| **AD-Sync** | `ad_sync.py` | Synchronisiert Mitarbeiterdaten aus Active Directory |
| **Demo-Daten** | `seed.py` | Erstellt Abteilungen, Mitarbeiter und Schichtvorlagen beim ersten Start |

---

## 5. Frontend

### Aufbau

Das Frontend ist eine Single-Page-Application (SPA) mit React und TypeScript. Vite dient als Build-Tool und Entwicklungsserver.

### Seitenstruktur

| Seite | Pfad | Zugriff | Beschreibung |
|---|---|---|---|
| Login | `/login` | Alle | Anmeldung mit Benutzername/Passwort |
| Dashboard | `/` | Alle | Begruessung, Stempelstatus, Monatsuebersicht, Urlaubssaldo |
| Zeiterfassung | `/time` | Alle | Kommen/Gehen-Buttons, Tagesuebersicht, Zuschlaege |
| Mein Dienstplan | `/schedule` | Alle | Monatskalender mit Schichtcodes, farblich kodiert |
| Abwesenheiten | `/absences` | Alle | Urlaubsantrag, Krankmeldung, Genehmigungsstatus |
| Nachrichten | `/chat` | Alle | Echtzeit-Chat (WebSocket), Einzel- und Gruppengespraeche |
| Mitarbeiter | `/employees` | HR/Admin | Suche, Filter, Paginierung, Detailansicht mit Bearbeitung |
| Abteilungen | `/departments` | HR/Admin | Abteilungsliste mit Hierarchie und Kostenstellen |
| Dienstplanung | `/shift-plans` | Leitung | Schichtvorlagen, Monatsplaene, Matrix-Ansicht |
| Monatsabschluss | `/monthly-closing` | HR/Admin | Zeiten abschliessen und als CSV fuer Loga exportieren |
| Auswertungen | `/reports` | HR/Admin | 4 Berichte: Jahres-, Abteilungs-, Zuschlags-, Abwesenheitsstatistik |

### Wichtige Muster

- **Authentifizierung:** `useAuth`-Hook prueft Token im localStorage und laedt Benutzerdaten ueber `/auth/me`. Leitet bei 401 automatisch zum Login weiter.
- **API-Client:** Zentraler Axios-Client in `services/api.ts` mit automatischer Token-Injektion.
- **Rollenbasierte Navigation:** Das Layout blendet Menuepunkte je nach Rolle ein/aus.
- **Styling:** Inline-Styles (kein CSS-Framework), einheitliches Farbschema auf Slate-Basis.

### Befehle

```bash
npm run dev       # Entwicklungsserver (Port 3000)
npm run build     # TypeScript-Pruefung + Produktions-Build
npm run lint      # ESLint
npm run preview   # Produktions-Build lokal testen
```

---

## 6. Mobile App (Android & iOS)

Eine gemeinsame Flutter/Dart-Codebase fuer Android und iOS. Die App richtet sich an alle Mitarbeiter und bietet die wichtigsten Funktionen fuer den Arbeitsalltag im Krankenhaus.

### 6.1 Funktionsumfang

| Screen | Beschreibung |
|---|---|
| **Login** | Anmeldung mit Benutzername/Passwort, Token in Secure Storage |
| **Profil** | Tageszeitabhaengige Begruessung, taeglicher Motivationsspruch (75 Sprueche), Monats-Arbeitszeitkarte mit Fortschrittsbalken, Personalnummer, Abmelden |
| **Zeiterfassung** | Grosser Ein-/Ausstempel-Button, Live-Uhrzeit (sekundengenau), laufende Arbeitszeit seit Einstempeln, Restzeit-Countdown bis Tages-Soll, Tagesuebersicht mit Stunden/Pause/Eintraegen, Pauseneingabe per Slider/Schnellauswahl |
| **Dienstplan** | Eigener Schichtplan als Kalenderansicht, Schichtdetails (Name, Zeiten, Farbe) |
| **Abwesenheiten** | Urlaub/Krankheit/Fortbildung beantragen, Urlaubskonto einsehen, Status verfolgen |
| **Chat** | Echtzeit-Nachrichten per WebSocket, Einzel- und Gruppenchats, Online-Status, Tipp-Anzeige |

### 6.2 Navigation

5-Tab-Navigation am unteren Bildschirmrand:

```
[ Profil ] [ Stempeln ] [ Dienstplan ] [ Abwesend ] [ Chat ]
```

### 6.3 Technische Details

| Bereich | Technologie |
|---|---|
| Framework | Flutter 3 / Dart |
| State Management | Provider-Pattern (`AuthProvider`) |
| HTTP-Client | `http`-Package mit JWT-Bearer-Token |
| Token-Speicherung | `flutter_secure_storage` (Keychain/Keystore) |
| WebSocket | `web_socket_channel` fuer Echtzeit-Chat |
| Datumsformatierung | `intl`-Package (Deutsch) |
| Pull-to-Refresh | `pull_to_refresh_flutter3` |

### 6.4 Android-App

**Lokaler Build:**
```bash
cd Mitarbeiterverwaltung/mobile
flutter build apk --release
```

**CI/CD Build (GitHub Actions):**
Der Android-Build laeuft automatisch bei Push auf `master` (Pfad `mobile/**`) oder per manueller Ausloesung. Workflow: `.github/workflows/build-ios.yml` (Job `build-android`).

**Ausgabe:** `build/app/outputs/flutter-apk/app-release.apk` (~50 MB)

**Fertige APK:** `releases/app-release.apk` (aus GitHub Actions heruntergeladen)

**Installation:**
- APK per USB, E-Mail oder internen Fileserver an Geraete verteilen
- Auf dem Android-Geraet: "Aus unbekannten Quellen installieren" erlauben
- Alternativ: Google Play Store (interner Track) oder MDM-System (z.B. Intune)

**Voraussetzungen:**
- Android 5.0 (API 21) oder hoeher
- Internetzugang zum Backend-Server (internes WLAN)

**Konfiguration:**
- Server-URL in `lib/services/api_service.dart` (`baseUrl`) anpassen
- Fuer Produktion: `android:usesCleartextTraffic="false"` in `AndroidManifest.xml` setzen

### 6.5 iOS-App (iPhone/iPad)

**CI/CD Build (GitHub Actions):**
Der iOS-Build laeuft auf einem macOS-Runner via GitHub Actions. Workflow: `.github/workflows/build-ios.yml` (Job `build-ios`). Der Build wird automatisch bei Push auf `master` (Pfad `mobile/**`) oder manuell ausgeloest.

```bash
# Manuell ausloesen:
gh workflow run build-ios.yml
```

**Lokaler Build (nur auf macOS moeglich):**
```bash
cd Mitarbeiterverwaltung/mobile
flutter build ios --release --no-codesign   # ohne Signierung
flutter build ipa --release                  # mit Signierung (erfordert Apple Developer Account)
```

**Ausgabe:** `build/ios/ipa/mitarbeiterverwaltung.ipa` (~7 MB)

**Fertige IPA:** `releases/mitarbeiterverwaltung.ipa` (aus GitHub Actions heruntergeladen, unsigniert)

**Wichtig:** Der iOS-Build ist **nur auf macOS** moeglich (Apple-Einschraenkung). Deshalb wird GitHub Actions mit macOS-Runner verwendet.

**Aktueller Stand:** Die IPA wird ohne Code-Signierung gebaut (`--no-codesign`). Fuer die Installation auf echten Geraeten ist ein Apple Developer Account ($99/Jahr) erforderlich.

**Verteilung (mit Apple Developer Account):**
- **TestFlight** — fuer interne Tests (bis 10.000 Tester)
- **Apple Business Manager** — fuer firmeninterne Verteilung ohne App Store
- **MDM-System** — Push per Intune, Jamf o.ae.

**iOS-spezifische Konfiguration:**
- Bundle-ID in `ios/Runner.xcodeproj` setzen (z.B. `de.ikk-kliniken.mitarbeiterverwaltung`)
- App Transport Security (ATS): HTTPS ist Pflicht, HTTP wird von iOS blockiert
- Push-Notifications: APNs-Zertifikat im Apple Developer Portal erstellen

### 6.8 CI/CD-Pipeline (GitHub Actions)

**Workflow:** `.github/workflows/build-ios.yml`

| Job | Runner | Dauer | Artefakt |
|---|---|---|---|
| `build-ios` | `macos-latest` | ~3-4 Min | `ios-release-ipa` (IPA) |
| `build-android` | `ubuntu-latest` | ~6 Min | `android-release-apk` (APK) |

**Trigger:**
- Automatisch bei Push auf `master` mit Aenderungen unter `mobile/**`
- Manuell per `workflow_dispatch` (GitHub UI oder `gh workflow run`)

**Artefakte:** Werden 30 Tage auf GitHub gespeichert und koennen unter Actions → Run → Artifacts heruntergeladen werden. Aktuelle Builds liegen auch lokal unter `releases/`.

### 6.6 Gemeinsame Konfiguration (beide Plattformen)

Die Server-URL muss vor dem Build angepasst werden:

```dart
// lib/services/api_service.dart
static String baseUrl = 'https://mitarbeiter.klinik.local/api/v1';
```

**Empfehlung fuer Produktion:** URL ueber eine Konfigurationsdatei oder Build-Flavors steuern, damit Dev- und Prod-Builds getrennt sind.

### 6.7 Offline-Verhalten

Die App benoetigt eine aktive Netzwerkverbindung. Es gibt aktuell keinen Offline-Modus. Bei Verbindungsverlust:
- Stempelversuche schlagen fehl mit Fehlermeldung
- Chat-WebSocket verbindet sich nicht automatisch neu
- Gespeicherte Tokens bleiben erhalten (kein erneuter Login noetig)

---

## 7. Datenbank

### Entwicklungsmodus

Im Entwicklungsmodus wird SQLite verwendet (`mitarbeiterverwaltung.db` im Backend-Ordner). Tabellen werden beim Serverstart automatisch erstellt — keine Migration noetig.

### Produktionsmodus

In Produktion wird PostgreSQL 16 eingesetzt. Datenbank-Migrationen laufen ueber Alembic:

```bash
# Migration erstellen (nach Modellaenderung)
alembic revision --autogenerate -m "Beschreibung der Aenderung"

# Migration ausfuehren
alembic upgrade head
```

> **Hinweis:** Aktuell existieren noch keine Alembic-Migrationsdateien. Die initiale Migration muss vor dem Produktionseinsatz erstellt werden.

### Datenmodell (Kerntabellen)

```
employees ──────────── departments
    │                      │
    ├── qualifications     │ (Hierarchie: parent_id)
    │                      │
    ├── time_entries ──── surcharges
    │
    ├── absences
    │
    ├── monthly_closings
    │
    ├── shift_assignments ── shift_templates
    │       │                    │
    │       ├── coverage_requests│
    │       └── swap_requests    └── shift_requirements
    │
    ├── conversation_members ── conversations ── messages
    │
    └── audit_logs
```

**Wichtige Zusammenhaenge:**

- **Mitarbeiter** gehoeren zu einer **Abteilung** (mit optionaler Hierarchie: Klinik > Abteilung > Station)
- **Zeiteintraege** koennen **Zuschlaege** haben (Nacht, Sonntag, Feiertag)
- **Schichtzuweisungen** verweisen auf **Schichtvorlagen** (Frueh, Spaet, Nacht etc.)
- **Monatsabschluesse** aggregieren Zeitdaten pro Mitarbeiter und Monat
- **Audit-Logs** protokollieren alle Aenderungen mit Benutzer, Aktion und geaenderten Feldern

---

## 8. Authentifizierung und Rollen

### Ablauf

```
[Login-Formular] → POST /auth/login
                        │
          ┌─────────────┴──────────────┐
          │ Entwicklung               │ Produktion
          │ Passwort = "dev"          │ LDAP-Bind gegen AD
          └─────────────┬──────────────┘
                        │
                  JWT-Token-Paar
                  (Access: 15 Min, Refresh: 7 Tage)
                        │
               Alle weiteren Anfragen
               mit Bearer-Token im Header
```

### Rollen und Berechtigungen

| Rolle | Kuerzel | Zugriff |
|---|---|---|
| **Administrator** | ADMIN | Vollzugriff auf alle Funktionen und Daten |
| **Personalabteilung** | HR | Stammdaten, Zeitauswertungen, Loga-Export, Genehmigungen |
| **Abteilungsleitung** | DEPARTMENT_MANAGER | Dienstplanung, Genehmigungen, Teamuebersicht (eigene Abteilung) |
| **Teamleitung** | TEAM_LEADER | Dienstplanung und Genehmigungen im eigenen Team |
| **Mitarbeiter** | EMPLOYEE | Eigene Daten, Zeiterfassung, Urlaubsantrag, Chat |

### Active Directory (Produktion)

Die Rollenzuordnung erfolgt ueber AD-Gruppenmitgliedschaft:

| AD-Gruppe | Rolle |
|---|---|
| `APP-Mitarbeiterverwaltung-Admin` | ADMIN |
| `APP-Mitarbeiterverwaltung-HR` | HR |
| `APP-Mitarbeiterverwaltung-Leitung` | DEPARTMENT_MANAGER |
| Keine der obigen Gruppen | EMPLOYEE |

Ein taeglicher Sync (`ad_sync.py`) gleicht Name, E-Mail und Abteilung aus dem AD ab. Der Sync kann auch manuell ueber `POST /admin/ad-sync` ausgeloest werden.

---

## 9. API-Referenz

Vollstaendige interaktive Dokumentation unter `/api/docs` (Swagger UI).

### Endpunkte nach Bereich

#### Authentifizierung (`/auth`)

| Methode | Pfad | Beschreibung |
|---|---|---|
| POST | `/auth/login` | Anmelden (gibt Access- und Refresh-Token zurueck) |
| POST | `/auth/refresh` | Access-Token erneuern |
| GET | `/auth/me` | Eigene Benutzerdaten abrufen |

#### Mitarbeiter (`/employees`)

| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/employees` | Liste (paginiert, suchbar, filterbar nach Abteilung) |
| GET | `/employees/{id}` | Einzelner Mitarbeiter |
| POST | `/employees` | Neuen Mitarbeiter anlegen (HR/Admin) |
| PATCH | `/employees/{id}` | Mitarbeiter bearbeiten (eigene Kontaktdaten oder alle Felder fuer HR) |
| DELETE | `/employees/{id}` | Mitarbeiter deaktivieren (Soft-Delete, HR/Admin) |
| GET | `/employees/{id}/qualifications` | Qualifikationen eines Mitarbeiters |
| POST | `/employees/{id}/qualifications` | Qualifikation hinzufuegen (HR/Admin) |

#### Abteilungen (`/departments`)

| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/departments` | Alle aktiven Abteilungen |
| GET | `/departments/{id}` | Einzelne Abteilung |
| POST | `/departments` | Abteilung erstellen (HR/Admin) |
| PATCH | `/departments/{id}` | Abteilung bearbeiten (HR/Admin) |
| GET | `/departments/{id}/employees` | Mitarbeiter einer Abteilung |

#### Zeiterfassung (`/time`)

| Methode | Pfad | Beschreibung |
|---|---|---|
| POST | `/time/clock-in` | Einstempeln |
| POST | `/time/clock-out` | Ausstempeln (berechnet Pause und Zuschlaege automatisch) |
| GET | `/time/status` | Aktueller Stempelstatus |
| POST | `/time/manual` | Manuellen Zeiteintrag erstellen |
| GET | `/time/entries` | Zeiteintraege nach Zeitraum abfragen |
| GET | `/time/daily` | Tagesuebersicht (Summe, Pause) |
| GET | `/time/monthly` | Monatsuebersicht (Soll, Ist, Ueberstunden, Zuschlaege) |
| POST | `/time/corrections` | Korrekturantrag stellen |
| GET | `/time/corrections/pending` | Offene Korrekturantraege (Leitung/HR) |
| POST | `/time/corrections/{id}/review` | Korrektur genehmigen/ablehnen |

#### Abwesenheiten (`/absences`)

| Methode | Pfad | Beschreibung |
|---|---|---|
| POST | `/absences` | Abwesenheit beantragen (Urlaub, Krank, Fortbildung, Sonder) |
| GET | `/absences` | Eigene Abwesenheiten (oder Team fuer Leitung) |
| GET | `/absences/pending` | Offene Antraege (Leitung/HR) |
| POST | `/absences/{id}/review` | Antrag genehmigen/ablehnen |
| DELETE | `/absences/{id}` | Antrag stornieren |
| GET | `/absences/vacation-balance` | Urlaubssaldo (Anspruch, genommen, offen, Rest) |

#### Schichtplanung (`/shifts`)

| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/shifts/templates` | Schichtvorlagen (Frueh, Spaet, Nacht etc.) |
| POST | `/shifts/templates` | Schichtvorlage erstellen (Leitung) |
| POST | `/shifts/plans` | Monatsplan erstellen (Leitung) |
| GET | `/shifts/plans` | Monatsplaene auflisten |
| POST | `/shifts/plans/{id}/publish` | Plan veroeffentlichen |
| POST | `/shifts/plans/{id}/assign` | Mitarbeiter einer Schicht zuweisen |
| POST | `/shifts/plans/{id}/assign-bulk` | Mehrere Zuweisungen auf einmal |
| DELETE | `/shifts/assignments/{id}` | Zuweisung entfernen |
| GET | `/shifts/plans/{id}/view` | Matrix-Ansicht (Mitarbeiter x Tage) |
| GET | `/shifts/my-schedule` | Eigener Dienstplan |
| GET | `/shifts/staffing-check` | Mindestbesetzung pruefen |
| POST | `/shifts/requirements` | Besetzungsanforderung definieren |
| POST | `/shifts/coverage` | Vertretung anfragen |
| GET | `/shifts/coverage/open` | Offene Vertretungsanfragen |
| POST | `/shifts/coverage/{id}/volunteer` | Vertretung uebernehmen |
| POST | `/shifts/swap` | Schichttausch anfragen |
| POST | `/shifts/swap/{id}/approve` | Schichttausch genehmigen |

#### Monatsabschluss (`/monthly`)

| Methode | Pfad | Beschreibung |
|---|---|---|
| POST | `/monthly/close` | Monat abschliessen (sperrt Zeiteintraege) |
| GET | `/monthly/overview` | Uebersicht des Abschlussstatus |
| POST | `/monthly/export` | CSV-Export im Loga-Format |

#### Chat (`/chat` und `/conversations`)

| Methode | Pfad | Beschreibung |
|---|---|---|
| WS | `/chat/ws/{token}` | WebSocket-Verbindung (Echtzeit-Nachrichten) |
| GET | `/conversations` | Eigene Gespraeche mit letzter Nachricht |
| POST | `/conversations` | Neues Gespraech (Einzel oder Gruppe) |
| GET | `/conversations/{id}/messages` | Nachrichtenverlauf (paginiert) |
| POST | `/conversations/{id}/messages` | Nachricht senden (REST-Fallback) |
| GET | `/chat/employees` | Mitarbeiterliste fuer Chat-Erstellung |
| GET | `/chat/online` | Aktuell online verbundene Benutzer |

#### Auswertungen (`/reports`)

| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/reports/yearly-overview` | Jahresuebersicht pro Mitarbeiter |
| GET | `/reports/department-summary` | Abteilungszusammenfassung fuer einen Monat |
| GET | `/reports/surcharge-summary` | Zuschlagsuebersicht (Nacht, Sonntag, Feiertag) |
| GET | `/reports/absence-statistics` | Abwesenheitsstatistik nach Typ und Monat |
| GET | `/reports/export-extended` | Erweiterter CSV-Export mit Zuschlaegen |

#### Admin (`/admin`)

| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/admin/dashboard` | Basis-Kennzahlen (Mitarbeiteranzahl) |
| POST | `/admin/ad-sync` | Active-Directory-Sync manuell ausloesen |

---

## 10. Geschaeftslogik im Detail

### Zeiterfassung und Zuschlaege

Die Zuschlagsberechnung folgt dem TVoeD / hauseigenem Tarif:

| Zuschlagsart | Zeitraum | Satz |
|---|---|---|
| **Nacht** | 20:00 – 06:00 Uhr | 20 % |
| **Sonntag** | Ganzer Sonntag | 25 % |
| **Feiertag** | Ganzer Feiertag | 35 % |
| **Samstag** | Ganzer Samstag | 0 % (konfigurierbar) |
| **Ueberstunden** | Ab Monatssoll | 30 % |

**Pausenregeln nach Arbeitszeitgesetz (ArbZG):**

- Ab 6 Stunden Arbeitszeit: mindestens 30 Minuten Pause
- Ab 9 Stunden Arbeitszeit: mindestens 45 Minuten Pause
- Wird automatisch beim Ausstempeln geprueft und ggf. ergaenzt

**Feiertage:** Gesetzliche Feiertage fuer NRW werden automatisch berechnet (inkl. beweglicher Feiertage wie Ostern, Pfingsten, Fronleichnam).

### Schichtplanung — Regelwerk

Bei jeder Schichtzuweisung werden folgende Regeln geprueft:

| Regel | Grenzwert | Quelle |
|---|---|---|
| Max. taegliche Arbeitszeit | 10 Stunden | § 3 ArbZG |
| Max. woechentliche Arbeitszeit | 48 Stunden | § 3 ArbZG |
| Mindestruhezeit zwischen Schichten | 11 Stunden | § 5 ArbZG |
| Max. aufeinanderfolgende Arbeitstage | 6 Tage | § 9 ArbZG |
| Keine Doppelbelegung | 1 Schicht pro Tag | — |

Verstoesse werden als Fehler (blockiert Zuweisung) oder Warnung (erlaubt mit Hinweis) zurueckgegeben.

### Abwesenheiten

- **Urlaubsanspruch:** Standard 30 Tage/Jahr (konfigurierbar pro Mitarbeiter)
- **Krankmeldung:** Wird automatisch genehmigt
- **Urlaubsantrag:** Muss von Leitung/HR genehmigt werden
- **Ueberlappungspruefung:** Bereits genehmigte Abwesenheiten im gleichen Zeitraum werden erkannt
- **Arbeitstage-Berechnung:** Nur Mo–Fr ohne Feiertage werden gezaehlt

### Monatsabschluss und Loga-Export

1. HR schliesst den Monat ab → Zeiteintraege werden gesperrt (Status: LOCKED)
2. Pro Mitarbeiter wird ein Abschlussrecord erstellt (Soll, Ist, Ueberstunden, Krankheitstage, Urlaubstage)
3. CSV-Export im Loga-Format: Semikolon-getrennt, deutsches Zahlenformat (Komma statt Punkt)

---

## 11. Deployment (Produktion)

### Architektur

```
┌─────────────────────────────────────────────────┐
│               ON-PREMISE SERVER                  │
│                                                  │
│  nginx (TLS) → FastAPI → PostgreSQL             │
│                    ↕          ↕                   │
│                  Redis    Celery-Worker           │
│                    ↕                              │
│             Active Directory                      │
└─────────────────────────────────────────────────┘
        │                    │
   Web-Admin            Mobile App
   (React)              (Flutter)
```

### Serveranforderungen

| Ressource | Minimum | Empfohlen |
|---|---|---|
| CPU | 4 Kerne | 8 Kerne |
| RAM | 16 GB | 32 GB |
| Speicher | 100 GB SSD | 250 GB SSD |
| OS | Ubuntu 22.04 LTS oder RHEL 9 | |
| Netzwerk | Zugang zu AD, internes WLAN fuer App | |

### Wichtige Umgebungsvariablen (Produktion)

```env
DB_USE_SQLITE=false
DB_PASSWORD=<sicheres_passwort>
JWT_SECRET_KEY=<zufaelliger_schluessel>
AD_ENABLED=true
AD_SERVER=ldap://dc01.klinik.local
APP_ENV=production
APP_DEBUG=false
CORS_ORIGINS=https://mitarbeiter.klinik.local
```

### Sicherheit

- **TLS 1.3** ueber nginx (Terminierung)
- **JWT-Tokens:** Access 15 Min, Refresh 7 Tage
- **RBAC:** Rollenbasierte Zugriffskontrolle auf API-Ebene
- **Audit-Log:** Alle Aenderungen an Stammdaten und Genehmigungen
- **DSGVO-konform:** Loeschkonzept, Datenminimierung
- **Chat-Verschluesselung:** Geplant (AES-256 in der Datenbank)

---

## 12. Aktueller Projektstand

*Letzte Aktualisierung: 29.03.2026*

### Implementierungsstatus

| Bereich | Backend | Frontend | Mobile | Status |
|---|---|---|---|---|
| Authentifizierung (JWT + Dev-Modus) | ✅ | ✅ | ✅ | Fertig |
| LDAP/Active-Directory-Anbindung | ✅ | — | — | Fertig (nicht getestet gegen Prod-AD) |
| Mitarbeiterverwaltung (CRUD) | ✅ | ✅ | — | Fertig |
| Abteilungen (Hierarchie) | ✅ | ✅ | — | Fertig |
| Zeiterfassung (Stempeln, Zuschlaege) | ✅ | ✅ | ✅ (Struktur) | Fertig |
| Abwesenheiten (Workflow) | ✅ | ✅ | ✅ (Struktur) | Fertig |
| Schichtplanung (Vorlagen, Regeln) | ✅ | ✅ | ✅ (Struktur) | Fertig |
| Vertretung und Schichttausch | ✅ | — | — | Backend fertig, Frontend ausstehend |
| Chat (WebSocket + REST) | ✅ | ✅ | ✅ (Struktur) | Fertig |
| Monatsabschluss + Loga-Export | ✅ | ✅ | — | Fertig |
| Auswertungen und Berichte | ✅ | ✅ | — | Fertig |
| Audit-Protokollierung | ✅ | — | — | Backend fertig |
| Demo-Daten (Seed) | ✅ | — | — | Fertig |
| Docker-Deployment | ✅ | — | — | Konfiguriert, nicht in Produktion getestet |
| Alembic-Migrationen | ⚙️ | — | — | Konfiguriert, keine Migrationsdateien erstellt |
| Tests | ⚠️ | — | — | Nur Beispielstruktur, keine echten Tests |
| Mobile App (Build/Plattform) | — | — | ✅ | Android APK + iOS IPA via GitHub Actions |

### Entwicklungsphasen (aus Architekturplan)

| Phase | Inhalt | Stand |
|---|---|---|
| **Phase 1** | Backend-Grundgeruest, Auth, Mitarbeiterverwaltung, Web-Admin | ✅ Abgeschlossen |
| **Phase 2** | Zeiterfassung (Stempeln, Berechnung, Korrekturen) | ✅ Abgeschlossen |
| **Phase 3** | Schichtplanung (Vorlagen, Zuweisung, Regelwerk) | ✅ Abgeschlossen |
| **Phase 4** | Mobile App (Login, Zeitstempel, Dienstplan, Self-Service) | ✅ Abgeschlossen (Android + iOS Build) |
| **Phase 5** | Chat und Kommunikation (WebSocket, Push, Gruppen, Dateianhänge, Support-Bot) | ✅ Abgeschlossen |
| **Phase 6** | Loga-Export, Monatsabschluss, Auswertungen | ✅ Abgeschlossen |
| **Phase 7** | Test, Bugfixes, Betriebsrat-Abstimmung, Rollout | ⏳ Ausstehend |

---

## 13. Dienste, Ports und Firewall

### Diensteuebersicht

| Dienst | Technologie | Port | Protokoll | Beschreibung |
|---|---|---|---|---|
| **PostgreSQL** | postgres:16-alpine | 5432 | TCP | Datenbank (nur Produktion, Entwicklung nutzt SQLite) |
| **Redis** | redis:7-alpine | 6379 | TCP | Cache und Message-Broker fuer Celery |
| **Backend API** | FastAPI + Uvicorn | 8000 | TCP (HTTP) | REST-API und WebSocket-Endpunkt |
| **Frontend** | React + Vite | 3000 | TCP (HTTP) | Web-Oberflaeche (nur Entwicklung, in Produktion ueber nginx) |
| **Celery Worker** | Python + Celery | — | — | Hintergrund-Tasks (kein eigener Port) |
| **nginx** | nginx (Produktion) | 443 / 80 | TCP (HTTPS/HTTP) | Reverse Proxy mit TLS-Terminierung |

### Abhaengigkeiten und Startreihenfolge

```
1. PostgreSQL (Port 5432)     ← muss zuerst laufen
2. Redis (Port 6379)          ← muss zuerst laufen
3. Backend API (Port 8000)    ← wartet auf PostgreSQL + Redis
4. Celery Worker              ← wartet auf PostgreSQL + Redis
5. Frontend (Port 3000)       ← braucht Backend API
6. Mobile App                 ← braucht Backend API (ueber Netzwerk)
```

### Firewall-Regeln

#### Entwicklung (lokaler Rechner)

Alle Dienste laufen auf `localhost` — keine Firewall-Freigabe noetig.

#### Produktion (On-Premise Server)

| Regel | Port | Richtung | Quelle → Ziel | Zweck |
|---|---|---|---|---|
| HTTPS Web-Frontend | **443** | Eingehend | Klinik-Netz → Server | Web-Zugriff (nginx) |
| HTTP-Redirect | **80** | Eingehend | Klinik-Netz → Server | Weiterleitung auf HTTPS |
| Backend API | **8000** | Eingehend | Klinik-WLAN → Server | Mobile App Zugriff (falls kein nginx-Proxy) |
| WebSocket | **8000** | Eingehend | Klinik-WLAN → Server | Chat-Echtzeit (ueber selben Port wie API) |
| LDAP/AD | **389** | Ausgehend | Server → Domain Controller | Active-Directory-Authentifizierung |
| LDAPS/AD | **636** | Ausgehend | Server → Domain Controller | AD ueber SSL (empfohlen) |
| DNS | **53** | Ausgehend | Server → DNS-Server | Namensaufloesung |

> **Hinweis:** PostgreSQL (5432) und Redis (6379) sollten **nicht** von aussen erreichbar sein. Diese Ports nur auf `localhost` oder im Docker-Netzwerk oeffnen.

#### Empfohlene Architektur mit nginx

```
Internet / Klinik-Netz
        │
   Port 443 (HTTPS)
        │
    ┌───▼───┐
    │ nginx │  ← TLS-Terminierung, statische Frontend-Dateien
    └───┬───┘
        │
   Port 8000 (intern)
        │
    ┌───▼────┐
    │ Backend│ → PostgreSQL (5432, intern)
    │ FastAPI│ → Redis (6379, intern)
    └────────┘
```

Bei dieser Architektur muss **nur Port 443** in der Firewall freigegeben werden. Die Mobile App verbindet sich ebenfalls ueber `https://mitarbeiter.klinik.local/api/v1`.

### Startskripte

Zum Starten und Beenden aller Dienste liegen Batch-Dateien im Projektordner:

| Datei | Beschreibung |
|---|---|
| `start.bat` | Startet alle Dienste (Backend + Frontend + Cloudflare Tunnel) |
| `stop.bat` | Beendet alle Dienste sauber (inkl. Tunnel) |

Aufruf:
```bash
cd Mitarbeiterverwaltung
start.bat       # Alles starten
stop.bat        # Alles beenden
```

---

## 14. Bekannte Einschraenkungen

| Thema | Beschreibung | Prioritaet |
|---|---|---|
| **Keine Alembic-Migrationen** | Tabellen werden per `create_all()` erstellt — fuer Produktion muessen Migrationen angelegt werden | Hoch |
| **iOS ohne Code-Signierung** | IPA wird ohne Signierung gebaut — fuer echte Geraete ist ein Apple Developer Account ($99/Jahr) noetig | Niedrig |
| **Vertretung/Tausch im Frontend** | Backend-Endpunkte existieren, aber kein UI dafuer | Mittel |
| **Admin-Dashboard** | Zeigt nur Basis-Kennzahlen, koennte um Diagramme erweitert werden | Niedrig |
| **App.css** | Enthaelt ungenutzten Vite-Template-Code | Niedrig |
| **Hardcodierte WebSocket-URL** | Chat verbindet sich fest mit `127.0.0.1:8000` | Niedrig |
