# MVA — Mitarbeiterverwaltung fuer Kliniken

**Moderne Personalverwaltung, Zeiterfassung und Dienstplanung — entwickelt fuer deutsche Krankenhaeuser.**

---

## Das Problem

Viele Kliniken planen ihre Dienste noch mit Excel, veralteter Software oder Papier. Die Folgen: Regelverstoesse gegen das Arbeitszeitgesetz, fehlende Transparenz fuer Mitarbeitende und stundenlange manuelle Planungsarbeit. Bestehende Enterprise-Loesungen sind fuer mittlere Haeuser zu teuer und zu komplex.

## Die Loesung

MVA ist eine All-in-One-Plattform fuer Personalverwaltung, Zeiterfassung, Dienstplanung und Teamkommunikation — speziell fuer den deutschen Klinikbetrieb. Modern, bezahlbar und sofort einsatzbereit.

---

## Funktionen

### Zeiterfassung

- **Digitales Stempeln** per Web oder Smartphone — Ein-/Ausstempeln mit einem Klick
- **Automatische Pausenberechnung** nach ArbZG (30 Min. ab 6h, 45 Min. ab 9h)
- **Zuschlagsberechnung** — Nacht (20%), Sonntag (25%), Feiertag (35%), Ueberstunden (30%)
- **Feiertags-Kalender** mit allen gesetzlichen Feiertagen (inkl. bewegliche Feiertage)
- **Monats- und Jahresuebersichten** mit Soll/Ist-Vergleich und Ueberstundenkonto
- **Korrekturantraege** mit Genehmigungsworkflow
- **Monatsabschluss** mit Sperrung und Export an Lohnbuchhaltung (P&I Loga-kompatibel)

### Dienstplanung

- **Jahresmatrix nach Excel-Vorbild** fuer Urlaub, Bereitschaft, Hotline, Schulung, Dienstreise, Teammeeting und weitere Tagescodes
- **Drag-to-plan**: Leitung setzt Codes per Ziehen ueber mehrere Tage und Mitarbeiter
- **Serverseitige Speicherung** mit Audit-Log; mehrere Browser sehen denselben Planstand
- **CSV-Export** fuer Weiterverarbeitung in Excel oder Controlling
- **Visuelle Planungsoberflaeche** — Kalenderansicht mit Drag-and-Drop
- **Schichtvorlagen** mit Farbcodierung (Frueh, Spaet, Nacht, Bereitschaft etc.)
- **Massenplanung** — Mehrere Tage und Mitarbeitende auf einmal zuweisen
- **ArbZG-Validierung in Echtzeit:**
  - Max. 10h pro Tag
  - Max. 48h pro Woche
  - Min. 11h Ruhezeit zwischen Schichten
  - Max. 6 aufeinanderfolgende Arbeitstage
  - Doppelbelegungspruefung
- **Mindestbesetzung** — Personaluntergrenzen pro Schicht, Wochentag und Abteilung definieren und automatisch pruefen
- **Schichttausch-Boerse** — Mitarbeitende koennen Schichten untereinander tauschen (mit automatischer Regelvalidierung)
- **Vertretungsanfragen** — Offene Schichten ausschreiben, Freiwillige melden sich

### Abwesenheitsmanagement

- **Urlaubsantrag** mit digitalem Genehmigungsworkflow
- **Krankmeldung** (automatisch genehmigt), Fortbildung, Sonderurlaub, Freizeitausgleich
- **Urlaubskonto** — Jahresanspruch, genommene und verbleibende Tage auf einen Blick
- **Ueberschneidungspruefung** — Verhindert doppelte Abwesenheiten
- **Arbeitstageberechnung** — Automatisch exkl. Wochenenden und Feiertage

### Personalverwaltung

- **Digitale Personalakte** — Stammdaten, Vertrag, Kontakt, Notfallkontakt
- **Abteilungshierarchie** mit Kostenstellen
- **Qualifikationsverwaltung** mit Ablaufdatum
- **5-stufiges Rollenkonzept:** Administrator, Personalleitung, Abteilungsleitung, Teamleitung, Mitarbeiter
- **Self-Service** — Mitarbeitende pflegen eigene Kontaktdaten, Vorgesetzte genehmigen Antraege

### Kommunikation

- **Integrierter Chat** — Einzel- und Gruppengespraeche in Echtzeit (WebSocket)
- **Tipp-Anzeige** und Gelesen-Status
- **Online-Status** — Sehen wer gerade verfuegbar ist
- **Abteilungs-Rundnachrichten** und Ankuendigungen
- **Spracherkennung** — Nachrichten per Spracheingabe diktieren (Mobile App)

