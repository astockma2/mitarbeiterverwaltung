import { useEffect, useState } from 'react';
import Card from '../components/Card';
import { getMySchedule } from '../services/api';

export default function MySchedule() {
  const [shifts, setShifts] = useState<any[]>([]);
  const [month, setMonth] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  });

  useEffect(() => {
    const [y, m] = month.split('-').map(Number);
    const start = `${y}-${String(m).padStart(2, '0')}-01`;
    const lastDay = new Date(y, m, 0).getDate();
    const end = `${y}-${String(m).padStart(2, '0')}-${lastDay}`;
    getMySchedule(start, end).then((r) => setShifts(r.data)).catch(() => setShifts([]));
  }, [month]);

  const weekdays = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', marginBottom: 24 }}>
        Mein Dienstplan
      </h1>

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
          <input type="month" value={month} onChange={(e) => setMonth(e.target.value)}
            style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 14 }} />
          <span style={{ color: '#64748b', fontSize: 13 }}>{shifts.length} Schichten</span>
        </div>

        {shifts.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>
            Kein Dienstplan fuer diesen Monat
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4 }}>
            {/* Wochentag-Header */}
            {['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'].map((d) => (
              <div key={d} style={{
                textAlign: 'center', fontSize: 12, fontWeight: 600, color: '#64748b', padding: 4,
              }}>{d}</div>
            ))}

            {/* Kalender-Zellen */}
            {(() => {
              const [y, m] = month.split('-').map(Number);
              const firstDay = new Date(y, m - 1, 1).getDay(); // 0=So
              const daysInMonth = new Date(y, m, 0).getDate();
              const offset = firstDay === 0 ? 6 : firstDay - 1; // Mo=0

              const shiftMap: Record<string, any> = {};
              shifts.forEach((s) => { shiftMap[s.date] = s; });

              const cells = [];
              for (let i = 0; i < offset; i++) {
                cells.push(<div key={`e${i}`} />);
              }
              for (let d = 1; d <= daysInMonth; d++) {
                const dateStr = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
                const shift = shiftMap[dateStr];
                const isToday = dateStr === new Date().toISOString().split('T')[0];
                const isWeekend = new Date(y, m - 1, d).getDay() % 6 === 0;

                cells.push(
                  <div key={d} style={{
                    border: isToday ? '2px solid #3b82f6' : '1px solid #e2e8f0',
                    borderRadius: 6, padding: 6, minHeight: 64,
                    background: isWeekend ? '#f8fafc' : '#fff',
                  }}>
                    <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{d}</div>
                    {shift && (
                      <div style={{
                        fontSize: 11, fontWeight: 600, padding: '3px 6px', borderRadius: 4,
                        background: (shift.shift_code === 'F' ? '#dcfce7' :
                          shift.shift_code === 'S' ? '#fef3c7' :
                          shift.shift_code === 'N' ? '#e0e7ff' : '#f1f5f9'),
                        color: (shift.shift_code === 'F' ? '#166534' :
                          shift.shift_code === 'S' ? '#92400e' :
                          shift.shift_code === 'N' ? '#3730a3' : '#374151'),
                      }}>
                        {shift.shift_code} {shift.shift_start}
                      </div>
                    )}
                  </div>
                );
              }
              return cells;
            })()}
          </div>
        )}

        {/* Liste */}
        {shifts.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: '#1e293b', marginBottom: 12 }}>Schichtliste</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                  <th style={th}>Datum</th>
                  <th style={th}>Tag</th>
                  <th style={th}>Schicht</th>
                  <th style={th}>Zeit</th>
                  <th style={th}>Status</th>
                </tr>
              </thead>
              <tbody>
                {shifts.map((s) => {
                  const d = new Date(s.date + 'T00:00:00');
                  return (
                    <tr key={s.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={td}>{s.date}</td>
                      <td style={td}>{weekdays[d.getDay()]}</td>
                      <td style={{ ...td, fontWeight: 500 }}>{s.shift_name} ({s.shift_code})</td>
                      <td style={td}>{s.shift_start} - {s.shift_end}</td>
                      <td style={td}>
                        <span style={{
                          fontSize: 11, padding: '2px 6px', borderRadius: 4,
                          background: s.status === 'CONFIRMED' ? '#dcfce7' : '#fef3c7',
                          color: s.status === 'CONFIRMED' ? '#166534' : '#92400e',
                        }}>{s.status === 'CONFIRMED' ? 'Bestaetigt' : s.status}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

const th = { textAlign: 'left' as const, padding: '6px 10px', color: '#64748b', fontWeight: 500 as const };
const td = { padding: '8px 10px' };
