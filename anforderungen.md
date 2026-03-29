---
name: Anforderungsdokument Mitarbeiterverwaltung
description: Funktionale und technische Anforderungen fuer die Mitarbeiterverwaltungssoftware mit Zeiterfassung und Kommunikation
type: requirements
---

# Anforderungsdokument — Mitarbeiterverwaltung IKK Kliniken

## 1. Projektuebersicht

| Feld | Wert |
|---|---|
| Projektname | Mitarbeiterverwaltung IKK Kliniken |
| Zielgruppe | ca. 1.000 Mitarbeiter (Aerzte, Pflege, Verwaltung, Technik) |
| Betriebsmodell | On-Premise (eigene Krankenhaus-IT) |
| Anbindungen | Active Directory, P&I Loga (Lohnabrechnung) |
| Plattformen | Web (Admin), Mobile App (iOS + Android) |

---

## 2. Funktionale Anforderungen

### 2.1 Mitarbeiterverwaltung (Stammdaten)

- **Mitarbeiterprofil**: Name, Personalnummer, Abteilung, Berufsgruppe, Rolle, Vertragsart, Eintrittsdatum
- **Abteilungen und Teams**: Hierarchische Struktur (Klinik > Abteilung > Station/Team)
- **Qualifikationen**: Facharztbezeichnungen, Zertifikate, Pflichtschulungen mit Ablaufdatum
- **Dokumentenablage**: Vertraege, Nachweise, Zeugnisse (pro Mitarbeiter)
- **Onboarding-Checklisten**: Aufgabenlisten fuer neue Mitarbeiter
- **Rollen und Rechte**: Admin, Abteilungsleiter, Teamleiter, Mitarbeiter

### 2.2 Zeiterfassung

- **Stempeln per App**: Kommen/Gehen ueber die mobile App (mit Standortpruefung optional)
- **Stempeln per Web**: Fuer Verwaltungsmitarbeiter am PC
- **Automatische Berechnung**:
  - Tagesarbeitszeit, Wochenarbeitszeit, Monatsarbeitszeit
  - Ueberstunden
  - Zuschllaege: Nacht, Sonntag, Feiertag (nach TVoeD/hauseigenem Tarif)
- **Pausenregelung**: Automatische Pausenabzuege nach Arbeitszeitgesetz
- **Korrekturen**: Mitarbeiter kann Korrekturantraege stellen, Vorgesetzter genehmigt
- **Abwesenheiten**:
  - Urlaub (Antrag > Genehmigung > Kalender)
  - Krankheit
  - Fortbildung
  - Sonderurlaub
- **Monatsabschluss**: Zeitdaten werden monatlich abgeschlossen und an Loga exportiert

### 2.3 Schichtplanung / Dienstplanung

- **Schichtmodelle**: Frueh, Spaet, Nacht, Bereitschaft, Rufbereitschaft — frei konfigurierbar
- **Dienstplan erstellen**: Abteilungsleiter plant Mitarbeiter auf Schichten (Monatsansicht)
- **Regelwerk**:
  - Maximale Arbeitszeit pro Tag/Woche (ArbZG)
  - Mindestruhezeit zwischen Schichten (11 Stunden)
  - Qualifikationsanforderungen pro Schicht (z.B. min. 1 Facharzt)
  - Wunschdienste / Tauschangebote durch Mitarbeiter
- **Konflikterkennung**: Warnung bei Regelverstoessen
- **Vertretungsmanagement**: Anfrage an verfuegbare Mitarbeiter bei Ausfall
- **Soll/Ist-Vergleich**: Geplante vs. tatsaechlich geleistete Zeiten

### 2.4 Kommunikation (Mobile App)

- **Einzelchat**: Direkte Nachrichten zwischen zwei Mitarbeitern
- **Gruppenchat**: Teams, Abteilungen, stationsbezogen
- **Ankuendigungen**: Einweg-Mitteilungen von Leitung an Gruppen (kein Antworten)
- **Push-Benachrichtigungen**:
  - Neuer Dienstplan veroeffentlicht
  - Dienstplanaenderung
  - Vertretungsanfrage
  - Neue Nachricht
  - Urlaubsantrag genehmigt/abgelehnt
- **Verfuegbarkeit melden**: "Ich kann einspringen" — fuer Vertretungsanfragen
- **Dateien teilen**: Bilder, PDFs (z.B. Aushanginfos)
- **Lesebestaetigung**: Fuer Ankuendigungen (wer hat gelesen?)

### 2.5 Self-Service (Mobile App fuer Mitarbeiter)

- Eigene Zeiten einsehen
- Dienstplan einsehen
- Urlaubsantrag stellen
- Krankmeldung einreichen
- Zeitkorrektur beantragen
- Eigene Dokumente einsehen
- Persoenliche Daten aktualisieren (Adresse, Telefon, Notfallkontakt)

---

## 3. Schnittstellen

### 3.1 Active Directory (AD)

- **Richtung**: AD → System (Import)
- **Zweck**: Benutzer-Authentifizierung (SSO via LDAP/Kerberos), Stammdaten-Sync
- **Sync**: Taeglich automatisch + manuell ausloesbar
- **Daten**: Benutzername, Name, E-Mail, Abteilung, Gruppenmitgliedschaft

### 3.2 P&I Loga (Lohnabrechnung)

