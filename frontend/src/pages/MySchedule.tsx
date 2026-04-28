import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import Card from '../components/Card';
import { getMySchedule } from '../services/api';

type ScheduleExtra = {
  type: string;
  code: string;
  label: string;
  status: string;
  color: string;
};

type ShiftAssignment = {
  id: number;
  date: string;
  shift_name?: string | null;
  shift_code?: string | null;
  shift_start?: string | null;
  shift_end?: string | null;
  status: string;
  extras?: ScheduleExtra[];
};

const SHIFT_STYLES: Record<string, { bg: string; text: string }> = {
  D: { bg: '#dbeafe', text: '#1e40af' },
  F: { bg: '#dcfce7', text: '#166534' },
  S: { bg: '#fef3c7', text: '#92400e' },
  N: { bg: '#e0e7ff', text: '#3730a3' },
};

export default function MySchedule() {
  const [shifts, setShifts] = useState<ShiftAssignment[]>([]);
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
          <input
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 14 }}
          />
          <span style={{ color: '#64748b', fontSize: 13 }}>{shifts.length} Dienste</span>
        </div>

        {shifts.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>
            Kein Dienstplan fuer diesen Monat
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, minmax(0, 1fr))', gap: 4 }}>
            {['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'].map((d) => (
              <div
                key={d}
                style={{
                  textAlign: 'center',
                  fontSize: 12,
                  fontWeight: 600,
                  color: '#64748b',
                  padding: 4,
                }}
              >
                {d}
              </div>
            ))}

            {buildCalendarCells(month, shifts)}
          </div>
        )}

        {shifts.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: '#1e293b', marginBottom: 12 }}>Dienstliste</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                  <th style={th}>Datum</th>
                  <th style={th}>Tag</th>
                  <th style={th}>Dienst</th>
                  <th style={th}>Zeit</th>
                  <th style={th}>Zusatz</th>
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
                      <td style={{ ...td, fontWeight: 500 }}>
                        {s.shift_name} ({s.shift_code})
                      </td>
                      <td style={td}>{formatShiftTime(s)}</td>
                      <td style={td}>
                        <ExtraChips extras={s.extras || []} />
                      </td>
                      <td style={td}>
                        <span style={{
                          fontSize: 11,
                          padding: '2px 6px',
                          borderRadius: 4,
                          background: s.status === 'CONFIRMED' ? '#dcfce7' : '#fef3c7',
                          color: s.status === 'CONFIRMED' ? '#166534' : '#92400e',
                        }}>
                          {s.status === 'CONFIRMED' ? 'Bestaetigt' : s.status}
                        </span>
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

function buildCalendarCells(month: string, shifts: ShiftAssignment[]) {
  const [y, m] = month.split('-').map(Number);
  const firstDay = new Date(y, m - 1, 1).getDay();
  const daysInMonth = new Date(y, m, 0).getDate();
  const offset = firstDay === 0 ? 6 : firstDay - 1;
  const shiftMap: Record<string, ShiftAssignment> = {};
  shifts.forEach((s) => { shiftMap[s.date] = s; });

  const cells = [];
  for (let i = 0; i < offset; i += 1) {
    cells.push(<div key={`e${i}`} />);
  }
  for (let d = 1; d <= daysInMonth; d += 1) {
    const dateStr = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    const shift = shiftMap[dateStr];
    const isToday = dateStr === new Date().toISOString().split('T')[0];
    const isWeekend = new Date(y, m - 1, d).getDay() % 6 === 0;

    cells.push(
      <div
        key={d}
        style={{
          border: isToday ? '2px solid #3b82f6' : '1px solid #e2e8f0',
          borderRadius: 6,
          padding: 6,
          minHeight: 82,
          background: isWeekend ? '#f8fafc' : '#fff',
          minWidth: 0,
        }}
      >
        <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{d}</div>
        {shift && (
          <>
            <ShiftPill shift={shift} />
            <div style={{ marginTop: 4 }}>
              <ExtraChips extras={(shift.extras || []).slice(0, 2)} compact />
              {(shift.extras || []).length > 2 && (
                <span style={{ color: '#64748b', fontSize: 10 }}>+{(shift.extras || []).length - 2}</span>
              )}
            </div>
          </>
        )}
      </div>
    );
  }
  return cells;
}

function ShiftPill({ shift }: { shift: ShiftAssignment }) {
  const code = shift.shift_code || 'D';
  const style = SHIFT_STYLES[code] || { bg: '#f1f5f9', text: '#374151' };
  return (
    <div
      title={`${shift.shift_name || 'Dienst'} ${formatShiftTime(shift)}`}
      style={{
        fontSize: 11,
        fontWeight: 700,
        padding: '3px 6px',
        borderRadius: 4,
        background: style.bg,
        color: style.text,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}
    >
      {code}{shift.shift_start ? ` ${shift.shift_start}` : ''}
    </div>
  );
}

function ExtraChips({ extras, compact = false }: { extras: ScheduleExtra[]; compact?: boolean }) {
  if (extras.length === 0) {
    return <span style={{ color: '#94a3b8', fontSize: 12 }}>-</span>;
  }
  return (
    <span style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
      {extras.map((extra, index) => (
        <span
          key={`${extra.type}-${extra.code}-${index}`}
          title={`${extra.label} (${extra.status})`}
          style={{
            background: extra.color,
            color: readableTextColor(extra.color),
            borderRadius: 4,
            padding: compact ? '1px 4px' : '2px 6px',
            fontSize: compact ? 10 : 11,
            fontWeight: 700,
            lineHeight: 1.4,
          }}
        >
          {extra.code}
        </span>
      ))}
    </span>
  );
}

function formatShiftTime(shift: ShiftAssignment) {
  if (!shift.shift_start && !shift.shift_end) return 'Zusatzdienst';
  return `${shift.shift_start || ''} - ${shift.shift_end || ''}`;
}

function readableTextColor(color: string) {
  const light = ['#FACC15', '#EAB308', '#FEF3C7', '#DCFCE7', '#DBEAFE'];
  return light.includes(color.toUpperCase()) ? '#111827' : '#ffffff';
}

const th: CSSProperties = { textAlign: 'left', padding: '6px 10px', color: '#64748b', fontWeight: 500 };
const td: CSSProperties = { padding: '8px 10px', verticalAlign: 'top' };
