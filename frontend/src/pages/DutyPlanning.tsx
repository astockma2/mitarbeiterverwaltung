import { useCallback, useEffect, useMemo, useState } from 'react';
import type { CSSProperties, FormEvent } from 'react';
import { Link } from 'react-router-dom';
import {
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  Plane,
  RefreshCw,
  Table2,
  X,
} from 'lucide-react';
import Card, { Badge } from '../components/Card';
import {
  createTravelRequest,
  getDepartments,
  getPendingTravelRequests,
  getPlanningCalendar,
  reviewTravelRequest,
} from '../services/api';

const MONTH_NAMES = [
  'Januar',
  'Februar',
  'Maerz',
  'April',
  'Mai',
  'Juni',
  'Juli',
  'August',
  'September',
  'Oktober',
  'November',
  'Dezember',
];

const WEEKDAY_SHORT = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];
const DAY_WIDTH = 34;
const NAME_WIDTH = 190;

type ViewMode = 'year' | 'month';

type PlanningEvent = {
  id: number;
  type: string;
  code: string;
  label: string;
  status: string;
  color: string;
  source?: string | null;
};

type PlanningDay = {
  date: string;
  events: PlanningEvent[];
};

type PlanningEmployee = {
  id: number;
  name: string;
  department_id?: number | null;
  department_name?: string | null;
  vacation_days_per_year: number;
  days: PlanningDay[];
};

type PlanningCalendar = {
  start_date: string;
  end_date: string;
  days: string[];
  employees: PlanningEmployee[];
};

type TravelRequest = {
  id: number;
  employee_id: number;
  employee_name?: string | null;
  start_date: string;
  end_date: string;
  destination: string;
  purpose: string;
  status: string;
};

type Department = {
  id: number;
  name: string;
};

type Props = {
  isHR: boolean;
};

const STATUS_LABELS: Record<string, string> = {
  REQUESTED: 'Beantragt',
  MANAGER_APPROVED: 'Fachlich frei',
  APPROVED: 'Genehmigt',
  APPROVED_LEGACY: 'Importiert',
  REJECTED: 'Abgelehnt',
  CANCELLED: 'Storniert',
  PLANNED: 'Geplant',
  CONFIRMED: 'Bestaetigt',
  IMPORTED: 'Importiert',
};

function pad(value: number) {
  return String(value).padStart(2, '0');
}

function dateKey(year: number, month: number, day: number) {
  return `${year}-${pad(month)}-${pad(day)}`;
}

function daysInMonth(year: number, month: number) {
  return new Date(year, month, 0).getDate();
}

function localDate(value: string) {
  return new Date(`${value}T00:00:00`);
}

function getRange(mode: ViewMode, year: number, month: number) {
  if (mode === 'year') {
    return { start: `${year}-01-01`, end: `${year}-12-31` };
  }
  return {
    start: dateKey(year, month, 1),
    end: dateKey(year, month, daysInMonth(year, month)),
  };
}

function isWeekend(value: string) {
  const day = localDate(value).getDay();
  return day === 0 || day === 6;
}

function eventTitle(event: PlanningEvent) {
  const status = STATUS_LABELS[event.status] || event.status;
  return `${event.code} - ${event.label} (${status})`;
}

function groupMonthHeaders(days: string[]) {
  const groups: Array<{ month: number; label: string; count: number }> = [];
  for (const day of days) {
    const month = localDate(day).getMonth();
    const last = groups[groups.length - 1];
    if (last?.month === month) {
      last.count += 1;
    } else {
      groups.push({ month, label: MONTH_NAMES[month], count: 1 });
    }
  }
  return groups;
}

