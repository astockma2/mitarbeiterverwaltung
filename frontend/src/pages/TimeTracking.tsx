import { useEffect, useState } from 'react';
import { Clock, LogIn, LogOut, Plus } from 'lucide-react';
import Card, { Badge } from '../components/Card';
import { clockIn, clockOut, getClockStatus, getTimeEntries, getDailySummary } from '../services/api';

export default function TimeTracking() {
  const [status, setStatus] = useState<any>(null);
  const [entries, setEntries] = useState<any[]>([]);
  const [breakMin, setBreakMin] = useState(30);
  const [loading, setLoading] = useState(false);
  const [today, setToday] = useState<any>(null);

  const load = () => {
    getClockStatus().then((r) => setStatus(r.data));
    const now = new Date().toISOString().split('T')[0];
    getTimeEntries({ start_date: now, end_date: now }).then((r) => setEntries(r.data));
    getDailySummary(now).then((r) => setToday(r.data));
  };

  useEffect(load, []);

  const handleClockIn = async () => {
    setLoading(true);
    try {
      await clockIn();
      load();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Fehler');
    }
    setLoading(false);
  };

  const handleClockOut = async () => {
    setLoading(true);
    try {
      await clockOut(breakMin);
      load();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Fehler');
    }
    setLoading(false);
  };

  const btnBase = {
    padding: '12px 24px', borderRadius: 8, border: 'none',
    fontSize: 15, fontWeight: 600 as const, cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 8, color: '#fff',
  };

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', marginBottom: 24 }}>
        Zeiterfassung
      </h1>

      {/* Stempel-Bereich */}
      <Card style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
          {!status?.clocked_in ? (
            <button onClick={handleClockIn} disabled={loading}
              style={{ ...btnBase, background: '#22c55e' }}>
              <LogIn size={18} /> Einstempeln
            </button>
          ) : (
            <>
              <div style={{ fontSize: 14 }}>
                <span style={{ color: '#22c55e', fontWeight: 600 }}>Eingestempelt</span>
                {' '}seit {new Date(status.since).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })}
                {' '}({status.elapsed_hours}h)
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <label style={{ fontSize: 13, color: '#64748b' }}>Pause (Min):</label>
                <input
                  type="number" value={breakMin} onChange={(e) => setBreakMin(+e.target.value)}
                  style={{ width: 60, padding: '6px 8px', borderRadius: 4, border: '1px solid #d1d5db', fontSize: 14 }}
                />
              </div>
              <button onClick={handleClockOut} disabled={loading}
                style={{ ...btnBase, background: '#ef4444' }}>
                <LogOut size={18} /> Ausstempeln
              </button>
            </>
          )}
        </div>
      </Card>

      {/* Tagesuebersicht */}
      {today && (
        <Card title={`Heute — ${today.total_hours}h (Pause: ${today.total_break_minutes} Min)`}
          style={{ marginBottom: 24 }}>
          {/* Arbeitszeit-Balken */}
          <div style={{ background: '#f1f5f9', borderRadius: 8, height: 8, marginBottom: 16 }}>
            <div style={{
              background: '#3b82f6', borderRadius: 8, height: '100%',
              width: `${Math.min(100, (today.total_hours / 8) * 100)}%`,
              transition: 'width 0.3s',
            }} />
          </div>
        </Card>
      )}

      {/* Eintraege */}
      <Card title="Heutige Eintraege">
        {entries.length === 0 ? (
          <div style={{ color: '#94a3b8', fontSize: 14, padding: 20, textAlign: 'center' }}>
            Noch keine Eintraege heute
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                <th style={th}>Kommen</th>
                <th style={th}>Gehen</th>
                <th style={th}>Pause</th>
                <th style={th}>Netto</th>
                <th style={th}>Typ</th>
                <th style={th}>Zuschlaege</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={td}>{fmtTime(e.clock_in)}</td>
                  <td style={td}>{e.clock_out ? fmtTime(e.clock_out) : <Badge text="offen" color="#f59e0b" />}</td>
                  <td style={td}>{e.break_minutes} Min</td>
                  <td style={td}>{e.net_hours != null ? `${e.net_hours}h` : '--'}</td>
                  <td style={td}><Badge text={e.entry_type} color="#64748b" /></td>
                  <td style={td}>
                    {(e.surcharges || []).map((s: any, i: number) => (
                      <Badge key={i} text={`${s.type} ${s.hours}h`} color="#8b5cf6" />
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

const th = { textAlign: 'left' as const, padding: '8px 12px', color: '#64748b', fontWeight: 500 as const };
const td = { padding: '10px 12px' };

function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
}
