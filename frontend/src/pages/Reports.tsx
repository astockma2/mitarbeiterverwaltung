import { useState } from 'react';
import Card, { Badge } from '../components/Card';
import {
  getYearlyOverview, getDepartmentSummary, getSurchargeSummary,
  getAbsenceStatistics, exportExtendedCsv,
} from '../services/api';

type Tab = 'yearly' | 'department' | 'surcharges' | 'absences';

export default function Reports() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [tab, setTab] = useState<Tab>('yearly');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const MONTHS = [
    'Januar', 'Februar', 'Maerz', 'April', 'Mai', 'Juni',
    'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
  ];

  const load = async () => {
    setLoading(true);
    setData(null);
    try {
      let r;
      switch (tab) {
        case 'yearly': r = await getYearlyOverview(year); break;
        case 'department': r = await getDepartmentSummary(year, month); break;
        case 'surcharges': r = await getSurchargeSummary(year, month); break;
        case 'absences': r = await getAbsenceStatistics(year); break;
      }
      setData(r.data);
    } catch { setData(null); }
    setLoading(false);
  };

  const handleExport = async () => {
    try {
      const r = await exportExtendedCsv(year, month);
      const blob = new Blob([r.data], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${year}_${String(month).padStart(2, '0')}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert('Export fehlgeschlagen');
    }
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: 'yearly', label: 'Jahresuebersicht' },
    { key: 'department', label: 'Abteilungen' },
    { key: 'surcharges', label: 'Zuschlaege' },
    { key: 'absences', label: 'Abwesenheiten' },
  ];

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', marginBottom: 24 }}>
        Auswertungen
      </h1>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
        {tabs.map((t) => (
          <button key={t.key} onClick={() => { setTab(t.key); setData(null); }} style={{
            padding: '8px 16px', borderRadius: 6, border: 'none', fontSize: 13, fontWeight: 500,
            background: tab === t.key ? '#3b82f6' : '#e2e8f0',
            color: tab === t.key ? '#fff' : '#64748b', cursor: 'pointer',
          }}>{t.label}</button>
        ))}
      </div>

      {/* Filter */}
      <Card style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'end', flexWrap: 'wrap' }}>
          <div>
            <label style={labelStyle}>Jahr</label>
            <input type="number" value={year} onChange={(e) => setYear(+e.target.value)} style={inputStyle} />
          </div>
          {(tab === 'department' || tab === 'surcharges') && (
            <div>
              <label style={labelStyle}>Monat</label>
              <select value={month} onChange={(e) => setMonth(+e.target.value)} style={inputStyle}>
                {MONTHS.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
              </select>
            </div>
          )}
          <button onClick={load} disabled={loading} style={{
            padding: '8px 20px', borderRadius: 6, background: '#3b82f6',
            color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer',
          }}>{loading ? 'Laden...' : 'Laden'}</button>
          <button onClick={handleExport} style={{
            padding: '8px 20px', borderRadius: 6, background: '#8b5cf6',
            color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer',
          }}>CSV-Export</button>
        </div>
      </Card>

      {/* Inhalt */}
      {loading && <div style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>Laden...</div>}

      {data && tab === 'yearly' && <YearlyView data={data} />}
      {data && tab === 'department' && <DepartmentView data={data} />}
      {data && tab === 'surcharges' && <SurchargeView data={data} />}
      {data && tab === 'absences' && <AbsenceView data={data} />}
    </div>
  );
}

