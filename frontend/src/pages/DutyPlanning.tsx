import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties, MouseEvent } from 'react';
import { Link } from 'react-router-dom';
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  ClipboardCopy,
  Eraser,
  Mail,
  RefreshCw,
  Table2,
} from 'lucide-react';
import Card, { Badge } from '../components/Card';
import {
  getDepartments,
  getPlanningCalendar,
  savePlanningCells,
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
type PlanningToolCode = 'D' | 'B' | 'B+' | 'H' | 'H+' | 'I' | 'I+' | 'M' | 'M+' | 'T' | 'S' | 'U' | 'Ug' | 'A' | 'DR' | 'CLEAR';

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

type Department = {
  id: number;
  name: string;
};

type Props = {
  isHR: boolean;
  isManager: boolean;
};

type PlanningTool = {
  code: PlanningToolCode;
  label: string;
  color: string;
  tone: string;
};

const PLANNING_TOOLS: PlanningTool[] = [
  { code: 'D', label: 'Dienst', color: '#2563EB', tone: '#DBEAFE' },
  { code: 'B', label: 'Bereit', color: '#C2410C', tone: '#FFEDD5' },
  { code: 'B+', label: 'Bereit plus', color: '#C2410C', tone: '#FFEDD5' },
  { code: 'H', label: 'Hotline', color: '#16A34A', tone: '#DCFCE7' },
  { code: 'H+', label: 'Hotline plus', color: '#16A34A', tone: '#DCFCE7' },
  { code: 'I', label: 'Ilmenau', color: '#F97316', tone: '#FFEDD5' },
  { code: 'I+', label: 'Ilmenau plus', color: '#F97316', tone: '#FFEDD5' },
  { code: 'M', label: 'MVZ', color: '#EAB308', tone: '#FEF9C3' },
  { code: 'M+', label: 'MVZ plus', color: '#EAB308', tone: '#FEF9C3' },
  { code: 'T', label: 'Team', color: '#1D4ED8', tone: '#DBEAFE' },
  { code: 'S', label: 'Schule', color: '#2563EB', tone: '#E0E7FF' },
  { code: 'U', label: 'Urlaub', color: '#D97706', tone: '#FEF3C7' },
  { code: 'Ug', label: 'Geplant', color: '#0EA5E9', tone: '#E0F2FE' },
  { code: 'A', label: 'AZA', color: '#E11D48', tone: '#FFE4E6' },
  { code: 'DR', label: 'Reise', color: '#65A30D', tone: '#ECFCCB' },
  { code: 'CLEAR', label: 'Leeren', color: '#475569', tone: '#F1F5F9' },
];

const TOOL_BY_CODE = Object.fromEntries(PLANNING_TOOLS.map((tool) => [tool.code, tool])) as Record<PlanningToolCode, PlanningTool>;

const STATUS_LABELS: Record<string, string> = {
  REQUESTED: 'Beantragt',
  MANAGER_APPROVED: 'Fachlich frei',
  APPROVED: 'Genehmigt',
  APPROVED_LEGACY: 'Importiert',
  REJECTED: 'Abgelehnt',
  CANCELLED: 'Storniert',
  PLANNED: 'Geplant',
  CONFIRMED: 'Bestaetigt',
  SWAPPED: 'Getauscht',
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

export default function DutyPlanning({ isHR, isManager }: Props) {
  const today = new Date();
  const [mode, setMode] = useState<ViewMode>('year');
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [departmentId, setDepartmentId] = useState('');
  const [calendar, setCalendar] = useState<PlanningCalendar | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedTool, setSelectedTool] = useState<PlanningToolCode>('D');
  const [painting, setPainting] = useState(false);
  const [paintPreview, setPaintPreview] = useState<Map<string, string | null>>(new Map());
  const paintBufferRef = useRef<Map<string, { employee_id: number; date: string; code: string | null }>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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
      const calendarResponse = await getPlanningCalendar(params);
      setCalendar(calendarResponse.data as PlanningCalendar);
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
  const canEditPlanning = isManager;

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

  const paintCell = useCallback((employee: PlanningEmployee, day: PlanningDay) => {
    if (!canEditPlanning) return;
    const code = selectedTool === 'CLEAR' ? null : selectedTool;
    const key = `${employee.id}:${day.date}`;
    paintBufferRef.current.set(key, { employee_id: employee.id, date: day.date, code });
    setPaintPreview((current) => {
      const next = new Map(current);
      next.set(key, code);
      return next;
    });
  }, [canEditPlanning, selectedTool]);

  const beginPaint = useCallback((employee: PlanningEmployee, day: PlanningDay) => {
    if (!canEditPlanning) return;
    paintBufferRef.current = new Map();
    setPaintPreview(new Map());
    setPainting(true);
    paintCell(employee, day);
  }, [canEditPlanning, paintCell]);

  const finishPaint = useCallback(async () => {
    if (!painting) return;
    setPainting(false);
    const entries = Array.from(paintBufferRef.current.values());
    paintBufferRef.current = new Map();
    if (entries.length === 0) return;

    setError('');
    try {
      await savePlanningCells(entries);
      setPaintPreview(new Map());
      await load();
    } catch (saveError: any) {
      setError(saveError.response?.data?.detail || 'Planungszellen konnten nicht gespeichert werden');
      setPaintPreview(new Map());
      await load();
    }
  }, [load, painting]);

  useEffect(() => {
    if (!painting) return undefined;
    const stopPainting = () => {
      void finishPaint();
    };
    window.addEventListener('mouseup', stopPainting);
    return () => window.removeEventListener('mouseup', stopPainting);
  }, [finishPaint, painting]);

  const title = mode === 'year' ? String(year) : `${MONTH_NAMES[month - 1]} ${year}`;
  const totalEvents = employees.reduce(
    (sum, employee) => sum + employee.days.reduce((daySum, day) => daySum + day.events.length, 0),
    0
  );
  const totalTravel = employees.reduce(
    (sum, employee) =>
      sum + employee.days.reduce((daySum, day) => daySum + day.events.filter((item) => item.code === 'DR').length, 0),
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
              {canEditPlanning ? (
                <PlanningToolbox selectedTool={selectedTool} onSelect={setSelectedTool} />
              ) : (
                <Legend />
              )}
            </div>
            <PlanningTable
              mode={mode}
              days={days}
              employees={employees}
              monthHeaders={monthHeaders}
              loading={loading}
              onOpenMonth={openMonth}
              canEdit={canEditPlanning}
              isPainting={painting}
              paintPreview={paintPreview}
              onBeginPaint={beginPaint}
              onPaintCell={paintCell}
            />
          </Card>
        </div>

        <aside style={{ display: 'flex', flexDirection: 'column', gap: 16, minWidth: 280 }}>
          <ReadinessMailCard calendar={calendar} year={year} month={month} />
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
  canEdit,
  isPainting,
  paintPreview,
  onBeginPaint,
  onPaintCell,
}: {
  mode: ViewMode;
  days: string[];
  employees: PlanningEmployee[];
  monthHeaders: Array<{ month: number; label: string; count: number }>;
  loading: boolean;
  onOpenMonth: (day: string) => void;
  canEdit: boolean;
  isPainting: boolean;
  paintPreview: Map<string, string | null>;
  onBeginPaint: (employee: PlanningEmployee, day: PlanningDay) => void;
  onPaintCell: (employee: PlanningEmployee, day: PlanningDay) => void;
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
                <CalendarCell
                  key={`${employee.id}-${day.date}`}
                  day={day}
                  compact={mode === 'year'}
                  draftCode={paintPreview.get(`${employee.id}:${day.date}`)}
                  canEdit={canEdit}
                  onMouseDown={() => onBeginPaint(employee, day)}
                  onMouseEnter={(event) => {
                    if (isPainting && event.buttons === 1) onPaintCell(employee, day);
                  }}
                />
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

function CalendarCell({
  day,
  compact,
  draftCode,
  canEdit,
  onMouseDown,
  onMouseEnter,
}: {
  day: PlanningDay;
  compact: boolean;
  draftCode?: string | null;
  canEdit: boolean;
  onMouseDown: () => void;
  onMouseEnter: (event: MouseEvent<HTMLTableCellElement>) => void;
}) {
  const previewEvent = draftCode === undefined ? null : previewPlanningEvent(draftCode);
  const events = previewEvent ? [previewEvent] : draftCode === null ? [] : day.events;
  const primary = events[0];
  const hasConflict = events.some((event) => event.type === 'absence') &&
    events.some((event) => event.type === 'shift' || event.type === 'duty');

  return (
    <td
      onMouseDown={(event) => {
        if (!canEdit || event.button !== 0) return;
        event.preventDefault();
        onMouseDown();
      }}
      onMouseEnter={(event) => {
        if (canEdit) onMouseEnter(event);
      }}
      title={events.map(eventTitle).join('\n')}
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
        cursor: canEdit ? 'crosshair' : 'default',
        userSelect: 'none',
      }}
    >
      {compact ? (
        <div style={{ fontSize: 10, fontWeight: 800, color: primary?.color || '#cbd5e1', lineHeight: '20px' }}>
          {primary?.code || ''}
          {events.length > 1 ? '+' : ''}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {events.slice(0, 3).map((event, index) => (
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
          {events.length > 3 && <span style={{ color: '#64748b', fontSize: 10 }}>+{events.length - 3}</span>}
        </div>
      )}
    </td>
  );
}

function previewPlanningEvent(code: string | null): PlanningEvent | null {
  if (code === null) return null;
  const tool = TOOL_BY_CODE[code as PlanningToolCode];
  if (!tool) return null;
  const type = code === 'D' ? 'shift' : ['U', 'Ug', 'A', 'DR'].includes(code) ? 'absence' : ['B', 'B+', 'H', 'H+', 'I', 'I+', 'M', 'M+'].includes(code) ? 'duty' : 'info';
  return {
    id: -1,
    type,
    code,
    label: tool.label,
    status: 'VORSCHAU',
    color: tool.color,
  };
}

function PlanningToolbox({
  selectedTool,
  onSelect,
}: {
  selectedTool: PlanningToolCode;
  onSelect: (tool: PlanningToolCode) => void;
}) {
  return (
    <div style={toolboxStyle}>
      {PLANNING_TOOLS.map((tool) => {
        const active = selectedTool === tool.code;
        const isClear = tool.code === 'CLEAR';
        return (
          <button
            key={tool.code}
            type="button"
            onClick={() => onSelect(tool.code)}
            title={tool.label}
            style={{
              ...toolButtonStyle,
              borderColor: active ? tool.color : '#cbd5e1',
              background: active ? tool.tone : '#ffffff',
              color: tool.color,
              boxShadow: active ? `inset 0 0 0 1px ${tool.color}` : 'none',
            }}
          >
            {isClear ? <Eraser size={14} /> : <span>{tool.code}</span>}
          </button>
        );
      })}
    </div>
  );
}

function ReadinessMailCard({
  calendar,
  year,
  month,
}: {
  calendar: PlanningCalendar | null;
  year: number;
  month: number;
}) {
  const [copied, setCopied] = useState(false);
  const weeks = useMemo(() => buildReadinessWeeks(calendar, year, month), [calendar, year, month]);
  const mailText = useMemo(() => buildReadinessMailText(weeks, year, month), [weeks, year, month]);
  const subject = `IT-Bereitschaft ${MONTH_NAMES[month - 1]} ${year}`;
  const mailto = `mailto:IT-Bereitschaft@ilm-kreis-kliniken.de?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(mailText)}`;

  const copyMail = async () => {
    await navigator.clipboard?.writeText(mailText);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <Card title="Karteikarte Bereitschaft-Mail">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {weeks.length === 0 ? (
          <div style={{ color: '#94a3b8', fontSize: 13 }}>Keine Bereitschaft im Monat</div>
        ) : (
          weeks.map((week) => (
            <div key={week.key} style={readinessWeekStyle}>
              <div style={{ fontWeight: 800, color: '#0f172a', fontSize: 13 }}>{week.label}</div>
              <div style={{ color: '#475569', fontSize: 12 }}>{week.names.join(', ')}</div>
            </div>
          ))
        )}
        <div style={mailTemplateStyle}>
          {mailText.split('\n').slice(0, 9).map((line, index) => (
            <div key={`${line}-${index}`}>{line || '\u00a0'}</div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" onClick={() => void copyMail()} style={secondaryButtonStyle}>
            <ClipboardCopy size={16} />
            {copied ? 'Kopiert' : 'Kopieren'}
          </button>
          <a href={mailto} style={secondaryButtonStyle}>
            <Mail size={16} />
            Mail
          </a>
        </div>
      </div>
    </Card>
  );
}

function buildReadinessWeeks(calendar: PlanningCalendar | null, year: number, month: number) {
  const weeks = new Map<string, { key: string; label: string; names: string[]; start: Date }>();
  for (const employee of calendar?.employees || []) {
    for (const day of employee.days) {
      const parsed = localDate(day.date);
      if (parsed.getFullYear() !== year || parsed.getMonth() + 1 !== month) continue;
      if (!day.events.some((event) => event.code === 'B')) continue;
      const start = weekStart(parsed);
      const end = new Date(start);
      end.setDate(start.getDate() + 6);
      const key = start.toISOString().slice(0, 10);
      const existing = weeks.get(key) || {
        key,
        start,
        label: `${pad(start.getDate())}.${pad(start.getMonth() + 1)}. - ${pad(end.getDate())}.${pad(end.getMonth() + 1)}.`,
        names: [],
      };
      if (!existing.names.includes(employee.name)) {
        existing.names.push(employee.name);
      }
      weeks.set(key, existing);
    }
  }
  return Array.from(weeks.values()).sort((a, b) => a.start.getTime() - b.start.getTime());
}

function buildReadinessMailText(
  weeks: Array<{ label: string; names: string[] }>,
  year: number,
  month: number,
) {
  const weekLines = weeks.length
    ? weeks.map((week) => `${week.label} ${week.names.join(', ')}`)
    : ['Keine Bereitschaft eingetragen'];
  return [
    `Bereitschaft ${MONTH_NAMES[month - 1]} ${year}`,
    '',
    ...weekLines,
    '',
    'Bereitschaftszeiten:',
    'Mo-Fr ab 06:00 Uhr immer erst 50881 anrufen',
    'ab 15:30 Uhr noch 50884 probieren',
    'Verhaltensregeln ausserhalb der Bereitschaftszeiten siehe VA Rufbereitschaft der Abteilung IT',
    '',
    'Alarmierung per MAIL an: IT-Bereitschaft@ilm-kreis-kliniken.de',
    'Telefonnummern nur nutzen, wenn der Notruf ueber Programm/Mail nicht funktioniert oder innerhalb von 30 Minuten keine Rueckmeldung erfolgt.',
    'Diese Telefonnummern sind nicht weiterzugeben!',
    '',
    'Ansprechpartner:',
    'Holger Enig: 0174 3473241 / holger.enig@gmx.de',
    'Tom Scheike: 0162 1991424 / Tom.Scheike.Hotline@mail.de',
    'Andre Stoecklein: 0174 3473244 / bereitschaft-ikk@gmx.de',
    'Peter Czaikowski: 0174 3473245 / peter.czaikowski@ilm-kreis-kliniken.de',
    'Ronny Weise: 01525 9753522 / ronny.weise@ilm-kreis-kliniken.de',
    'Marc Nitsch: 0174 3473243 / marc.nitsch@ilm-kreis-kliniken.de',
  ].join('\n');
}

function weekStart(value: Date) {
  const start = new Date(value);
  const day = start.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  start.setDate(start.getDate() + diff);
  start.setHours(0, 0, 0, 0);
  return start;
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

const toolboxStyle: CSSProperties = {
  display: 'flex',
  gap: 6,
  flexWrap: 'wrap',
  alignItems: 'center',
};

const toolButtonStyle: CSSProperties = {
  width: 34,
  height: 28,
  border: '1px solid #cbd5e1',
  borderRadius: 7,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 11,
  fontWeight: 900,
  cursor: 'pointer',
  padding: 0,
};

const readinessWeekStyle: CSSProperties = {
  border: '1px solid #e2e8f0',
  borderRadius: 8,
  background: '#f8fafc',
  padding: '8px 10px',
};

const mailTemplateStyle: CSSProperties = {
  border: '1px solid #e2e8f0',
  borderRadius: 8,
  background: '#ffffff',
  color: '#475569',
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
  fontSize: 11,
  lineHeight: 1.5,
  padding: 10,
  maxHeight: 160,
  overflow: 'hidden',
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

const selectStyle: CSSProperties = {
  height: 36,
  border: '1px solid #cbd5e1',
  borderRadius: 8,
  background: '#ffffff',
  color: '#334155',
  padding: '0 10px',
  fontSize: 13,
};

const errorStyle: CSSProperties = {
  marginBottom: 12,
  padding: '10px 12px',
  borderRadius: 8,
  background: '#fee2e2',
  color: '#991b1b',
  fontSize: 13,
};
