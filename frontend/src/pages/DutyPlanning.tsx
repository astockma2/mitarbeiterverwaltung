import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties, MouseEvent, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Download,
  Eraser,
  Paintbrush,
  Save,
  Search,
  Table2,
} from 'lucide-react';
import Card from '../components/Card';
import { getDutyPlan, getEmployees, saveDutyPlanCells } from '../services/api';

const DAY_WIDTH = 28;
const NAME_WIDTH = 190;
const BALANCE_WIDTH = 68;

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

const DUTY_CODE_OPTIONS = [
  { code: 'U', label: 'Urlaub', cellText: 'U', background: '#ffd42a', color: '#111827' },
  { code: 'Ug', label: 'Urlaub geplant', cellText: 'Ug', background: '#12a8e0', color: '#ffffff' },
  { code: 'A', label: 'Arbeitszeitausgleich', cellText: 'A', background: '#ff6b7a', color: '#111827' },
  { code: 'S', label: 'Schulung', cellText: 'S', background: '#006db6', color: '#ffffff' },
  { code: 'B', label: 'Bereitschaft', cellText: 'B', background: '#d45a1c', color: '#ffffff' },
  { code: 'I', label: 'Ilmenau', cellText: 'I', background: '#fff0ed', color: '#111827' },
  { code: 'H', label: 'Hotlinedienst', cellText: 'H', background: '#00b75a', color: '#ffffff' },
  { code: 'M', label: 'MVZ', cellText: 'M', background: '#f7eb00', color: '#111827' },
  { code: 'Dr', label: 'Dienstreisen', cellText: 'DR', background: '#b7e4a2', color: '#111827' },
  { code: 'K', label: 'Kur', cellText: 'K', background: '#ffc86f', color: '#111827' },
  { code: 'su', label: 'security update day', cellText: 'su', background: '#ff9aa8', color: '#111827' },
  { code: 'T', label: 'Teammeeting', cellText: 'T', background: '#0713c9', color: '#ffffff' },
  { code: 'Ez', label: 'Elternzeit', cellText: 'Ez', background: '#f4c04d', color: '#111827' },
  { code: 'TSC', label: 'Zeitreduzierung TSC', cellText: '', background: '#315d1e', color: '#ffffff' },
] as const;

type DutyCode = (typeof DUTY_CODE_OPTIONS)[number]['code'];
type ActiveTool = DutyCode | 'erase';
type SaveState = 'idle' | 'saving' | 'saved' | 'error';

type DutyPlanEntry = {
  id: number;
  employee_id: number;
  date: string;
  code: string;
  note?: string | null;
};

type EmployeeItem = {
  id: number;
  first_name: string;
  last_name: string;
  department_name?: string | null;
  vacation_days_per_year?: number | null;
};

type DayInfo = {
  date: Date;
  key: string;
  month: number;
  day: number;
  weekday: number;
  week: number;
};

type DutyAssignments = Record<number, Record<string, DutyCode>>;
type DutyCellUpdate = { employee_id: number; date: string; code: DutyCode | null };

const DUTY_CODE_MAP = DUTY_CODE_OPTIONS.reduce(
  (acc, option) => ({ ...acc, [option.code]: option }),
  {} as Record<DutyCode, (typeof DUTY_CODE_OPTIONS)[number]>
);

const VACATION_CODES = new Set<DutyCode>(['U', 'Ug']);

const tableHeaderCell: CSSProperties = {
  border: '1px solid #cbd5e1',
  padding: 0,
  height: 24,
  fontSize: 11,
  fontWeight: 700,
  color: '#0f172a',
  background: '#f8fafc',
  textAlign: 'center',
  whiteSpace: 'nowrap',
};

const stickyColumnBase: CSSProperties = {
  position: 'sticky',
  zIndex: 4,
  border: '1px solid #cbd5e1',
  background: '#ffffff',
};

function pad(value: number) {
  return String(value).padStart(2, '0');
}