export default function DutyPlanning({ isHR }: Props) {
  const today = new Date();
  const [mode, setMode] = useState<ViewMode>('year');
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [departmentId, setDepartmentId] = useState('');
  const [calendar, setCalendar] = useState<PlanningCalendar | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [pendingTravel, setPendingTravel] = useState<TravelRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [travelForm, setTravelForm] = useState({
    employee_id: '',
    start_date: dateKey(today.getFullYear(), today.getMonth() + 1, today.getDate()),
    end_date: dateKey(today.getFullYear(), today.getMonth() + 1, today.getDate()),
    destination: '',
    purpose: '',
    cost_center: '',
    transport_type: '',
    estimated_costs: '',
  });

  const range = useMemo(() => getRange(mode, year, month), [mode, year, month]);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params: { start_date: string; end_date: string; department_id?: string } = {
        start_date: range.start,
        end_date: range.end,
      };
      if (departmentId) params.department_id = departmentId;
      const [calendarResponse, pendingResponse] = await Promise.all([
        getPlanningCalendar(params),
        getPendingTravelRequests().catch(() => ({ data: [] })),
      ]);
      setCalendar(calendarResponse.data as PlanningCalendar);
      setPendingTravel(pendingResponse.data as TravelRequest[]);
    } catch (loadError: any) {
      setError(loadError.response?.data?.detail || 'Planung konnte nicht geladen werden');
    } finally {
      setLoading(false);
    }
  }, [departmentId, range.end, range.start]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!isHR) return;
    getDepartments()
      .then((response) => setDepartments(response.data as Department[]))
      .catch(() => setDepartments([]));
  }, [isHR]);

  const employees = calendar?.employees || [];
  const days = calendar?.days || [];
  const monthHeaders = useMemo(() => groupMonthHeaders(days), [days]);

  const setPrevious = () => {
    if (mode === 'year') {
      setYear((current) => current - 1);
      return;
    }
    if (month === 1) {
      setYear((current) => current - 1);
      setMonth(12);
      return;
    }
    setMonth((current) => current - 1);
  };

  const setNext = () => {
    if (mode === 'year') {
      setYear((current) => current + 1);
      return;
    }
    if (month === 12) {
      setYear((current) => current + 1);
      setMonth(1);
      return;
    }
    setMonth((current) => current + 1);
  };

  const openMonth = (day: string) => {
    const parsed = localDate(day);
    setYear(parsed.getFullYear());
    setMonth(parsed.getMonth() + 1);
    setMode('month');
  };

  const submitTravel = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    try {
      await createTravelRequest({
        employee_id: travelForm.employee_id ? Number(travelForm.employee_id) : undefined,
        start_date: travelForm.start_date,
        end_date: travelForm.end_date,
        destination: travelForm.destination,
        purpose: travelForm.purpose,
        cost_center: travelForm.cost_center || undefined,
        transport_type: travelForm.transport_type || undefined,
        estimated_costs: travelForm.estimated_costs ? Number(travelForm.estimated_costs) : null,
      });
      setTravelForm((current) => ({
        ...current,
        destination: '',
        purpose: '',
        cost_center: '',
        transport_type: '',
        estimated_costs: '',
      }));
      await load();
    } catch (submitError: any) {
      setError(submitError.response?.data?.detail || 'Dienstreise konnte nicht gespeichert werden');
    }
  };

  const reviewTravel = async (id: number, approved: boolean) => {
    await reviewTravelRequest(id, { approved, final_approval: isHR });
    await load();
  };

  const title = mode === 'year' ? String(year) : `${MONTH_NAMES[month - 1]} ${year}`;
  const totalEvents = employees.reduce(
    (sum, employee) => sum + employee.days.reduce((daySum, day) => daySum + day.events.length, 0),
    0
  );
  const totalTravel = employees.reduce(
    (sum, employee) =>
      sum + employee.days.reduce((daySum, day) => daySum + day.events.filter((item) => item.type === 'travel').length, 0),
    0
  );

  return (
    <div>
      <div style={topbarStyle}>
        <div>
          <h1 style={headingStyle}>
            <CalendarDays size={24} />
            Dienstplanung
          </h1>
          <div style={{ marginTop: 6, color: '#64748b', fontSize: 13 }}>
            {title}
          </div>
        </div>
        <Link to="/shift-plans/monthly" style={secondaryButtonStyle}>
          <Table2 size={16} />
          Schicht-Editor
        </Link>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <div style={toolbarStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <button onClick={setPrevious} style={iconButtonStyle} title="Zurueck">
              <ChevronLeft size={18} />
            </button>
            <div style={periodStyle}>{title}</div>
            <button onClick={setNext} style={iconButtonStyle} title="Weiter">
              <ChevronRight size={18} />
            </button>
            <div style={segmentedStyle}>
              <button
                onClick={() => setMode('year')}
                style={segmentStyle(mode === 'year')}
              >
                Jahr
              </button>
              <button
                onClick={() => setMode('month')}
                style={segmentStyle(mode === 'month')}
              >
                Monat
              </button>
            </div>
            {mode === 'month' && (
              <select value={month} onChange={(event) => setMonth(Number(event.target.value))} style={selectStyle}>
                {MONTH_NAMES.map((name, index) => (
                  <option key={name} value={index + 1}>{name}</option>
                ))}
              </select>
            )}
            {isHR && (
              <select value={departmentId} onChange={(event) => setDepartmentId(event.target.value)} style={selectStyle}>
                <option value="">Alle Abteilungen</option>
                {departments.map((department) => (
                  <option key={department.id} value={department.id}>{department.name}</option>
                ))}
              </select>
            )}
          </div>
          <button onClick={() => void load()} style={secondaryButtonStyle}>
            <RefreshCw size={16} />
            Aktualisieren
          </button>
        </div>

        <div style={metricGridStyle}>
          <Metric label="Mitarbeiter" value={employees.length} />
          <Metric label="Eintraege" value={totalEvents} />
          <Metric label="Dienstreisen" value={totalTravel} />
          <Metric label="Offene Reisen" value={pendingTravel.length} />
        </div>
      </Card>

      {error && <div style={errorStyle}>{error}</div>}

      <div style={contentGridStyle}>
        <div style={{ minWidth: 0 }}>
          <Card style={{ padding: 0, overflow: 'hidden' }}>
            <div style={calendarHeaderStyle}>
              <div style={{ fontWeight: 700, color: '#1e293b' }}>
                {mode === 'year' ? 'Jahresansicht' : 'Monatsansicht'}
              </div>
              <Legend />
            </div>
            <PlanningTable
              mode={mode}
              days={days}
              employees={employees}
              monthHeaders={monthHeaders}
              loading={loading}
              onOpenMonth={openMonth}
            />
          </Card>
        </div>

        <aside style={{ display: 'flex', flexDirection: 'column', gap: 16, minWidth: 280 }}>
          <Card title="Dienstreise">
            <form onSubmit={submitTravel} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <select
                value={travelForm.employee_id}
                onChange={(event) => setTravelForm((current) => ({ ...current, employee_id: event.target.value }))}
                style={inputStyle}
              >
                <option value="">Eigene Dienstreise</option>
                {employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>{employee.name}</option>
                ))}
              </select>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <input
                  type="date"
                  value={travelForm.start_date}
                  onChange={(event) => setTravelForm((current) => ({ ...current, start_date: event.target.value }))}
                  style={inputStyle}
                  required
                />
                <input
                  type="date"
                  value={travelForm.end_date}
                  onChange={(event) => setTravelForm((current) => ({ ...current, end_date: event.target.value }))}
                  style={inputStyle}
                  required
                />
              </div>
              <input
                value={travelForm.destination}
                onChange={(event) => setTravelForm((current) => ({ ...current, destination: event.target.value }))}
                placeholder="Ziel"
                style={inputStyle}
                required
              />
              <input
                value={travelForm.purpose}
                onChange={(event) => setTravelForm((current) => ({ ...current, purpose: event.target.value }))}
                placeholder="Anlass"
                style={inputStyle}
                required
              />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <input
                  value={travelForm.cost_center}
                  onChange={(event) => setTravelForm((current) => ({ ...current, cost_center: event.target.value }))}
                  placeholder="Kostenstelle"
                  style={inputStyle}
                />
                <input
                  type="number"
                  value={travelForm.estimated_costs}
                  onChange={(event) => setTravelForm((current) => ({ ...current, estimated_costs: event.target.value }))}
                  placeholder="Kosten"
                  style={inputStyle}
                />
              </div>
              <input
                value={travelForm.transport_type}
                onChange={(event) => setTravelForm((current) => ({ ...current, transport_type: event.target.value }))}
                placeholder="Verkehrsmittel"
                style={inputStyle}
              />
              <button type="submit" style={primaryButtonStyle}>
                <Plane size={16} />
                Beantragen
              </button>
            </form>
          </Card>

          <Card title={`Offene Dienstreisen (${pendingTravel.length})`}>
            {pendingTravel.length === 0 ? (
              <div style={{ color: '#94a3b8', fontSize: 13, padding: '8px 0' }}>
                Keine offenen Antraege
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {pendingTravel.map((travel) => (
                  <div key={travel.id} style={pendingTravelStyle}>
                    <div style={{ fontWeight: 700, color: '#0f172a', fontSize: 13 }}>
                      {travel.employee_name || `Mitarbeiter ${travel.employee_id}`}
                    </div>
                    <div style={{ color: '#64748b', fontSize: 12 }}>
                      {travel.start_date} bis {travel.end_date}
                    </div>
                    <div style={{ color: '#334155', fontSize: 12, marginTop: 2 }}>
                      {travel.destination}
                    </div>
                    <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                      <button onClick={() => void reviewTravel(travel.id, true)} style={approveButtonStyle}>
                        <Check size={14} />
                      </button>
                      <button onClick={() => void reviewTravel(travel.id, false)} style={rejectButtonStyle}>
                        <X size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </aside>
      </div>
    </div>
  );
}

function PlanningTable({
  mode,
  days,
  employees,
  monthHeaders,
  loading,
  onOpenMonth,
}: {
  mode: ViewMode;
  days: string[];
  employees: PlanningEmployee[];
  monthHeaders: Array<{ month: number; label: string; count: number }>;
  loading: boolean;
  onOpenMonth: (day: string) => void;
}) {
  const tableWidth = NAME_WIDTH + days.length * DAY_WIDTH;

  return (
    <div style={{ overflow: 'auto', maxHeight: mode === 'year' ? 'calc(100vh - 310px)' : 'calc(100vh - 280px)', minHeight: 360 }}>
      <table style={{ borderCollapse: 'collapse', tableLayout: 'fixed', minWidth: tableWidth, width: tableWidth }}>
        <thead>
          {mode === 'year' && (
            <tr>
              <th style={stickyHeaderStyle(0, 0, NAME_WIDTH)} rowSpan={2}>Name</th>
              {monthHeaders.map((header) => (
                <th
                  key={`${header.month}-${header.label}`}
                  colSpan={header.count}
                  style={{
                    ...headerCellStyle,
                    top: 0,
                    height: 28,
                    background: '#eef7e9',
                    borderLeft: '2px solid #94a3b8',
                  }}
                >
                  {header.label}
                </th>
              ))}
            </tr>
          )}
          <tr>
            {mode === 'month' && <th style={stickyHeaderStyle(0, 0, NAME_WIDTH)}>Name</th>}
            {days.map((day) => {
              const parsed = localDate(day);
              return (
                <th
                  key={day}
                  onClick={() => mode === 'year' && onOpenMonth(day)}
                  title={`${WEEKDAY_SHORT[parsed.getDay()]} ${parsed.getDate()}.${parsed.getMonth() + 1}.${parsed.getFullYear()}`}
                  style={{
                    ...headerCellStyle,
                    top: mode === 'year' ? 28 : 0,
                    width: DAY_WIDTH,
                    minWidth: DAY_WIDTH,
                    cursor: mode === 'year' ? 'pointer' : 'default',
                    background: isWeekend(day) ? '#e0f2fe' : '#ffffff',
                    borderLeft: parsed.getDate() === 1 ? '2px solid #94a3b8' : '1px solid #cbd5e1',
                  }}
                >
                  <div style={{ fontSize: 10, color: isWeekend(day) ? '#0369a1' : '#64748b' }}>
                    {mode === 'month' ? WEEKDAY_SHORT[parsed.getDay()] : ''}
                  </div>
                  <div>{parsed.getDate()}</div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {loading && (
            <tr>
              <td colSpan={days.length + 1} style={{ padding: 28, textAlign: 'center', color: '#64748b' }}>
                Planung wird geladen...
              </td>
            </tr>
          )}
          {!loading && employees.map((employee, rowIndex) => (
            <tr key={employee.id}>
              <td style={stickyBodyStyle(rowIndex)}>
                <div style={{ fontWeight: 700, color: '#0f172a' }}>{employee.name}</div>
                <div style={{ color: '#94a3b8', fontSize: 10 }}>{employee.department_name || 'Ohne Abteilung'}</div>
              </td>
              {employee.days.map((day) => (
                <CalendarCell key={`${employee.id}-${day.date}`} day={day} compact={mode === 'year'} />
              ))}
            </tr>
          ))}
          {!loading && employees.length === 0 && (
            <tr>
              <td colSpan={days.length + 1} style={{ padding: 28, textAlign: 'center', color: '#64748b' }}>
                Keine Mitarbeiter gefunden.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function CalendarCell({ day, compact }: { day: PlanningDay; compact: boolean }) {
  const primary = day.events[0];
  const hasConflict = day.events.some((event) => event.type === 'absence') &&
    day.events.some((event) => event.type === 'shift' || event.type === 'duty');

  return (
    <td
      title={day.events.map(eventTitle).join('\n')}
      style={{
        width: DAY_WIDTH,
        minWidth: DAY_WIDTH,
        height: compact ? 24 : 52,
        border: hasConflict ? '2px solid #dc2626' : '1px solid #cbd5e1',
        background: primary?.color ? `${primary.color}24` : isWeekend(day.date) ? '#f0f9ff' : '#ffffff',
        color: '#0f172a',
        textAlign: 'center',
        verticalAlign: 'top',
        padding: compact ? 1 : 3,
      }}
    >
      {compact ? (
        <div style={{ fontSize: 10, fontWeight: 800, color: primary?.color || '#cbd5e1', lineHeight: '20px' }}>
          {primary?.code || ''}
          {day.events.length > 1 ? '+' : ''}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {day.events.slice(0, 3).map((event, index) => (
            <span
              key={`${event.type}-${event.id}-${index}`}
              style={{
                background: event.color,
                color: event.color === '#FACC15' || event.color === '#EAB308' ? '#111827' : '#ffffff',
                borderRadius: 4,
                padding: '2px 3px',
                fontSize: 10,
                fontWeight: 800,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {event.code}
            </span>
          ))}
          {day.events.length > 3 && <span style={{ color: '#64748b', fontSize: 10 }}>+{day.events.length - 3}</span>}
        </div>
      )}
    </td>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={metricStyle}>
      <div style={{ color: '#64748b', fontSize: 12 }}>{label}</div>
      <div style={{ color: '#0f172a', fontSize: 18, fontWeight: 800 }}>{value}</div>
    </div>
  );
}

function Legend() {
  const items = [
    ['Dienst', '#3B82F6'],
    ['Abwesenheit', '#FACC15'],
    ['Dienstreise', '#65A30D'],
    ['Hinweis', '#64748B'],
    ['Konflikt', '#DC2626'],
  ] as const;

  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
      {items.map(([label, color]) => (
        <Badge key={label} text={label} color={color} />
      ))}
    </div>
  );
}

function segmentStyle(active: boolean): CSSProperties {
  return {
    border: 'none',
    background: active ? '#1e293b' : 'transparent',
    color: active ? '#ffffff' : '#475569',
    padding: '7px 12px',
    borderRadius: 6,
    fontSize: 13,
    fontWeight: 700,
    cursor: 'pointer',
  };
}

function stickyHeaderStyle(top: number, left: number, width: number): CSSProperties {
  return {
    ...headerCellStyle,
    position: 'sticky',
    top,
    left,
    zIndex: 5,
    width,
    minWidth: width,
    background: '#ffffff',
  };
}

function stickyBodyStyle(rowIndex: number): CSSProperties {
  return {
    position: 'sticky',
    left: 0,
    zIndex: 4,
    width: NAME_WIDTH,
    minWidth: NAME_WIDTH,
    height: 36,
    border: '1px solid #cbd5e1',
    background: rowIndex % 2 === 0 ? '#f8fafc' : '#ffffff',
    padding: '4px 8px',
    textAlign: 'left',
  };
}

const topbarStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 16,
  marginBottom: 18,
  flexWrap: 'wrap',
};

const headingStyle: CSSProperties = {
  margin: 0,
  fontSize: 24,
  color: '#1e293b',
  display: 'flex',
  alignItems: 'center',
  gap: 10,
};

const toolbarStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  gap: 12,
  flexWrap: 'wrap',
};

const periodStyle: CSSProperties = {
  minWidth: 150,
  textAlign: 'center',
  fontWeight: 800,
  color: '#0f172a',
  fontSize: 18,
};

const segmentedStyle: CSSProperties = {
  display: 'inline-flex',
  padding: 3,
  border: '1px solid #cbd5e1',
  borderRadius: 8,
  background: '#f8fafc',
};

const metricGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
  gap: 10,
  marginTop: 14,
};

const metricStyle: CSSProperties = {
  border: '1px solid #e2e8f0',
  background: '#f8fafc',
  borderRadius: 8,
  padding: '10px 12px',
};

const contentGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1fr) 320px',
  gap: 16,
  alignItems: 'start',
};

const calendarHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 12,
  alignItems: 'center',
  padding: '12px 14px',
  borderBottom: '1px solid #e2e8f0',
  flexWrap: 'wrap',
};

const headerCellStyle: CSSProperties = {
  position: 'sticky',
  zIndex: 3,
  border: '1px solid #cbd5e1',
  padding: 0,
  height: 32,
  fontSize: 11,
  fontWeight: 800,
  color: '#0f172a',
  textAlign: 'center',
  whiteSpace: 'nowrap',
};

const iconButtonStyle: CSSProperties = {
  height: 36,
  width: 38,
  border: '1px solid #cbd5e1',
  borderRadius: 8,
  background: '#ffffff',
  color: '#334155',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
};

const secondaryButtonStyle: CSSProperties = {
  minHeight: 36,
  border: '1px solid #cbd5e1',
  borderRadius: 8,
  background: '#ffffff',
  color: '#334155',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 8,
  padding: '0 12px',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 700,
  textDecoration: 'none',
};

const primaryButtonStyle: CSSProperties = {
  minHeight: 36,
  border: 'none',
  borderRadius: 8,
  background: '#2563eb',
  color: '#ffffff',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 8,
  padding: '0 12px',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 700,
};

const selectStyle: CSSProperties = {
  height: 36,
  border: '1px solid #cbd5e1',
  borderRadius: 8,
  background: '#ffffff',
  color: '#334155',
  padding: '0 10px',
  fontSize: 13,
};

const inputStyle: CSSProperties = {
  minHeight: 36,
  border: '1px solid #cbd5e1',
  borderRadius: 8,
  padding: '0 10px',
  fontSize: 13,
  boxSizing: 'border-box',
  width: '100%',
};

const errorStyle: CSSProperties = {
  marginBottom: 12,
  padding: '10px 12px',
  borderRadius: 8,
  background: '#fee2e2',
  color: '#991b1b',
  fontSize: 13,
};

const pendingTravelStyle: CSSProperties = {
  border: '1px solid #e2e8f0',
  borderRadius: 8,
  padding: 10,
  background: '#f8fafc',
};

const approveButtonStyle: CSSProperties = {
  ...secondaryButtonStyle,
  minHeight: 30,
  width: 34,
  padding: 0,
  color: '#16a34a',
};

const rejectButtonStyle: CSSProperties = {
  ...secondaryButtonStyle,
  minHeight: 30,
  width: 34,
  padding: 0,
  color: '#dc2626',
};
