import { useState } from 'react';
import Card, { Badge } from '../components/Card';
import { getMonthlyOverview, closeMonth, exportLoga } from '../services/api';

export default function MonthlyClosing() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [overview, setOverview] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [closing, setClosing] = useState(false);

  const MONTHS = [
    'Januar', 'Februar', 'Maerz', 'April', 'Mai', 'Juni',
    'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
  ];

  const load = async () => {
    setLoading(true);
    try {
      const r = await getMonthlyOverview(year, month);
      setOverview(r.data);
    } catch { setOverview(null); }
    setLoading(false);
  };

  const handleClose = async () => {
    if (!confirm(`Monatsabschluss fuer ${MONTHS[month - 1]} ${year} durchfuehren?`)) return;
    setClosing(true);
    try {
      await closeMonth(year, month);
      await load();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Fehler');
    }
    setClosing(false);
  };

  const handleExport = async () => {
    try {
      const r = await exportLoga(year, month);
      const blob = new Blob([r.data], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `loga_export_${year}_${String(month).padStart(2, '0')}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      await load();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Keine exportierbaren Daten');
    }
  };

  const STATUS_COLORS: Record<string, string> = {
    CLOSED: '#22c55e', EXPORTED: '#3b82f6', OPEN: '#f59e0b',
  };
  const STATUS_LABELS: Record<string, string> = {
    CLOSED: 'Abgeschlossen', EXPORTED: 'Exportiert', OPEN: 'Offen',
  };

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', marginBottom: 24 }}>
        Monatsabschluss
      </h1>

      {/* Filter */}
      <Card style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'end', flexWrap: 'wrap' }}>
          <div>
            <label style={labelStyle}>Jahr</label>
            <input type="number" value={year} onChange={(e) => setYear(+e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Monat</label>
            <select value={month} onChange={(e) => setMonth(+e.target.value)} style={inputStyle}>
              {MONTHS.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
            </select>
          </div>
          <button onClick={load} disabled={loading} style={{ ...btnStyle, background: '#3b82f6' }}>
            {loading ? 'Laden...' : 'Laden'}
          </button>
          <button onClick={handleClose} disabled={closing} style={{ ...btnStyle, background: '#22c55e' }}>
            Monat abschliessen
          </button>
          <button onClick={handleExport} style={{ ...btnStyle, background: '#8b5cf6' }}>
            Loga-Export (CSV)
          </button>
        </div>
      </Card>

      {/* Uebersicht */}
      {overview && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20 }}>
            <StatBox label="Mitarbeiter gesamt" value={overview.total_employees} />
            <StatBox label="Abgeschlossen" value={overview.closed} color="#22c55e" />
            <StatBox label="Offen" value={overview.open} color="#f59e0b" />
            <StatBox label="Exportiert" value={overview.exported} color="#3b82f6" />
          </div>

          <Card>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                  <th style={th}>Mitarbeiter</th>
                  <th style={th}>Soll</th>
                  <th style={th}>Ist</th>
                  <th style={th}>Ueber</th>
                  <th style={th}>Krank</th>
                  <th style={th}>Urlaub</th>
                  <th style={th}>Status</th>
                </tr>
              </thead>
              <tbody>
                {overview.closings.map((c: any) => (
                  <tr key={c.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ ...td, fontWeight: 500 }}>{c.employee_name}</td>
                    <td style={td}>{c.target_hours}h</td>
                    <td style={td}>{c.total_hours}h</td>
                    <td style={{
                      ...td,
                      color: c.overtime_hours > 0 ? '#f59e0b' : c.overtime_hours < 0 ? '#ef4444' : '#64748b',
                      fontWeight: 500,
                    }}>
                      {c.overtime_hours > 0 ? '+' : ''}{c.overtime_hours}h
                    </td>
                    <td style={td}>{c.sick_days > 0 ? `${c.sick_days} T` : '--'}</td>
                    <td style={td}>{c.vacation_days > 0 ? `${c.vacation_days} T` : '--'}</td>
                    <td style={td}>
                      <Badge
                        text={STATUS_LABELS[c.status] || c.status}
                        color={STATUS_COLORS[c.status] || '#64748b'}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {overview.closings.length === 0 && (
              <div style={{ textAlign: 'center', padding: 24, color: '#94a3b8', fontSize: 14 }}>
                Noch keine Abschluesse fuer diesen Monat
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}

function StatBox({ label, value, color }: { label: string; value: number | string; color?: string }) {
  return (
    <div style={{
      padding: 16, background: '#fff', borderRadius: 8,
      border: '1px solid #e2e8f0', textAlign: 'center',
    }}>
      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: color || '#1e293b' }}>{value}</div>
    </div>
  );
}

const labelStyle = { display: 'block', fontSize: 12, color: '#64748b', marginBottom: 4 } as const;
const inputStyle = { padding: '8px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 14 };
const btnStyle = {
  padding: '8px 16px', borderRadius: 6, border: 'none',
  color: '#fff', fontSize: 13, fontWeight: 600 as const, cursor: 'pointer',
};
const th = { textAlign: 'left' as const, padding: '8px 12px', color: '#64748b', fontWeight: 500 as const };
const td = { padding: '10px 12px' };
