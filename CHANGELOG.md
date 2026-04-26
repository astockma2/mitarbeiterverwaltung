# Changelog

## [1.5.1] - 2026-04-26

### Jahres-Dienstplan — IT-Team-Beispieldaten 2026
- Neuer idempotenter Seed `seed_jahresplan_2026` legt 9 IT-Mitarbeiter (Stefan Raida, Holger Enig, Tom Scheike, Andre Stoecklein, Peter Czaikowski, Marc Nitsch, Ronny Weise, Andre Stockmann, Ben Nettkau) und ihre `DutyPlanEntry`-Eintraege fuer 2026 an.
- Dienstplanung-Seite zeigt damit out-of-the-box die echten Tagescodes (U/Ug/A/S/B/I/H/Dr/K/su/T/TSC) wie auf dem Plan-Screenshot vom 26.04.2026.
- Leere Felder = Normaldienst (Default).

## [0.2.0] - 2026-03-30

### Mitarbeiter-Seite (Frontend)
- Mitarbeiter werden nach Abteilungen gruppiert in aufklappbaren Karten angezeigt
- Client-seitige Suche nach Name, Personalnummer und E-Mail
- Neue Spalte "Beschaeftigungsart" (Vollzeit, Teilzeit, Minijob, Azubi)
- Backend: `EmployeeListResponse` liefert jetzt `department_name` und `employment_type`

### Beschaeftigungsarten
- Beschaeftigungsart ist im Mitarbeiter-Detail per Dropdown aenderbar (HR/Admin)
- In der Mitarbeiterliste als eigene Spalte sichtbar

### Dienstplanung — Schichtvorlagen (CRUD)
- Neuer Bereich "Schichtvorlagen verwalten" in der Werkzeugleiste
- Schichtvorlagen erstellen: Name, Kuerzel, Start-/Endzeit, Pause, Farbe, Mitternacht-Option
- Schichtvorlagen bearbeiten und loeschen (Soft-Delete)
- Backend: neue Endpoints `PUT /api/v1/shifts/templates/{id}` und `DELETE /api/v1/shifts/templates/{id}`

### Chat — Neuer-Chat-Dialog
- Mitarbeiter im "Neuer Chat"-Dialog nach Abteilungen gruppiert (auf-/zuklappbar)
- Suchfeld zum Filtern der Mitarbeiter nach Name
- Backend: Chat-Employees-Endpoint liefert jetzt `department_id` und `department_name`

### Chat — Aktualisierung
- WebSocket-Reconnect: Automatische Wiederverbindung nach 3 Sekunden bei Abbruch
- Polling-Fallback: Konversationsliste und aktive Nachrichten werden alle 10 Sekunden aktualisiert
- Ref statt State fuer WebSocket und aktive Konversation (behebt Race-Condition bei neuen Nachrichten)

### Server-Zugriff
- Vite Dev-Server hoert auf `0.0.0.0` (erreichbar ueber LAN/externe IP)
- Frontend API-Base-URL dynamisch (relativ statt hardcoded `127.0.0.1`)
- Backend CORS erlaubt alle Origins fuer Entwicklung

### Mobile App (Flutter)
- ChatEmployee-Model erweitert um `departmentId` und `departmentName`
- Neuer-Chat-Dialog: Mitarbeiter nach Abteilungen gruppiert mit Suchfeld
- Chat-Detail: Polling alle 5 Sekunden fuer neue Nachrichten
- API-Base-URL ueber `--dart-define=API_URL=...` konfigurierbar

## [0.1.0] - Erstversion

- Login mit AD-Benutzername (Dev-Modus: Passwort "dev")
- Dashboard mit Statistiken
- Zeiterfassung (Stempeln, Eintraege, Korrekturen)
- Abwesenheitsverwaltung (Urlaub, Krank, Fortbildung)
- Dienstplanung mit Drag-and-Paint-Kalender
- Schichtvorlagen mit ArbZG-Validierung
- Chat mit WebSocket-Echtzeit
- Monatsabschluss und Reports/Export
- Mitarbeiter- und Abteilungsverwaltung
- RBAC: Admin, HR, Abteilungsleitung, Teamleitung, Mitarbeiter
- Flutter Mobile-App (Android/iOS)