function YearlyView({ data }: { data: any }) {
  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 20 }}>
        <StatBox label="Mitarbeiter" value={data.summary.total_employees} />
        <StatBox label="Gesamtstunden" value={`${data.summary.total_hours}h`} color="#3b82f6" />
        <StatBox label="Ueberstunden" value={`${data.summary.total_overtime}h`} color="#f59e0b" />
        <StatBox label="Krankheitstage" value={data.summary.total_sick_days} color="#ef4444" />
        <StatBox label="Urlaubstage" value={data.summary.total_vacation_days} color="#8b5cf6" />
      </div>

      <Card>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
              <th style={th}>Name</th>
              <th style={th}>Abteilung</th>
              <th style={th}>Soll</th>
              <th style={th}>Ist</th>
              <th style={th}>Ueber</th>
              <th style={th}>Krank</th>
              <th style={th}>Urlaub</th>
            </tr>
          </thead>
          <tbody>
            {data.employees.map((e: any) => (
              <tr key={e.employee_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                <td style={{ ...td, fontWeight: 500 }}>{e.name}</td>
                <td style={{ ...td, color: '#64748b' }}>{e.department || '--'}</td>
                <td style={td}>{e.target_hours}h</td>
                <td style={td}>{e.total_hours}h</td>
                <td style={{
                  ...td, fontWeight: 500,
                  color: e.overtime_hours > 0 ? '#f59e0b' : e.overtime_hours < 0 ? '#ef4444' : '#64748b',
                }}>
                  {e.overtime_hours > 0 ? '+' : ''}{e.overtime_hours}h
                </td>
                <td style={td}>{e.sick_days || '--'}</td>
                <td style={td}>{e.vacation_days || '--'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}

function DepartmentView({ data }: { data: any }) {
  return (
    <Card>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
            <th style={th}>Abteilung</th>
            <th style={th}>Kostenstelle</th>
            <th style={th}>MA</th>
            <th style={th}>Soll</th>
            <th style={th}>Ist</th>
            <th style={th}>Ueber</th>
            <th style={th}>Krank</th>
          </tr>
        </thead>
        <tbody>
          {data.departments.map((d: any) => (
            <tr key={d.department_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
              <td style={{ ...td, fontWeight: 500 }}>{d.department_name}</td>
              <td style={{ ...td, fontFamily: 'monospace', color: '#64748b' }}>{d.cost_center || '--'}</td>
              <td style={td}>{d.employee_count}</td>
              <td style={td}>{d.target_hours}h</td>
              <td style={td}>{d.total_hours}h</td>
              <td style={{
                ...td, fontWeight: 500,
                color: d.overtime_hours > 0 ? '#f59e0b' : '#64748b',
              }}>
                {d.overtime_hours > 0 ? '+' : ''}{d.overtime_hours}h
              </td>
              <td style={td}>{d.sick_days || '--'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.departments.length === 0 && (
        <div style={{ textAlign: 'center', padding: 24, color: '#94a3b8' }}>Keine Daten</div>
      )}
    </Card>
  );
}

function SurchargeView({ data }: { data: any }) {
  const LABELS: Record<string, string> = {
    NIGHT: 'Nachtzuschlag', SUNDAY: 'Sonntagszuschlag',
    HOLIDAY: 'Feiertagszuschlag', SATURDAY: 'Samstagszuschlag',
  };

  return (
    <>
      {/* Gesamtauswertung */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 20 }}>
        {Object.entries(data.totals).map(([type, hours]) => (
          <StatBox key={type} label={LABELS[type] || type} value={`${hours}h`} color="#8b5cf6" />
        ))}
        {Object.keys(data.totals).length === 0 && (
          <StatBox label="Keine Zuschlaege" value="--" />
        )}
      </div>

      {/* Pro Mitarbeiter */}
      {data.by_employee.length > 0 && (
        <Card>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                <th style={th}>Mitarbeiter</th>
                {Object.keys(data.totals).map((type) => (
                  <th key={type} style={th}>{LABELS[type] || type}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.by_employee.map((e: any) => (
                <tr key={e.employee_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ ...td, fontWeight: 500 }}>{e.name}</td>
                  {Object.keys(data.totals).map((type) => (
                    <td key={type} style={td}>
                      {e.surcharges[type] ? `${e.surcharges[type]}h` : '--'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </>
  );
}

function AbsenceView({ data }: { data: any }) {
  const TYPE_LABELS: Record<string, string> = {
    VACATION: 'Urlaub', SICK: 'Krankheit', TRAINING: 'Fortbildung',
    SPECIAL: 'Sonderurlaub', COMP_TIME: 'Freizeitausgleich',
  };
  const MONTH_NAMES = [
    '', 'Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun',
    'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez',
  ];

  return (
    <>
      {/* Nach Typ */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 20 }}>
        {Object.entries(data.by_type).map(([type, info]: [string, any]) => (
          <StatBox key={type} label={TYPE_LABELS[type] || type}
            value={`${info.days} Tage`}
            color={type === 'SICK' ? '#ef4444' : type === 'VACATION' ? '#8b5cf6' : '#3b82f6'}
          />
        ))}
      </div>

      {/* Nach Monat */}
      <Card title="Abwesenheitstage pro Monat" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'end', height: 120 }}>
          {Array.from({ length: 12 }, (_, i) => {
            const m = String(i + 1);
            const days = data.by_month[m] || 0;
            const maxDays = Math.max(1, ...Object.values(data.by_month as Record<string, number>));
            return (
              <div key={i} style={{ flex: 1, textAlign: 'center' }}>
                <div style={{
                  background: '#3b82f6', borderRadius: '4px 4px 0 0',
                  height: `${Math.max(2, (days / maxDays) * 100)}px`,
                  marginBottom: 4, transition: 'height 0.3s',
                }} />
                <div style={{ fontSize: 10, color: '#64748b' }}>{MONTH_NAMES[i + 1]}</div>
                <div style={{ fontSize: 11, fontWeight: 600 }}>{days || ''}</div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Top Krankheitstage */}
      {data.top_sick_days.length > 0 && (
        <Card title="Hoechste Krankheitstage">
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <tbody>
              {data.top_sick_days.map((e: any, i: number) => (
                <tr key={i} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ ...td, fontWeight: 500 }}>{e.name}</td>
                  <td style={{ ...td, textAlign: 'right', color: '#ef4444', fontWeight: 600 }}>
                    {e.days} Tage
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </>
  );
}

function StatBox({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div style={{
      padding: 16, background: '#fff', borderRadius: 8,
      border: '1px solid #e2e8f0', textAlign: 'center',
    }}>
      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: color || '#1e293b' }}>{value}</div>
    </div>
  );
}

const labelStyle = { display: 'block', fontSize: 12, color: '#64748b', marginBottom: 4 } as const;
const inputStyle = { padding: '8px 10px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 14 };
const th = { textAlign: 'left' as const, padding: '8px 12px', color: '#64748b', fontWeight: 500 as const };
const td = { padding: '10px 12px' };
