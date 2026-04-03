import { CSSProperties, ReactNode } from 'react';

// ── Inline-Formatting ────────────────────────────────────────────────────────

function renderInline(text: string): ReactNode[] {
  // Erkenne **fett**, *kursiv*, `code`, [text](#anchor)
  const parts: ReactNode[] = [];
  const re = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`|\[([^\]]+)\]\(([^)]+)\))/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    if (m[2]) parts.push(<strong key={key++}>{m[2]}</strong>);
    else if (m[3]) parts.push(<em key={key++}>{m[3]}</em>);
    else if (m[4]) parts.push(<code key={key++} style={styles.inlineCode}>{m[4]}</code>);
    else if (m[5]) {
      const href = m[6];
      parts.push(<a key={key++} href={href} style={styles.link}>{m[5]}</a>);
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

// ── Block-Renderer ───────────────────────────────────────────────────────────

function toAnchor(text: string): string {
  return text.toLowerCase()
    .replace(/[äöüß]/g, (c) => ({ ä: 'ae', ö: 'oe', ü: 'ue', ß: 'ss' }[c] ?? c))
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

interface TocEntry { level: number; text: string; anchor: string }

function parseMarkdown(md: string): { blocks: ReactNode[]; toc: TocEntry[] } {
  const lines = md.split('\n');
  const blocks: ReactNode[] = [];
  const toc: TocEntry[] = [];
  let i = 0;
  let keyCounter = 0;
  const k = () => keyCounter++;

  while (i < lines.length) {
    const line = lines[i];

    // Leere Zeile überspringen
    if (line.trim() === '') { i++; continue; }

    // Horizontale Linie
    if (/^-{3,}$/.test(line.trim())) {
      blocks.push(<hr key={k()} style={styles.hr} />);
      i++;
      continue;
    }

    // Überschriften
    const hMatch = line.match(/^(#{1,3})\s+(.+)/);
    if (hMatch) {
      const level = hMatch[1].length;
      const text = hMatch[2];
      const anchor = toAnchor(text);
      toc.push({ level, text, anchor });
      const Tag = `h${level}` as keyof JSX.IntrinsicElements;
      const hStyle = level === 1 ? styles.h1 : level === 2 ? styles.h2 : styles.h3;
      blocks.push(
        <Tag key={k()} id={anchor} style={hStyle as CSSProperties}>
          {renderInline(text)}
        </Tag>
      );
      i++;
      continue;
    }

    // Screenshot-Platzhalter  [Screenshot: ...]
    const ssMatch = line.match(/^\[Screenshot:\s*(.+)\]$/);
    if (ssMatch) {
      blocks.push(
        <div key={k()} style={styles.screenshot}>
          <span style={styles.screenshotIcon}>📷</span>
          <span style={styles.screenshotText}>{ssMatch[1]}</span>
        </div>
      );
      i++;
      continue;
    }

    // Blockquote
    if (line.startsWith('> ')) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].startsWith('> ')) {
        quoteLines.push(lines[i].slice(2));
        i++;
      }
      blocks.push(
        <blockquote key={k()} style={styles.blockquote}>
          {quoteLines.map((l, idx) => (
            <p key={idx} style={{ margin: idx === 0 ? 0 : '6px 0 0' }}>{renderInline(l)}</p>
          ))}
        </blockquote>
      );
      continue;
    }

    // Tabelle
    if (line.startsWith('|')) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].startsWith('|')) {
        tableLines.push(lines[i]);
        i++;
      }
      const rows = tableLines
        .filter(l => !/^\|[-| :]+\|/.test(l))
        .map(l => l.replace(/^\||\|$/g, '').split('|').map(c => c.trim()));
      if (rows.length > 0) {
        const [header, ...body] = rows;
        blocks.push(
          <div key={k()} style={styles.tableWrapper}>
            <table style={styles.table}>
              <thead>
                <tr>
                  {header.map((cell, ci) => (
                    <th key={ci} style={styles.th}>{renderInline(cell)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {body.map((row, ri) => (
                  <tr key={ri} style={ri % 2 === 1 ? styles.trAlt : undefined}>
                    {row.map((cell, ci) => (
                      <td key={ci} style={styles.td}>{renderInline(cell)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      continue;
    }

    // Geordnete Liste
    if (/^\d+\.\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s/, ''));
        i++;
      }
      blocks.push(
        <ol key={k()} style={styles.ol}>
          {items.map((item, idx) => (
            <li key={idx} style={styles.li}>{renderInline(item)}</li>
          ))}
        </ol>
      );
      continue;
    }

    // Ungeordnete Liste
    if (/^[-*]\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*]\s/, ''));
        i++;
      }
      blocks.push(
        <ul key={k()} style={styles.ul}>
          {items.map((item, idx) => (
            <li key={idx} style={styles.li}>{renderInline(item)}</li>
          ))}
        </ul>
      );
      continue;
    }

    // Normaler Absatz
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].match(/^#{1,3}\s/) &&
      !lines[i].startsWith('|') &&
      !lines[i].startsWith('> ') &&
      !/^[-*]\s/.test(lines[i]) &&
      !/^\d+\.\s/.test(lines[i]) &&
      !/^-{3,}$/.test(lines[i].trim()) &&
      !lines[i].match(/^\[Screenshot:/)
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    if (paraLines.length > 0) {
      blocks.push(
        <p key={k()} style={styles.p}>
          {paraLines.flatMap((l, idx) => idx < paraLines.length - 1
            ? [...renderInline(l), <br key={`br-${idx}`} />]
            : renderInline(l)
          )}
        </p>
      );
    }
  }

  return { blocks, toc };
}

// ── Stile ────────────────────────────────────────────────────────────────────

const styles = {
  h1: {
    fontSize: 32, fontWeight: 800, color: '#1e293b',
    margin: '0 0 8px', lineHeight: 1.3,
  } as CSSProperties,
  h2: {
    fontSize: 22, fontWeight: 700, color: '#1e293b',
    margin: '40px 0 12px', paddingBottom: 8,
    borderBottom: '2px solid #e2e8f0',
  } as CSSProperties,
  h3: {
    fontSize: 16, fontWeight: 700, color: '#334155',
    margin: '28px 0 8px',
  } as CSSProperties,
  p: {
    fontSize: 15, color: '#374151', lineHeight: 1.75, margin: '0 0 12px',
  } as CSSProperties,
  hr: {
    border: 'none', borderTop: '1px solid #e2e8f0', margin: '32px 0',
  } as CSSProperties,
  blockquote: {
    margin: '16px 0', padding: '14px 20px',
    background: '#f0f9ff', borderLeft: '4px solid #3b82f6',
    borderRadius: '0 8px 8px 0',
    fontSize: 14, color: '#475569', lineHeight: 1.7,
  } as CSSProperties,
  screenshot: {
    display: 'flex', alignItems: 'center', gap: 12,
    background: '#f1f5f9', border: '1px dashed #cbd5e1',
    borderRadius: 8, padding: '16px 20px', margin: '16px 0',
  } as CSSProperties,
  screenshotIcon: {
    fontSize: 22, flexShrink: 0,
  } as CSSProperties,
  screenshotText: {
    fontSize: 13, color: '#64748b', fontStyle: 'italic',
  } as CSSProperties,
  tableWrapper: {
    overflowX: 'auto', margin: '16px 0',
  } as CSSProperties,
  table: {
    width: '100%', borderCollapse: 'collapse', fontSize: 14,
  } as CSSProperties,
  th: {
    background: '#1e293b', color: '#fff', padding: '10px 14px',
    textAlign: 'left', fontWeight: 600, whiteSpace: 'nowrap',
  } as CSSProperties,
  td: {
    padding: '9px 14px', borderBottom: '1px solid #e2e8f0',
    color: '#374151', verticalAlign: 'top',
  } as CSSProperties,
  trAlt: {
    background: '#f8fafc',
  } as CSSProperties,
  ol: {
    margin: '8px 0 16px', paddingLeft: 24,
  } as CSSProperties,
  ul: {
    margin: '8px 0 16px', paddingLeft: 24,
  } as CSSProperties,
  li: {
    fontSize: 15, color: '#374151', lineHeight: 1.7, marginBottom: 4,
  } as CSSProperties,
  inlineCode: {
    background: '#f1f5f9', borderRadius: 4, padding: '2px 6px',
    fontFamily: 'monospace', fontSize: '0.9em', color: '#0f172a',
  } as CSSProperties,
  link: {
    color: '#3b82f6', textDecoration: 'none',
  } as CSSProperties,
};

// ── Benutzerhandbuch-Inhalt ──────────────────────────────────────────────────

const HANDBUCH_MD = `# Benutzerhandbuch — Mitarbeiterverwaltung (MVA)
### Ilm-Kreis-Kliniken

**Version:** 1.0 · **Stand:** April 2026
**Zielgruppe:** Alle Mitarbeiterinnen und Mitarbeiter der Ilm-Kreis-Kliniken

---

## 1. Erste Schritte

### 1.1 Anmelden im Browser (Web)

1. Öffnen Sie Ihren Browser (z. B. Chrome, Firefox, Edge).
2. Geben Sie die Adresse **https://mva.c3po42.de** ein und drücken Sie Enter.
3. Die Anmeldeseite erscheint mit dem Logo der Ilm-Kreis-Kliniken.
4. Geben Sie Ihren **Benutzernamen** ein (z. B. \`m.mustermann\`).
5. Geben Sie Ihr **Passwort** ein.
6. Klicken Sie auf den blauen Button **„Anmelden"**.

[Screenshot: Anmeldeseite mit Benutzername- und Passwortfeld]

> **Hinweis:** Ihr Benutzername entspricht Ihrem Windows-Anmeldekonto im Krankenhaus. Wenden Sie sich bei Fragen an die IT-Abteilung.

### 1.2 Anmelden in der Android-App

1. Installieren Sie die App **„MVA Ilm-Kreis-Kliniken"** auf Ihrem Android-Gerät.
2. Öffnen Sie die App.
3. Geben Sie Ihren Benutzernamen und Ihr Passwort ein.
4. Tippen Sie auf **„Anmelden"**.

[Screenshot: App-Anmeldebildschirm]

### 1.3 Passwort zurücksetzen

Das Passwort wird über Ihr Windows-Konto im Krankenhaus verwaltet. Eine Selbstzurücksetzung ist in der Anwendung derzeit nicht möglich.

**Bitte wenden Sie sich bei einem vergessenen Passwort direkt an:**
- Die IT-Abteilung Ihres Standorts, oder
- Ihren Vorgesetzten, der die IT informieren kann.

### 1.4 Abmelden

Um sich sicher abzumelden:

1. Klicken Sie links unten in der dunklen Seitenleiste auf den roten Link **„Abmelden"** (mit dem Pfeil-Symbol).
2. Sie werden automatisch zur Anmeldeseite weitergeleitet.

> **Tipp:** Melden Sie sich immer ab, wenn Sie einen gemeinsam genutzten Computer verwenden.

### 1.5 Die Benutzeroberfläche kennenlernen

Nach der Anmeldung sehen Sie:

- **Linke Seitenleiste (dunkel):** Hauptnavigation mit allen Bereichen wie Zeiterfassung, Dienstplan, Abwesenheiten usw.
- **Hauptbereich (hell):** Der Inhalt des jeweils ausgewählten Bereichs.
- **Unten in der Seitenleiste:** Ihr Name, Ihre Rolle und der Abmelden-Button.

[Screenshot: Hauptansicht nach dem Login mit beschrifteter Seitenleiste]

---

## 2. Zeiterfassung

### 2.1 Einstempeln (Kommen)

1. Klicken Sie in der linken Seitenleiste auf **„Zeiterfassung"**.
2. Sie sehen den Bereich mit dem **grünen Button „Einstempeln"**.
3. Klicken Sie auf diesen Button.
4. Die Ansicht wechselt: Sie sehen nun in grün **„Eingestempelt seit HH:MM"** und die bisherige Arbeitszeit.

[Screenshot: Zeiterfassung — grüner „Einstempeln"-Button]

> **Hinweis:** Das Einstempeln ist nur möglich, wenn Sie sich noch nicht eingestempelt haben. Sollte der Button fehlen, sind Sie bereits eingestempelt.

### 2.2 Ausstempeln (Gehen)

1. Gehen Sie zu **„Zeiterfassung"**.
2. Neben Ihrer Arbeitszeit sehen Sie ein Feld **„Pause (Min)"**.
3. Tragen Sie die Anzahl Ihrer Pausenminuten ein (Standard: 30 Minuten).
4. Klicken Sie auf den roten Button **„Ausstempeln"**.

[Screenshot: Zeiterfassung — rotes „Ausstempeln"-Button mit Pausen-Feld]

> **Wichtig:** Geben Sie die Pause korrekt ein. Die Pausenzeiten werden automatisch nach dem Arbeitszeitgesetz (ArbZG) geprüft.

### 2.3 Pausenregelung nach ArbZG

Die Anwendung berechnet Pausen automatisch nach gesetzlichen Vorgaben:

| Arbeitszeit | Mindestpause |
|---|---|
| Mehr als 6 Stunden | 30 Minuten |
| Mehr als 9 Stunden | 45 Minuten |

Sie müssen die tatsächliche Pausenzeit beim Ausstempeln eintragen. Die Nettostunden (abzüglich Pausen) werden automatisch berechnet und in der Übersicht angezeigt.

### 2.4 Tagesübersicht einsehen

Auf der Seite „Zeiterfassung" sehen Sie direkt unterhalb des Stempel-Bereichs:

- **Heute — X.Xh (Pause: XX Min):** Ihre heutige Gesamtarbeitszeit mit blauem Fortschrittsbalken (8-Stunden-Ziel).
- **Heutige Einträge:** Eine Tabelle mit allen Ein- und Ausstempelungen des Tages, inkl. Pausen, Nettozeit, Schichttyp und Zuschlägen (z. B. Nachtzuschlag).

[Screenshot: Tagesübersicht mit Tabelle der heutigen Einträge]

### 2.5 Zeitkorrektur beantragen

Haben Sie vergessen einzustempeln oder ist ein Fehler aufgetreten? Wenden Sie sich an Ihren **Abteilungsleiter** oder die **Personalabteilung (HR)**.

Diese können im System eine Zeitkorrektur vornehmen. Halten Sie folgende Informationen bereit:
- Datum
- Uhrzeitkorrektur (Kommen / Gehen)
- Grund der Korrektur

> **Tipp:** Melden Sie Korrekturen möglichst zeitnah — spätestens bis zum Ende des laufenden Monats.

---

## 3. Abwesenheiten

### 3.1 Urlaubsantrag stellen

1. Klicken Sie in der Seitenleiste auf **„Abwesenheiten"**.
2. Oben sehen Sie Ihr **Urlaubskonto** (Anspruch, genommen, beantragt, verbleibend).
3. Klicken Sie rechts auf den blauen Button **„Neuer Antrag"**.
4. Es erscheint ein Formular. Füllen Sie es aus:
- **Typ:** Wählen Sie „Urlaub" aus dem Dropdown-Menü.
- **Von:** Geben Sie das Startdatum ein.
- **Bis:** Geben Sie das Enddatum ein.
- **Anmerkung:** Optional — z. B. „Familienurlaub".
5. Klicken Sie auf den grünen Button **„Absenden"**.

[Screenshot: Abwesenheits-Formular mit ausgefüllten Feldern]

> Ihr Antrag erhält den Status **„Beantragt"** (gelb). Sobald der Abteilungsleiter ihn genehmigt, wechselt er zu **„Genehmigt"** (grün).

### 3.2 Urlaubskonto einsehen (Resturlaub)

Ihr Urlaubskonto wird oben auf der Seite „Abwesenheiten" immer aktuell angezeigt:

- **Anspruch [Jahr]:** Ihr gesamter Jahresurlaub
- **Genommen:** Bereits genutzter Urlaub
- **Beantragt:** Urlaubstage in Bearbeitung
- **Verbleibend:** Ihr Resturlaub (grün)

[Screenshot: Urlaubskonto-Übersicht]

### 3.3 Krankmeldung einreichen

1. Gehen Sie zu **„Abwesenheiten"** → **„Neuer Antrag"**.
2. Wählen Sie als Typ **„Krankheit"**.
3. Tragen Sie das erste und das voraussichtlich letzte Krankheitsdatum ein.
4. Klicken Sie auf **„Absenden"**.

> **Hinweis:** Die Krankmeldung dient der Dokumentation im System. Die ärztliche Bescheinigung geben Sie bitte weiterhin wie gewohnt in der Personalabteilung ab.

### 3.4 Fortbildung oder Sonderurlaub beantragen

Das Verfahren ist dasselbe wie beim Urlaubsantrag:

1. **„Neuer Antrag"** klicken.
2. Als Typ **„Fortbildung"** oder **„Sonderurlaub"** wählen.
3. Datum eingeben und ggf. eine Anmerkung hinzufügen (z. B. Name der Fortbildung).
4. **„Absenden"** klicken.

### 3.5 Status eines Antrags prüfen

In der Tabelle unter „Abwesenheiten" sehen Sie alle Ihre Anträge mit ihrem aktuellen Status:

| Status | Farbe | Bedeutung |
|---|---|---|
| Beantragt | Gelb | Wartet auf Genehmigung |
| Genehmigt | Grün | Vom Vorgesetzten genehmigt |
| Abgelehnt | Rot | Vom Vorgesetzten abgelehnt |
| Storniert | Grau | Von Ihnen zurückgezogen |

[Screenshot: Abwesenheitsliste mit farbigen Status-Badges]

---

## 4. Dienstplan

### 4.1 Eigenen Dienstplan einsehen

1. Klicken Sie in der Seitenleiste auf **„Mein Dienstplan"**.
2. Oben sehen Sie eine Monatsauswahl (Standard: aktueller Monat).
3. Wählen Sie bei Bedarf einen anderen Monat aus.
4. Der Kalender zeigt alle Ihre geplanten Schichten für den gewählten Monat.

[Screenshot: Dienstplan-Kalender mit eingetragenen Schichten]

- **Heute** ist mit einem blauen Rahmen hervorgehoben.
- **Wochenendtage** (Samstag/Sonntag) haben einen hellgrauen Hintergrund.

### 4.2 Schichten verstehen

Jede Schicht wird mit einem farbigen Kürzel angezeigt:

| Farbe | Kürzel | Bedeutung |
|---|---|---|
| Grün | F | Frühschicht |
| Gelb | S | Spätschicht |
| Blau/Lila | N | Nachtschicht |
| Grau | — | Sonstige Schicht |

Unterhalb des Kalenders finden Sie die **Schichtliste** mit genauen Uhrzeiten (z. B. „06:00 – 14:00") und dem Status (Bestätigt / offen).

> **Hinweis:** Der Dienstplan wird von Ihrer Abteilungsleitung erstellt und veröffentlicht. Erst nach der Veröffentlichung ist er für Sie sichtbar.

### 4.3 Schichttausch beantragen

Ein direkter Schichttausch ist über das System noch nicht möglich. Sprechen Sie Ihren Wunsch für einen Tausch direkt mit Ihrer Abteilungsleitung ab oder schreiben Sie ihr eine Nachricht im **Chat** (siehe Kapitel 5).

### 4.4 Vertretung anbieten / Einspringen

Wenn Sie bei einer freien Schicht einspringen können, wenden Sie sich direkt an Ihre Abteilungsleitung — persönlich oder über den **Chat** in der Anwendung. Teilen Sie mit:
- Das Datum der Schicht
- Die Schicht (z. B. Frühschicht)
- Ihre Verfügbarkeit

---

## 5. Nachrichten / Chat

### 5.1 Einzelnachricht senden

1. Klicken Sie in der Seitenleiste auf **„Nachrichten"**.
2. Links sehen Sie die Liste Ihrer vorhandenen Gespräche.
3. Um ein neues Gespräch zu starten, klicken Sie auf den blauen **„+"-Button** oben rechts in der Nachrichtenliste.
4. Eine Mitarbeiterliste erscheint. Suchen Sie nach dem Namen (Suchfeld oben).
5. Klicken Sie auf den gewünschten Mitarbeiter.
6. Das Chatfenster öffnet sich rechts.
7. Schreiben Sie Ihre Nachricht in das Textfeld unten und drücken Sie **Enter** oder klicken Sie auf den blauen **Senden-Button** (Pfeil).

[Screenshot: Chat-Ansicht mit geöffnetem Gespräch und Texteingabe]

### 5.2 Bestehende Gespräche öffnen

In der linken Spalte sehen Sie alle Ihre Gespräche. Gespräche mit ungelesenen Nachrichten werden **fett** angezeigt und zeigen eine blaue Zahl (Anzahl ungelesener Nachrichten).

Klicken Sie auf ein Gespräch, um es zu öffnen.

### 5.3 Mitarbeiter nach Abteilung suchen

Beim Starten eines neuen Chats (Schritt 3–4 oben) sind die Mitarbeiter nach **Abteilungen** gruppiert. Klicken Sie auf den Abteilungsnamen, um die Liste auf- oder zuzuklappen.

Ein grüner Punkt neben dem Namen bedeutet: Der Mitarbeiter ist gerade online.

[Screenshot: Mitarbeiterliste nach Abteilungen gruppiert]

### 5.4 Gruppenchat / Abteilungs-Chat

Bestehende Gruppengespräche (z. B. der Abteilungs-Chat) erscheinen ebenfalls in Ihrer Gesprächsliste. Klicken Sie darauf, um am Gespräch teilzunehmen.

> **Hinweis:** Neue Gruppenkonversationen werden derzeit von der Abteilungsleitung oder der IT eingerichtet.

---

## 6. Für Abteilungsleiter

Dieser Abschnitt richtet sich an Mitarbeiterinnen und Mitarbeiter mit der Rolle **Abteilungsleitung** oder **Teamleitung**.

### 6.1 Mitarbeiter der Abteilung einsehen

1. Klicken Sie in der Seitenleiste auf **„Mitarbeiter"**.
2. Die Liste zeigt alle Mitarbeiter, nach Abteilung gruppiert.
3. Nutzen Sie das Suchfeld oben (nach Name, Personalnummer oder E-Mail).
4. Mit dem Abteilungs-Dropdown können Sie die Ansicht auf eine bestimmte Abteilung einschränken.
5. Klicken Sie auf eine Zeile, um das Profil eines Mitarbeiters zu öffnen.

[Screenshot: Mitarbeiterliste mit Suchfeld und Abteilungsfilter]

### 6.2 Urlaubsanträge genehmigen oder ablehnen

1. Klicken Sie auf **„Abwesenheiten"**.
2. Als Abteilungsleiter sehen Sie oben zwei Reiter: **„Meine Abwesenheiten"** und **„Offene Anträge (X)"**.
3. Klicken Sie auf **„Offene Anträge"**.
4. Die Tabelle zeigt alle noch nicht bearbeiteten Anträge Ihrer Mitarbeiter.
5. Pro Antrag sehen Sie zwei Buttons:
- Grüner **Haken-Button**: Antrag genehmigen
- Roter **X-Button**: Antrag ablehnen
6. Klicken Sie den entsprechenden Button.

[Screenshot: Offene Anträge mit grünem Haken und rotem X-Button]

### 6.3 Zeitkorrekturen prüfen

Zeitkorrekturen werden von HR oder Admin direkt im System vorgenommen. Als Abteilungsleiter können Sie die Zeiteinträge Ihrer Mitarbeiter über die Auswertungen (HR-Zugang erforderlich) einsehen oder bei Fragen die Personalabteilung kontaktieren.

### 6.4 Dienstplan erstellen und veröffentlichen

1. Klicken Sie in der Seitenleiste auf **„Dienstplanung"**.
2. Klicken Sie oben rechts auf **„Neuer Dienstplan"**.
3. Im Dialog wählen Sie:
- **Abteilung** (Dropdown)
- **Jahr** und **Monat**
4. Klicken Sie auf **„Erstellen"**.

Der neue Plan erscheint mit dem Status **„Entwurf"** in der Liste.

**Schichten einplanen:**

1. Wählen Sie in der Werkzeugleiste ein Schicht-Kürzel (z. B. „F" für Frühschicht).
2. Klicken Sie in der Tabelle auf **„Anzeigen"** beim gewünschten Plan.
3. Der Kalender zeigt alle Mitarbeiter und alle Tage des Monats.
4. **Ziehen** Sie mit der Maus über die gewünschten Zellen (Mitarbeiter × Tag), um Schichten zuzuweisen.
5. Zum Löschen einer Schicht wählen Sie den **„Radierer"** in der Werkzeugleiste und ziehen über die betreffenden Zellen.

**Dienstplan veröffentlichen:**

1. Klicken Sie in der Planliste auf den grünen Button **„Veröffentlichen"**.
2. Der Status wechselt auf **„Veröffentlicht"** — ab sofort sehen alle Mitarbeiter der Abteilung ihren Dienstplan.

[Screenshot: Dienstplanung mit Werkzeugleiste und Kalender-Raster]

> **Hinweis:** Veröffentlichte Pläne können nicht mehr direkt bearbeitet werden. Kontaktieren Sie bei Bedarf die IT.

### 6.5 Besetzungsübersicht prüfen

In der Kalenderansicht eines Dienstplans sehen Sie auf einen Blick, welche Mitarbeiter an welchem Tag welche Schicht haben. Tage ohne Eintrag (grauer Punkt) sind ungeplant.

---

## 7. Für HR und Administration

Dieser Abschnitt richtet sich an Mitarbeiterinnen und Mitarbeiter mit der Rolle **HR** oder **Administrator**.

### 7.1 Neuen Mitarbeiter anlegen

1. Klicken Sie auf **„Mitarbeiter"** in der Seitenleiste.
2. Klicken Sie oben rechts auf den Button **„Neuer Mitarbeiter"** (falls sichtbar, je nach Berechtigung).
3. Füllen Sie das Formular mit den Stammdaten aus:
- Vorname, Nachname
- Personalnummer
- E-Mail-Adresse
- Abteilung, Rolle, Beschäftigungsart
- Eintrittsdatum, Wochenstunden, Urlaubsanspruch
4. Klicken Sie auf **„Speichern"**.

> Der neue Mitarbeiter kann sich mit seinem Windows-Benutzernamen anmelden, sobald das Konto im Active Directory angelegt ist.

### 7.2 Mitarbeiter deaktivieren

1. Klicken Sie auf **„Mitarbeiter"** und öffnen Sie das Profil des betreffenden Mitarbeiters (Klick auf die Zeile).
2. Klicken Sie auf den Button **„Bearbeiten"** (Stift-Symbol).
3. Setzen Sie den Schalter **„Aktiv"** auf inaktiv.
4. Klicken Sie auf **„Speichern"**.

Der Mitarbeiter erscheint danach mit einem roten **„Inaktiv"**-Badge und kann sich nicht mehr anmelden.

[Screenshot: Mitarbeiterprofil mit Bearbeiten-Button]

### 7.3 Monatsabschluss durchführen

1. Klicken Sie in der Seitenleiste auf **„Monatsabschluss"**.
2. Wählen Sie das gewünschte **Jahr** und den **Monat** aus.
3. Prüfen Sie die angezeigten Zeiteinträge auf Vollständigkeit.
4. Klicken Sie auf **„Abschluss durchführen"**, um den Monat zu sperren.

> Nach dem Abschluss können Zeiteinträge des betreffenden Monats nicht mehr verändert werden. Stellen Sie sicher, dass alle Korrekturen vorher eingetragen wurden.

[Screenshot: Monatsabschluss-Seite mit Monatsauswahl und Abschluss-Button]

### 7.4 CSV-Export für die Lohnabrechnung (LOGA)

1. Klicken Sie auf **„Auswertungen"** in der Seitenleiste.
2. Wählen Sie das gewünschte **Jahr** und den **Monat** aus.
3. Klicken Sie auf den lila Button **„CSV-Export"**.
4. Die Datei wird automatisch heruntergeladen (Name: \`report_JJJJ_MM.csv\`).
5. Importieren Sie diese Datei in Ihr Lohnabrechnungssystem (LOGA).

[Screenshot: Auswertungen-Seite mit CSV-Export-Button]

### 7.5 Berichte und Auswertungen

Unter **„Auswertungen"** stehen vier Auswertungstypen zur Verfügung:

| Reiter | Inhalt |
|---|---|
| Jahresübersicht | Soll/Ist-Stunden, Überstunden, Krank- und Urlaubstage je Mitarbeiter |
| Abteilungen | Arbeitsstunden und Kranktage je Abteilung (pro Monat) |
| Zuschläge | Nacht-, Sonntags-, Feiertags- und Samstagszuschläge |
| Abwesenheiten | Abwesenheitstage nach Typ und Monat, Top-Kranktage |

**Auswertung laden:**

1. Wählen Sie den gewünschten Reiter.
2. Stellen Sie Jahr (und ggf. Monat) ein.
3. Klicken Sie auf **„Laden"**.

[Screenshot: Auswertungen — Jahresübersicht mit Tabelle und Kennzahlen]

---

## Häufige Fragen

**Ich kann mich nicht anmelden — was tun?**
Prüfen Sie, ob Ihr Benutzername korrekt eingetragen ist (kein „@" oder Domain-Anteil). Wenden Sie sich bei anhaltenden Problemen an die IT-Abteilung.

**Ich habe vergessen einzustempeln — was jetzt?**
Wenden Sie sich an Ihre Abteilungsleitung oder die Personalabteilung. Diese können eine Zeitkorrektur eintragen.

**Mein Antrag hat den Status „Abgelehnt" — warum?**
Sprechen Sie direkt mit Ihrer Abteilungsleitung. Im System gibt es derzeit kein separates Kommentarfeld für Ablehnungsgründe.

**Ich sehe keinen Dienstplan für den aktuellen Monat.**
Der Dienstplan wurde möglicherweise noch nicht veröffentlicht. Sprechen Sie Ihre Abteilungsleitung an.

**Wie erkenne ich, ob meine Nachricht angekommen ist?**
Nachrichten, die Sie senden, erscheinen sofort in Ihrer Ansicht auf der rechten Seite (blauer Hintergrund). Eine separate Lesebestätigung ist derzeit nicht verfügbar.

---

*Bei weiteren Fragen wenden Sie sich an die IT-Abteilung der Ilm-Kreis-Kliniken.*
*Dieses Handbuch wird regelmäßig aktualisiert.*`;

// ── Inhaltsverzeichnis-Komponente ────────────────────────────────────────────

function Toc({ entries }: { entries: TocEntry[] }) {
  const chapters = entries.filter(e => e.level === 2);
  if (chapters.length === 0) return null;
  return (
    <nav style={{
      background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 10,
      padding: '20px 24px', marginBottom: 40,
    }}>
      <div style={{ fontWeight: 700, fontSize: 14, color: '#1e293b', marginBottom: 12 }}>
        Inhaltsverzeichnis
      </div>
      <ol style={{ margin: 0, paddingLeft: 20 }}>
        {chapters.map((entry, idx) => (
          <li key={idx} style={{ marginBottom: 6 }}>
            <a
              href={`#${entry.anchor}`}
              style={{ color: '#3b82f6', textDecoration: 'none', fontSize: 14 }}
            >
              {entry.text}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

// ── Haupt-Komponente ─────────────────────────────────────────────────────────

export default function Handbuch() {
  const { blocks, toc } = parseMarkdown(HANDBUCH_MD);

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', color: '#1e293b', minHeight: '100vh' }}>

      {/* Header */}
      <header style={{
        background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
        padding: '20px 40px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 12,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <img src="/logo-ikk.png" alt="Ilm-Kreis-Kliniken" style={{ width: 48, height: 48, objectFit: 'contain' }} />
          <div>
            <div style={{ color: '#fff', fontSize: 18, fontWeight: 700 }}>Mitarbeiterverwaltung</div>
            <div style={{ color: '#94a3b8', fontSize: 13 }}>Benutzerhandbuch</div>
          </div>
        </div>
        <nav style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <a
            href="/produkt"
            style={{
              color: '#94a3b8', padding: '8px 14px',
              textDecoration: 'none', fontSize: 14, fontWeight: 500, borderRadius: 6,
            }}
          >
            ← Zurück zur Übersicht
          </a>
          <a
            href="/login"
            style={{
              background: '#3b82f6', color: '#fff', padding: '8px 20px',
              borderRadius: 6, textDecoration: 'none', fontSize: 14, fontWeight: 600,
            }}
          >
            Anmelden
          </a>
        </nav>
      </header>

      {/* Hero-Banner */}
      <div style={{
        background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
        padding: '40px 40px 48px', textAlign: 'center', color: '#fff',
        borderBottom: '4px solid #3b82f6',
      }}>
        <h1 style={{ fontSize: 32, fontWeight: 800, margin: '0 0 8px' }}>
          Benutzerhandbuch
        </h1>
        <p style={{ color: '#94a3b8', fontSize: 15, margin: '0 0 24px' }}>
          Ilm-Kreis-Kliniken · Mitarbeiterverwaltung (MVA) · Version 1.0 · Stand April 2026
        </p>
        <a
          href="/produkt/benutzerhandbuch.pdf"
          download
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: '#3b82f6', color: '#fff', padding: '10px 24px',
            borderRadius: 8, textDecoration: 'none', fontSize: 14, fontWeight: 600,
          }}
        >
          <span>⬇</span> Als PDF herunterladen
        </a>
      </div>

      {/* Hauptinhalt */}
      <main style={{ maxWidth: 860, margin: '0 auto', padding: '48px 24px 80px' }}>
        <Toc entries={toc} />
        {blocks}
      </main>

      {/* Footer */}
      <footer style={{
        background: '#0f172a', color: '#64748b', textAlign: 'center',
        padding: '24px 40px', fontSize: 13,
      }}>
        © {new Date().getFullYear()} Ilm-Kreis-Kliniken · Mitarbeiterverwaltung · Alle Rechte vorbehalten
        {' · '}
        <a href="/produkt" style={{ color: '#64748b', textDecoration: 'underline' }}>Produktseite</a>
      </footer>
    </div>
  );
}