### Berichte und Auswertungen

- **Jahresuebersicht** pro Mitarbeiter (Stunden, Ueberstunden, Abwesenheiten)
- **Abteilungsreport** — Besetzungsgrad, Krankenquote, Ueberstunden
- **Zuschlagsanalyse** — Nacht-, Sonntags- und Feiertagsstunden nach Mitarbeiter
- **Abwesenheitsstatistik** — Trends und Verteilung nach Typ und Monat
- **CSV-Export** — Kompatibel mit P&I Loga und anderen Lohnabrechnungssystemen

### Audit und Compliance

- **Lueckenlose Protokollierung** aller Aenderungen (wer, was, wann)
- **ArbZG-konforme Planung** mit automatischer Regelvalidierung
- **DSGVO-konformes Rollenkonzept** — Jeder sieht nur, was er sehen darf
- **NIS-2-faehig** — Verschluesselung, Zugriffsprotokollierung, On-Premise-Betrieb

---

## Plattformen

| Plattform | Technologie | Einsatz |
|---|---|---|
| **Web-App** | React, TypeScript | Verwaltung, Planung, Berichte — laeuft im Browser |
| **Android-App** | Flutter | Stempeln, Dienstplan einsehen, Chat, Abwesenheiten — fuer alle Mitarbeitenden |
| **API** | REST + WebSocket | Integration in bestehende Systeme (KIS, ERP, Lohnbuchhaltung) |

---

## Technische Eckdaten

| Merkmal | Detail |
|---|---|
| **Backend** | Python 3.12, FastAPI (async) |
| **Datenbank** | PostgreSQL 16 |
| **Cache** | Redis 7 |
| **Deployment** | Docker Compose — ein Befehl, alles laeuft |
| **Authentifizierung** | Active Directory (LDAP) oder lokale Passwoerter (bcrypt) |
| **Schnittstellen** | REST-API, WebSocket, CSV-Export (P&I Loga), LDAP/AD |
| **Sicherheit** | JWT-Token, bcrypt-Hashing, rollenbasierte Zugriffskontrolle, Audit-Log |
| **Betriebsmodell** | On-Premise oder gehostete Loesung — volle Datensouveraenitaet |

---

## Betriebsmodelle

### On-Premise

Die Software laeuft auf Ihrer eigenen Infrastruktur. Sie behalten die volle Kontrolle ueber Ihre Daten — ideal fuer KRITIS-Haeuser und Einrichtungen mit strengen Datenschutzanforderungen.

- Docker Compose auf jedem Linux-Server
- Automatische Installation in unter 30 Minuten
- Active-Directory-Anbindung an Ihr bestehendes Netzwerk

### Gehostete Loesung

Wir betreiben MVA fuer Sie auf deutschen Servern. Sie kuemmern sich um Ihre Mitarbeitenden, wir um die Technik.

- Hosting in Deutschland (EU-DSGVO-konform)
- Automatische Updates und Backups
- SSL-verschluesselter Zugriff

---

## Zielgruppe

- **Krankenhaeuser und Kliniken** mit 200 bis 1.000 Mitarbeitenden
- **Pflegeeinrichtungen** und Rehabilitationskliniken
- **Medizinische Versorgungszentren** mit Schichtbetrieb

---

## Vorteile auf einen Blick

| Was andere bieten | Was MVA anders macht |
|---|---|
| Veraltete Oberflaechen | Moderne, intuitive Benutzeroberflaeche |
| Nur Desktop | Web-App + Android-App fuer alle Mitarbeitenden |
| Separate Chat-Tools | Kommunikation direkt in der Anwendung integriert |
| Intransparente Preise | Klare Preisgestaltung pro Mitarbeiter/Monat |
| Nur Cloud oder nur On-Premise | Beide Modelle verfuegbar — Sie entscheiden |
| Wochen fuer die Einrichtung | Docker-Installation in unter 30 Minuten |
| Regelverstoesse erst im Nachhinein | ArbZG-Validierung in Echtzeit bei der Planung |
| Kein Export | P&I Loga-kompatibel, CSV-Export fuer jede Lohnbuchhaltung |

---

## Kontakt

Interesse an einer Demo oder einem Testbetrieb?

**Andre Stockmann**
E-Mail: andre@astockma.de
Web: https://mva.c3po42.de