function toDateKey(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function getIsoWeek(date: Date) {
  const utcDate = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = utcDate.getUTCDay() || 7;
  utcDate.setUTCDate(utcDate.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(utcDate.getUTCFullYear(), 0, 1));
  return Math.ceil((((utcDate.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
}

function getDaysForYear(year: number): DayInfo[] {
  const days: DayInfo[] = [];
  const cursor = new Date(year, 0, 1);
  while (cursor.getFullYear() === year) {
    days.push({
      date: new Date(cursor),
      key: toDateKey(cursor),
      month: cursor.getMonth(),
      day: cursor.getDate(),
      weekday: cursor.getDay(),
      week: getIsoWeek(cursor),
    });
    cursor.setDate(cursor.getDate() + 1);
  }
  return days;
}

function daysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate();
}

function isDutyCode(code: string): code is DutyCode {
  return Object.prototype.hasOwnProperty.call(DUTY_CODE_MAP, code);
}

function getEmployeeName(employee: EmployeeItem) {
  return `${employee.first_name} ${employee.last_name}`.trim();
}

function getErrorMessage(error: unknown, fallback: string) {
  const response = (error as { response?: { data?: { detail?: string } } }).response;
  return response?.data?.detail || fallback;
}

function isWeekend(day: DayInfo) {
  return day.weekday === 0 || day.weekday === 6;
}

function isHolidayBand(day: DayInfo) {
  const key = day.key;
  return (
    (key >= '2026-01-01' && key <= '2026-01-03') ||
    (key >= '2026-02-16' && key <= '2026-02-21') ||
    (key >= '2026-03-30' && key <= '2026-04-10') ||
    (key >= '2026-07-06' && key <= '2026-08-14') ||
    (key >= '2026-10-12' && key <= '2026-10-24') ||
    (key >= '2026-12-23' && key <= '2026-12-31')
  );
}

function escapeCsv(value: string | number) {
  const raw = String(value);
  if (raw.includes(';') || raw.includes('"') || raw.includes('\n')) {
    return `"${raw.replaceAll('"', '""')}"`;
  }
  return raw;
}

export default function DutyPlanning() {
  const [year, setYear] = useState(2026);
  const [employees, setEmployees] = useState<EmployeeItem[]>([]);
  const [assignments, setAssignments] = useState<DutyAssignments>({});
  const [activeTool, setActiveTool] = useState<ActiveTool>('U');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [stagedCount, setStagedCount] = useState(0);

  const isPainting = useRef(false);
  const stagedCells = useRef<Map<string, DutyCellUpdate>>(new Map());

  const days = useMemo(() => getDaysForYear(year), [year]);
  const monthHeaders = useMemo(
    () => MONTH_NAMES.map((name, month) => ({ name, month, days: daysInMonth(year, month) })),
    [year]
  );

  const filteredEmployees = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return employees;
    return employees.filter((employee) => {
      const name = getEmployeeName(employee).toLowerCase();
      const department = employee.department_name?.toLowerCase() || '';
      return name.includes(term) || department.includes(term);
    });
  }, [employees, search]);

  const loadPlanner = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [employeeResponse, planResponse] = await Promise.all([
        getEmployees({ page_size: 500, is_active: true }),
        getDutyPlan(year),
      ]);
      const nextAssignments: DutyAssignments = {};
      const entries = planResponse.data.entries as DutyPlanEntry[];

      for (const entry of entries) {
        if (!isDutyCode(entry.code)) continue;
        nextAssignments[entry.employee_id] = {
          ...(nextAssignments[entry.employee_id] || {}),
          [entry.date]: entry.code,
        };
      }

      setEmployees(employeeResponse.data.items as EmployeeItem[]);
      setAssignments(nextAssignments);
      setSaveState('idle');
    } catch (loadError) {
      setError(getErrorMessage(loadError, 'Dienstplanung konnte nicht geladen werden'));
    } finally {
      setLoading(false);
    }
  }, [year]);

  const commitPaint = useCallback(async () => {
    const entries = Array.from(stagedCells.current.values());
    if (entries.length === 0) return;

    stagedCells.current.clear();
    setStagedCount(0);
    setSaveState('saving');
    try {
      await saveDutyPlanCells(entries);
      setSaveState('saved');
    } catch (saveError) {
      setSaveState('error');
      setError(getErrorMessage(saveError, 'Dienstplan-Zellen konnten nicht gespeichert werden'));
      await loadPlanner();
    }
  }, [loadPlanner]);

  useEffect(() => {
    void loadPlanner();
  }, [loadPlanner]);

  useEffect(() => {
    const stopPainting = () => {
      if (!isPainting.current) return;
      isPainting.current = false;
      void commitPaint();
    };
    window.addEventListener('mouseup', stopPainting);
    return () => window.removeEventListener('mouseup', stopPainting);
  }, [commitPaint]);

  const stageCell = (employeeId: number, dateKey: string, code: DutyCode | null) => {
    const key = `${employeeId}:${dateKey}`;
    const currentCode = assignments[employeeId]?.[dateKey] || null;
    if (currentCode === code && !stagedCells.current.has(key)) return;

    stagedCells.current.set(key, { employee_id: employeeId, date: dateKey, code });
    setStagedCount(stagedCells.current.size);
    setSaveState('idle');

    setAssignments((current) => {
      const row = { ...(current[employeeId] || {}) };
      if (code) {
        row[dateKey] = code;
      } else {
        delete row[dateKey];
      }
      return { ...current, [employeeId]: row };
    });
  };

  const paintCell = (employeeId: number, dateKey: string) => {
    stageCell(employeeId, dateKey, activeTool === 'erase' ? null : activeTool);
  };

  const handleCellMouseDown = (
    employeeId: number,
    dateKey: string,
    event: MouseEvent<HTMLTableCellElement>
  ) => {
    event.preventDefault();
    if (loading) return;
    isPainting.current = true;
    paintCell(employeeId, dateKey);
  };

  const handleCellMouseEnter = (employeeId: number, dateKey: string) => {
    if (!isPainting.current || loading) return;
    paintCell(employeeId, dateKey);
  };

  const handleCellContextMenu = (
    employeeId: number,
    dateKey: string,
    event: MouseEvent<HTMLTableCellElement>
  ) => {
    event.preventDefault();
    stageCell(employeeId, dateKey, null);
    void commitPaint();
  };

  const plannedVacationDays = (employeeId: number) => {
    const row = assignments[employeeId] || {};
    return Object.values(row).filter((code) => VACATION_CODES.has(code)).length;
  };

  const remainingVacationDays = (employee: EmployeeItem) => {
    const entitlement = employee.vacation_days_per_year ?? 30;
    return Math.max(0, entitlement - plannedVacationDays(employee.id));
  };

  const exportCsv = () => {
    const header = ['Name', 'Rest 2025', String(year), ...days.map((day) => day.key)];
    const rows = filteredEmployees.map((employee) => [
      getEmployeeName(employee),
      '0',
      String(remainingVacationDays(employee)),
      ...days.map((day) => assignments[employee.id]?.[day.key] || ''),
    ]);
    const csv = [header, ...rows]
      .map((row) => row.map((value) => escapeCsv(value)).join(';'))
      .join('\n');
    const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `dienstplanung-${year}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const totalVacation = filteredEmployees.reduce(
    (sum, employee) => sum + plannedVacationDays(employee.id),
    0
  );
  const totalReadiness = filteredEmployees.reduce((sum, employee) => {
    const row = assignments[employee.id] || {};
    return sum + Object.values(row).filter((code) => code === 'B').length;
  }, 0);

  const activeOption = activeTool === 'erase' ? null : DUTY_CODE_MAP[activeTool];
  const tableMinWidth = NAME_WIDTH + BALANCE_WIDTH * 2 + days.length * DAY_WIDTH;

  return (
    <div>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        gap: 16,
        marginBottom: 18,
        flexWrap: 'wrap',
      }}>
        <div>
          <h1 style={{
            margin: 0,
            fontSize: 24,
            color: '#1e293b',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}>
            <CalendarDays size={24} />
            Dienstplanung
          </h1>
          <div style={{ marginTop: 6, color: '#64748b', fontSize: 13 }}>
            Jahresuebersicht mit Urlaub, Bereitschaft, Hotline, Schulungen und Teamterminen
          </div>
        </div>
        <Link
          to="/shift-plans/monthly"
          title="Zur bisherigen Monatsplanung"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            padding: '9px 12px',
            border: '1px solid #cbd5e1',
            borderRadius: 8,
            color: '#334155',
            background: '#ffffff',
            textDecoration: 'none',
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          <Table2 size={16} />
          Monatsplanung
        </Link>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 12,
            flexWrap: 'wrap',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <button
                onClick={() => setYear((current) => current - 1)}
                title="Vorjahr"
                style={iconButtonStyle}
              >
                <ChevronLeft size={18} />
              </button>
              <div style={{
                minWidth: 120,
                textAlign: 'center',
                fontWeight: 700,
                fontSize: 20,
                color: '#0f172a',
              }}>
                {year}
              </div>
              <button
                onClick={() => setYear((current) => current + 1)}
                title="Naechstes Jahr"
                style={iconButtonStyle}
              >
                <ChevronRight size={18} />
              </button>
              <button
                onClick={() => setYear(2026)}
                title="Auf 2026 springen"
                style={secondaryButtonStyle}
              >
                2026
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <div style={{
                position: 'relative',
                width: 240,
                maxWidth: '100%',
              }}>
                <Search
                  size={16}
                  style={{
                    position: 'absolute',
                    left: 10,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: '#64748b',
                  }}
                />
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Mitarbeiter suchen"
                  style={{
                    width: '100%',
                    height: 36,
                    padding: '0 10px 0 34px',
                    border: '1px solid #cbd5e1',
                    borderRadius: 8,
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
              </div>
              <button onClick={exportCsv} title="CSV exportieren" style={secondaryButtonStyle}>
                <Download size={16} />
                CSV
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            {DUTY_CODE_OPTIONS.map((option) => (
              <button
                key={option.code}
                onClick={() => setActiveTool(option.code)}
                title={option.label}
                style={{
                  ...codeButtonStyle,
                  borderColor: activeTool === option.code ? '#0f172a' : '#cbd5e1',
                  boxShadow: activeTool === option.code ? '0 0 0 2px rgba(15,23,42,0.12)' : 'none',
                }}
              >
                <span style={{
                  width: 16,
                  height: 16,
                  borderRadius: 4,
                  background: option.background,
                  border: '1px solid rgba(15,23,42,0.18)',
                }} />
                <span>{option.code}</span>
              </button>
            ))}
            <button
              onClick={() => setActiveTool('erase')}
              title="Zellen leeren"
              style={{
                ...codeButtonStyle,
                borderColor: activeTool === 'erase' ? '#0f172a' : '#cbd5e1',
                boxShadow: activeTool === 'erase' ? '0 0 0 2px rgba(15,23,42,0.12)' : 'none',
              }}
            >
              <Eraser size={16} />
              Leeren
            </button>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: 10,
          }}>
            <Metric label="Mitarbeiter" value={filteredEmployees.length} />
            <Metric label="Urlaub geplant" value={totalVacation} />
            <Metric label="Bereitschaften" value={totalReadiness} />
            <Metric
              label="Status"
              value={saveStateLabel(saveState, stagedCount)}
              icon={saveState === 'saving' ? <Save size={16} /> : <Paintbrush size={16} />}
            />
          </div>
        </div>
      </Card>

      {error && (
        <div style={{
          marginBottom: 12,
          padding: '10px 12px',
          borderRadius: 8,
          background: '#fee2e2',
          color: '#991b1b',
          fontSize: 13,
        }}>
          {error}
        </div>
      )}

      <Card style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '12px 14px',
          borderBottom: '1px solid #e2e8f0',
          background: '#ffffff',
          flexWrap: 'wrap',
        }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 13,
            color: '#334155',
            fontWeight: 600,
          }}>
            <Paintbrush size={16} />
            {activeTool === 'erase' ? 'Leeren' : `${activeOption?.code} - ${activeOption?.label}`}
          </div>
          <div style={{ color: '#64748b', fontSize: 12 }}>
            Ziehen zum Malen, Rechtsklick leert eine Zelle.
          </div>
        </div>

        <div style={{
          overflow: 'auto',
          maxHeight: 'calc(100vh - 330px)',
          minHeight: 360,
          background: '#f8fafc',
        }}>
          <table style={{
            borderCollapse: 'collapse',
            tableLayout: 'fixed',
            minWidth: tableMinWidth,
            width: tableMinWidth,
            userSelect: 'none',
            background: '#ffffff',
          }}>
            <thead>
              <tr>
                <th rowSpan={3} style={stickyHeaderStyle(0, NAME_WIDTH)}>Name</th>
                <th rowSpan={3} style={stickyHeaderStyle(NAME_WIDTH, BALANCE_WIDTH)}>Rest 2025</th>
                <th rowSpan={3} style={stickyHeaderStyle(NAME_WIDTH + BALANCE_WIDTH, BALANCE_WIDTH)}>
                  {year}
                </th>
                {monthHeaders.map((month) => (
                  <th
                    key={month.name}
                    colSpan={month.days}
                    style={{
                      ...tableHeaderCell,
                      position: 'sticky',
                      top: 0,
                      zIndex: 2,
                      height: 28,
                      background: '#eef7e9',
                      borderLeft: month.month === 0 ? '2px solid #94a3b8' : '1px solid #cbd5e1',
                    }}
                  >
                    {month.name}
                  </th>
                ))}
              </tr>
              <tr>
                {days.map((day) => (
                  <th
                    key={`kw-${day.key}`}
                    style={{
                      ...tableHeaderCell,
                      position: 'sticky',
                      top: 28,
                      zIndex: 2,
                      width: DAY_WIDTH,
                      background: isWeekend(day) ? '#d9f4fb' : '#f8fafc',
                      borderLeft: day.day === 1 ? '2px solid #94a3b8' : '1px solid #cbd5e1',
                    }}
                  >
                    {day.weekday === 1 || day.day === 1 ? day.week : ''}
                  </th>
                ))}
              </tr>
              <tr>
                {days.map((day) => (
                  <th
                    key={`day-${day.key}`}
                    title={`${WEEKDAY_SHORT[day.weekday]} ${day.day}.${day.month + 1}.${year}`}
                    style={{
                      ...tableHeaderCell,
                      position: 'sticky',
                      top: 52,
                      zIndex: 2,
                      width: DAY_WIDTH,
                      background: isWeekend(day) ? '#d9f4fb' : isHolidayBand(day) ? '#ffefb0' : '#ffffff',
                      borderLeft: day.day === 1 ? '2px solid #94a3b8' : '1px solid #cbd5e1',
                    }}
                  >
                    {day.day}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={days.length + 3} style={{ padding: 28, textAlign: 'center', color: '#64748b' }}>
                    Dienstplanung wird geladen...
                  </td>
                </tr>
              )}

              {!loading && filteredEmployees.map((employee, rowIndex) => (
                <tr key={employee.id}>
                  <td style={{
                    ...stickyBodyStyle(0, NAME_WIDTH, rowIndex),
                    padding: '0 8px',
                    textAlign: 'left',
                    fontWeight: 600,
                    color: '#0f172a',
                  }}>
                    {getEmployeeName(employee)}
                  </td>
                  <td style={stickyBodyStyle(NAME_WIDTH, BALANCE_WIDTH, rowIndex)}>
                    0
                  </td>
                  <td style={stickyBodyStyle(NAME_WIDTH + BALANCE_WIDTH, BALANCE_WIDTH, rowIndex)}>
                    {remainingVacationDays(employee)}
                  </td>
                  {days.map((day) => {
                    const code = assignments[employee.id]?.[day.key] || null;
                    const option = code ? DUTY_CODE_MAP[code] : null;
                    return (
                      <td
                        key={`${employee.id}-${day.key}`}
                        title={`${getEmployeeName(employee)} - ${WEEKDAY_SHORT[day.weekday]} ${day.day}.${day.month + 1}.${year}${option ? ` - ${option.label}` : ''}`}
                        onMouseDown={(event) => handleCellMouseDown(employee.id, day.key, event)}
                        onMouseEnter={() => handleCellMouseEnter(employee.id, day.key)}
                        onContextMenu={(event) => handleCellContextMenu(employee.id, day.key, event)}
                        style={{
                          width: DAY_WIDTH,
                          height: 22,
                          border: '1px solid #cbd5e1',
                          borderLeft: day.day === 1 ? '2px solid #94a3b8' : '1px solid #cbd5e1',
                          background: option?.background || (isWeekend(day) ? '#d9f4fb' : isHolidayBand(day) ? '#ffefb0' : '#ffffff'),
                          color: option?.color || '#0f172a',
                          textAlign: 'center',
                          fontSize: 10,
                          fontWeight: option ? 700 : 500,
                          cursor: activeTool === 'erase' ? 'cell' : 'crosshair',
                          lineHeight: '22px',
                        }}
                      >
                        {option?.cellText || ''}
                      </td>
                    );
                  })}
                </tr>
              ))}

              {!loading && filteredEmployees.length === 0 && (
                <tr>
                  <td colSpan={days.length + 3} style={{ padding: 28, textAlign: 'center', color: '#64748b' }}>
                    Keine Mitarbeiter gefunden.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function Metric({
  label,
  value,
  icon,
}: {
  label: string;
  value: string | number;
  icon?: ReactNode;
}) {
  return (
    <div style={{
      border: '1px solid #e2e8f0',
      borderRadius: 8,
      padding: '10px 12px',
      minHeight: 58,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 10,
      background: '#f8fafc',
    }}>
      <div>
        <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{label}</div>
        <div style={{ fontSize: 17, color: '#0f172a', fontWeight: 700 }}>{value}</div>
      </div>
      {icon && <div style={{ color: '#475569', display: 'flex' }}>{icon}</div>}
    </div>
  );
}

function saveStateLabel(saveState: SaveState, stagedCount: number) {
  if (stagedCount > 0) return `${stagedCount} offen`;
  if (saveState === 'saving') return 'Speichert';
  if (saveState === 'saved') return 'Gespeichert';
  if (saveState === 'error') return 'Fehler';
  return 'Bereit';
}

function stickyHeaderStyle(left: number, width: number): CSSProperties {
  return {
    ...stickyColumnBase,
    top: 0,
    left,
    width,
    minWidth: width,
    zIndex: 5,
    height: 80,
    fontSize: 11,
    fontWeight: 700,
    color: '#0f172a',
  };
}

function stickyBodyStyle(left: number, width: number, rowIndex: number): CSSProperties {
  return {
    ...stickyColumnBase,
    left,
    width,
    minWidth: width,
    height: 22,
    textAlign: 'center',
    fontSize: 11,
    background: rowIndex % 2 === 0 ? '#eef4e8' : '#ffffff',
  };
}

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
  fontWeight: 600,
};

const codeButtonStyle: CSSProperties = {
  height: 34,
  border: '1px solid #cbd5e1',
  borderRadius: 8,
  background: '#ffffff',
  color: '#1e293b',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 6,
  padding: '0 10px',
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 700,
};
