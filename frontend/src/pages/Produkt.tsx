export default function Produkt() {
  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', color: '#1e293b' }}>

      {/* Header */}
      <header style={{
        background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
        padding: '20px 40px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 12,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <img src="/logo-ikk.png" alt="Ilm-Kreis-Kliniken" style={{ width: 48, height: 48, objectFit: 'contain' }} />
          <span style={{ color: '#fff', fontSize: 20, fontWeight: 700 }}>Mitarbeiterverwaltung</span>
        </div>
        <nav style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <a
            href="#funktionen"
            style={{
              color: '#94a3b8', padding: '8px 14px',
              textDecoration: 'none', fontSize: 14, fontWeight: 500, borderRadius: 6,
            }}
          >
            Funktionen
          </a>
          <a
            href="#preise"
            style={{
              color: '#94a3b8', padding: '8px 14px',
              textDecoration: 'none', fontSize: 14, fontWeight: 500, borderRadius: 6,
            }}
          >
            Preise
          </a>
          <a
            href="/produkt/handbuch"
            style={{
              color: '#94a3b8', padding: '8px 14px',
              textDecoration: 'none', fontSize: 14, fontWeight: 500, borderRadius: 6,
            }}
          >
            Handbuch
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

      {/* Hero */}
      <section style={{
        background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
        padding: '80px 40px', textAlign: 'center', color: '#fff',
      }}>
        <h1 style={{ fontSize: 40, fontWeight: 800, margin: '0 0 16px' }}>
          Mitarbeiterverwaltung
        </h1>
        <p style={{ fontSize: 20, color: '#94a3b8', maxWidth: 600, margin: '0 auto 32px' }}>
          Die digitale Lösung für Personalverwaltung, Dienstplanung und Zeiterfassung
          in den Ilm-Kreis-Kliniken.
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <a
            href="/login"
            style={{
              background: '#3b82f6', color: '#fff', padding: '14px 36px',
              borderRadius: 8, textDecoration: 'none', fontSize: 16, fontWeight: 700,
              display: 'inline-block',
            }}
          >
            Jetzt einloggen
          </a>
          <a
            href="/produkt/handbuch"
            style={{
              background: 'transparent', color: '#fff', padding: '14px 36px',
              borderRadius: 8, textDecoration: 'none', fontSize: 16, fontWeight: 600,
              display: 'inline-block', border: '2px solid #475569',
            }}
          >
            Benutzerhandbuch
          </a>
        </div>
      </section>

      {/* Features */}
      <section id="funktionen" style={{ padding: '72px 40px', background: '#f8fafc' }}>
        <h2 style={{ textAlign: 'center', fontSize: 28, fontWeight: 700, marginBottom: 48 }}>
          Funktionen im Überblick
        </h2>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 24, maxWidth: 1100, margin: '0 auto',
        }}>
          {[
            {
              icon: '🕐',
              title: 'Zeiterfassung',
              desc: 'Arbeitszeiten digital erfassen, Überstunden automatisch berechnen und Korrekturen beantragen.',
            },
            {
              icon: '📅',
              title: 'Abwesenheitsverwaltung',
              desc: 'Urlaub, Krankmeldungen und sonstige Abwesenheiten übersichtlich verwalten und genehmigen.',
            },
            {
              icon: '📋',
              title: 'Dienstplanung',
              desc: 'Schichtpläne erstellen, Schichttausch ermöglichen und Besetzungsengpässe frühzeitig erkennen.',
            },
            {
              icon: '👥',
              title: 'Personalverwaltung',
              desc: 'Mitarbeiterdaten pflegen, Qualifikationen hinterlegen und Abteilungen organisieren.',
            },
            {
              icon: '💬',
              title: 'Interner Chat',
              desc: 'Direkte Kommunikation zwischen Mitarbeitern und Teams – sicher und ohne externe Dienste.',
            },
            {
              icon: '📊',
              title: 'Auswertungen',
              desc: 'Überstundenberichte, Abwesenheitsstatistiken und Jahresübersichten für das HR-Team.',
            },
          ].map((f) => (
            <div key={f.title} style={{
              background: '#fff', borderRadius: 10, padding: '28px 24px',
              boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
            }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>{f.icon}</div>
              <h3 style={{ fontSize: 17, fontWeight: 700, margin: '0 0 8px' }}>{f.title}</h3>
              <p style={{ fontSize: 14, color: '#64748b', margin: 0, lineHeight: 1.6 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Vorteile */}
      <section style={{ padding: '72px 40px', background: '#fff' }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          <h2 style={{ fontSize: 28, fontWeight: 700, marginBottom: 32, textAlign: 'center' }}>
            Ihre Vorteile
          </h2>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {[
              'Vollständig browserbasiert – kein lokales Programm notwendig',
              'Rollenbasierte Zugriffssteuerung für Mitarbeiter, Schichtleiter und HR',
              'Mobil optimiert für den Einsatz auf Smartphones und Tablets',
              'Sichere Datenhaltung auf eigenen Servern der Ilm-Kreis-Kliniken',
              'Monatliche Abschlüsse und Exportfunktionen für die Lohnbuchhaltung',
            ].map((v) => (
              <li key={v} style={{
                display: 'flex', alignItems: 'flex-start', gap: 12,
                padding: '12px 0', borderBottom: '1px solid #f1f5f9', fontSize: 15, color: '#374151',
              }}>
                <span style={{ color: '#22c55e', fontWeight: 700, marginTop: 1 }}>✓</span>
                {v}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Preise */}
      <section id="preise" style={{ padding: '72px 40px', background: '#f8fafc' }}>
        <div style={{ maxWidth: 800, margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ fontSize: 28, fontWeight: 700, marginBottom: 16 }}>Preise</h2>
          <p style={{ fontSize: 15, color: '#64748b', marginBottom: 32 }}>
            Die Mitarbeiterverwaltung wird intern betrieben und steht allen Mitarbeitenden der
            Ilm-Kreis-Kliniken kostenfrei zur Verfügung.
          </p>
          <div style={{
            background: '#fff', borderRadius: 12, padding: '40px 32px',
            boxShadow: '0 2px 20px rgba(0,0,0,0.08)', display: 'inline-block', minWidth: 280,
          }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#6366f1', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
              Intern
            </div>
            <div style={{ fontSize: 40, fontWeight: 800, color: '#1e293b', marginBottom: 4 }}>Kostenlos</div>
            <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 24 }}>für alle Mitarbeitenden</div>
            <a href="/login" style={{
              display: 'block', background: '#3b82f6', color: '#fff',
              padding: '12px 0', borderRadius: 8, textDecoration: 'none',
              fontSize: 15, fontWeight: 600, textAlign: 'center',
            }}>
              Jetzt anmelden
            </a>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{
        background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
        padding: '64px 40px', textAlign: 'center', color: '#fff',
      }}>
        <h2 style={{ fontSize: 28, fontWeight: 700, margin: '0 0 16px' }}>
          Bereit zum Loslegen?
        </h2>
        <p style={{ color: '#94a3b8', fontSize: 16, margin: '0 0 28px' }}>
          Melden Sie sich mit Ihren Zugangsdaten an und verwalten Sie alles an einem Ort.
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <a
            href="/login"
            style={{
              background: '#3b82f6', color: '#fff', padding: '14px 36px',
              borderRadius: 8, textDecoration: 'none', fontSize: 16, fontWeight: 700,
              display: 'inline-block',
            }}
          >
            Zur Anmeldung
          </a>
          <a
            href="/produkt/handbuch"
            style={{
              background: 'transparent', color: '#94a3b8', padding: '14px 36px',
              borderRadius: 8, textDecoration: 'none', fontSize: 16, fontWeight: 600,
              display: 'inline-block', border: '2px solid #475569',
            }}
          >
            Benutzerhandbuch lesen
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer style={{
        background: '#0f172a', color: '#64748b', textAlign: 'center',
        padding: '24px 40px', fontSize: 13,
      }}>
        © {new Date().getFullYear()} Ilm-Kreis-Kliniken · Mitarbeiterverwaltung · Alle Rechte vorbehalten
        {' · '}
        <a href="/produkt/handbuch" style={{ color: '#64748b', textDecoration: 'underline' }}>Handbuch</a>
      </footer>

    </div>
  );
}