- **Richtung**: System → Loga (Export)
- **Zweck**: Monatliche Uebergabe der Zeitdaten fuer Lohnabrechnung
- **Format**: CSV oder XML (nach Loga-Importspezifikation)
- **Daten**: Personalnummer, Arbeitsstunden, Ueberstunden, Zuschlaege, Abwesenheiten
- **Frequenz**: Monatlich nach Zeitabschluss

---

## 4. Nicht-funktionale Anforderungen

| Anforderung | Zielwert |
|---|---|
| Verfuegbarkeit | 99,5% waehrend Betriebszeiten |
| Antwortzeit API | < 500ms (95. Perzentil) |
| Gleichzeitige Nutzer | mind. 300 |
| Datenspeicherung | On-Premise, verschluesselt |
| Backup | Taeglich, 30 Tage Aufbewahrung |
| DSGVO | Vollstaendig konform, Loeschkonzept |
| Betriebsrat | Keine verdeckte Leistungsueberwachung, Betriebsvereinbarung erforderlich |
| Barrierefreiheit | WCAG 2.1 Level AA (Web-Frontend) |

---

## 5. Benutzerrollen

| Rolle | Zugriff |
|---|---|
| **Administrator** | Vollzugriff, Systemkonfiguration, Benutzerverwaltung |
| **Personalabteilung** | Stammdaten, Zeitauswertungen, Loga-Export, Abwesenheiten |
| **Abteilungsleiter** | Dienstplanung, Genehmigungen, Teamuebersicht der eigenen Abteilung |
| **Teamleiter** | Dienstplanung Team, Genehmigungen Team |
| **Mitarbeiter** | Self-Service, eigene Daten, Chat |

---

## 6. Implementierungsstand (Stand: Maerz 2026)

### Umgesetzt

| Funktion | Details |
|---|---|
| **Mitarbeiterverwaltung** | CRUD, Detailansicht mit Bearbeitung (Adresse, Telefon, Geburtsdatum, Beruf, Arbeitszeitmodell, Notfallkontakt, Urlaubstage). Self-Edit fuer Mitarbeiter (eigene Kontaktdaten). Qualifikationen. |
| **Abteilungsverwaltung** | Hierarchische Struktur, Kostenstellen |
| **Zeiterfassung** | Kommen/Gehen per Web und App, Pausen, Tages-/Monatsuebersicht, Zuschlaege (Nacht/Sonntag/Feiertag) |
| **Abwesenheiten** | Urlaub, Krankheit, Fortbildung, Sonderurlaub. Antragsworkflow mit Genehmigung. Urlaubskonto. |
| **Schichtplanung** | 6 Schichtvorlagen (Frueh/Spaet/Nacht/Tag/Bereitschaft/Rufbereitschaft). Monatsplaene pro Abteilung. **Drag-to-Paint-Kalender**: Schichtvorlage oben auswaehlen, dann mit gedrückter Maus ueber Tage ziehen. Bulk-Zuweisung. Radierer-Werkzeug. Regelwerk-Pruefung (Ruhezeit, Max-Stunden). Diensttausch, Vertretungsanfragen. Veroeffentlichung. |
| **Monatsabschluss** | Zeitdaten pro Mitarbeiter abschliessen, Loga-CSV-Export (Semikolon-getrennt, deutsches Dezimalformat) |
| **Berichte** | Jahresuebersicht, Abteilungszusammenfassung, Zuschlagsuebersicht, Abwesenheitsstatistik, erweiterter CSV-Export |
| **Chat** | Einzel- und Gruppenchat ueber WebSocket. Echtzeit-Nachrichten, Typing-Indicator, Online-Status, Ungelesen-Zaehler. |
| **Mobile App** | Flutter-App mit Login, Dashboard, Zeitstempel (grosser runder Button), Dienstplan-Kalender, Abwesenheiten, Chat, Profil |
| **Authentifizierung** | JWT mit Access/Refresh-Token. Dev-Modus mit Passwort "dev". Rollenbasierte Zugriffskontrolle (5 Rollen). |
| **Audit-Log** | Alle Stammdatenaenderungen werden protokolliert |

### Noch offen

| Funktion | Status |
|---|---|
| Active Directory SSO | Geplant (Phase 7) |
| Push-Benachrichtigungen (FCM) | Geplant |
| Dokumentenablage pro Mitarbeiter | Geplant |
| Onboarding-Checklisten | Geplant |
| Ankuendigungen (Einweg) | Geplant |
| Lesebestaetigung Chat | Geplant |
| Docker-Deployment | Geplant (Phase 7) |
| PostgreSQL-Migration (Produktion) | Dev nutzt SQLite, Prod-Umstellung konfiguriert |
| DSGVO-Loeschkonzept | Geplant |
| Betriebsrat-Abstimmung | Geplant (Phase 7) |

### Demo-Zugaenge (Entwicklung)

| Benutzername | Rolle | Passwort |
|---|---|---|
| admin | Administrator | dev |
| hr.leitung | Personalabteilung | dev |
| m.mueller | Abteilungsleitung (Innere Medizin) | dev |
| s.schmidt | Teamleitung (Pflege Station 1) | dev |
| t.weber | Mitarbeiter (Pflege Station 1) | dev |
| a.fischer | Mitarbeiter (Chirurgie) | dev |
| k.braun | Mitarbeiter Teilzeit (Verwaltung) | dev |
